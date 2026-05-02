import rclpy
from py_pkg.robot_specs import (
    BLADDER_MAX_VOLUME_M3,
    BLADDER_MIN_VOLUME_M3,
    VOLUME_PER_REV_M3,
)
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_publisher_for_topic,
    create_subscription_for_topic,
)
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import FluidPressure
from std_msgs.msg import Float32, Float64, Int32

from .constants import Conversions, SimTopics


class BCUSimBridge(Node):
    def __init__(self):
        super().__init__(
            "nautilus_bcu_bridge",
            automatically_declare_parameters_from_overrides=True,
            allow_undeclared_parameters=True,
        )

        # Directly access parameters from the YAML overrides.
        model_name = self.get_parameter("model_name").value

        # Seeded from Gazebo's first BUOYANCY_VOLUME_STATE callback (see
        # sim_bcu_volume_callback). Until then we don't push a volume back
        # to Gazebo — pushing 0.0 + delta would clobber the SDF-initialized
        # bladder state on the first RPM tick.
        self.current_volume = None

        # ====================
        # BCU RPM/flow control
        # ====================
        self.last_time = self.get_clock().now()
        self.rpm_sub = create_subscription_for_topic(
            self, UUVTopics.BCU_RPM, self.rpm_callback
        )
        self.flow_pub = create_publisher_for_topic(self, UUVTopics.BCU_FLOW_RATE)

        # ==============
        # BCU pressure / volume telemetry
        # ==============
        # Gazebo's buoyancy plugin only exposes bladder *volume*, not pressure.
        # On real hardware the BCU pressure transducer reads bladder pressure,
        # which for a flexible membrane in contact with seawater equals
        # ambient sea pressure to first order. So we source pressure from the
        # same sea-pressure plugin external_sensor_sim_bridge uses, and expose
        # bladder volume on its own topic.
        self.latest_volume_ml = 0  # bladder volume (mL), echoed from Gazebo
        self.latest_pressure_pa = 0  # bladder pressure (Pa), from sea pressure
        # 10 Hz pub timer to throttle data
        self.pub_timer = self.create_timer(0.1, self.publish_at_rate)
        self.bcu_pressure_pub = create_publisher_for_topic(self, UUVTopics.BCU_PRESSURE)
        self.bcu_volume_pub = create_publisher_for_topic(self, UUVTopics.BCU_VOLUME)
        self.sim_current_volume_sub = self.create_subscription(
            Float64,
            SimTopics.BUOYANCY_VOLUME_STATE.format(model_name=model_name),
            self.sim_bcu_volume_callback,
            10,
        )
        self.sim_pressure_sub = self.create_subscription(
            FluidPressure,
            SimTopics.SEA_PRESSURE.format(model_name=model_name),
            self.sim_sea_pressure_callback,
            10,
        )

        self.sim_volume_pub = self.create_publisher(
            Float64, SimTopics.BUOYANCY_COMMAND.format(model_name=model_name), 10
        )

        
        self.sim_oil_weight_pub = self.create_publisher(
            Float64, SimTopics.OIL_WEIGHT_COMMAND.format(model_name=model_name), 10
        )

        self.get_logger().info(f"Nautilus BCU Bridge: Listening on {UUVTopics.BCU_RPM}")

    def rpm_callback(self, msg):

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        # rpm -> rps -> total revs in dt -> volume change
        rpm = float(msg.data)
        rps = rpm / 60.0

        # Only integrate + push to Gazebo once we've synced to its SDF-
        # initialized bladder volume; otherwise we'd overwrite the initial
        # state. Flow-rate feedback below stays open-loop and fires regardless.
        if self.current_volume is not None:
            delta_vol = rps * VOLUME_PER_REV_M3 * dt

            self.current_volume += delta_vol
            self.current_volume = max(
                BLADDER_MIN_VOLUME_M3, min(self.current_volume, BLADDER_MAX_VOLUME_M3)
            )

            out_msg = Float64()
            out_msg.data = self.current_volume
            self.sim_volume_pub.publish(out_msg)

            out_msg_weight = Float64()
            out_msg_weight.data = self.current_volume/self.max_capacity*0.3091
            self.sim_oil_weight_pub.publish(out_msg_weight)

        # Mock Flow Rate feedback (m3/s)
        flow_msg = Float32()
        flow_msg.data = rps * VOLUME_PER_REV_M3
        self.flow_pub.publish(flow_msg)

    def sim_bcu_volume_callback(self, msg):
        # Seed current_volume from Gazebo's first volume report so subsequent
        # RPM-driven integration starts at the SDF-initialized bladder state.
        # last_time is also reset to now so the first dt after sync doesn't
        # include the time spent waiting for Gazebo's first publish.
        if self.current_volume is None:
            self.current_volume = float(msg.data)
            self.last_time = self.get_clock().now()

        # Volume (m3) to milliliters (mL) as integer
        self.latest_volume_ml = int(msg.data * Conversions.M3_TO_ML)

    def sim_sea_pressure_callback(self, msg):
        # The dave sea_pressure_sensor plugin fills FluidPressure.fluid_pressure
        # in kPa (its standardPressure is 101.325, gradient kPaPerM is 9.80638);
        # FluidPressure semantics require Pa, so scale here. Mirrors the
        # conversion in external_sensor_sim_bridge so /bcu/pressure and
        # /external/pressure share units (Pa, Int32) and downstream code can
        # use physics.pressure_to_depth on either.
        self.latest_pressure_pa = int(msg.fluid_pressure * 1000.0)

    def publish_at_rate(self):
        self.bcu_pressure_pub.publish(Int32(data=self.latest_pressure_pa))
        self.bcu_volume_pub.publish(Int32(data=self.latest_volume_ml))


def main(args=None):
    # Catch SIGINT/SIGTERM so the process exits 0 instead of 1 on Ctrl-C —
    # otherwise launch_testing's exit-code check intermittently fails.
    rclpy.init(args=args)
    node = BCUSimBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
