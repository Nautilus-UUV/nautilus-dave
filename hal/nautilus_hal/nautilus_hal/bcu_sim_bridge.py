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
from sensor_msgs.msg import FluidPressure
from std_msgs.msg import Float32, Float64, Int32

from .bridge_base import SimBridgeNode, run_bridge
from .constants import Conversions, SimTopics, sea_pressure_pa
from .fault_injection import BCUFaultInjector


class BCUSimBridge(SimBridgeNode):
    def __init__(self):
        super().__init__("nautilus_bcu_bridge")

    def setup_bridges(self):
        # Bridge-specific YAML overrides (model_name is read by the base).
        self.m3_per_rev = self.get_parameter("m3_per_rev").value
        self.max_capacity = self.get_parameter("max_capacity_m3").value
        self.min_capacity = self.get_parameter("min_capacity_m3").value
        self.fault_probability = self.get_parameter("fault_probability_bcu").value
        self.fault_duration_sec = self.get_parameter("fault_duration_sec_bcu").value

        # Seeded from Gazebo's first BUOYANCY_VOLUME_STATE callback (see
        # sim_bcu_volume_callback). Until then we don't push a volume back
        # to Gazebo — pushing 0.0 + delta would clobber the SDF-initialized
        # bladder state on the first RPM tick.
        self.current_volume = None

        # ====================
        # Fault Injection
        # ====================
        self.rpm_fault_injector = BCUFaultInjector(
            self,
            fault_topic="/bcu/rpm/fault",
            fault_probability=self.fault_probability,
            fault_duration_sec=self.fault_duration_sec,
        )

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
            SimTopics.BUOYANCY_VOLUME_STATE.format(model_name=self.model_name),
            self.sim_bcu_volume_callback,
            10,
        )
        self.sim_pressure_sub = self.create_subscription(
            FluidPressure,
            SimTopics.SEA_PRESSURE.format(model_name=self.model_name),
            self.sim_sea_pressure_callback,
            10,
        )

        self.sim_volume_pub = self.create_publisher(
            Float64, SimTopics.BUOYANCY_COMMAND.format(model_name=self.model_name), 10
        )

        self.get_logger().info(f"Nautilus BCU Bridge: Listening on {UUVTopics.BCU_RPM}")

    def rpm_callback(self, msg):

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        raw_rpm = float(msg.data)
        rpm = self.rpm_fault_injector.apply(raw_rpm)

        # rpm -> rps -> total revs in dt -> volume change
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
        self.latest_pressure_pa = sea_pressure_pa(msg.fluid_pressure)

    def publish_at_rate(self):
        self.bcu_pressure_pub.publish(Int32(data=self.latest_pressure_pa))
        self.bcu_volume_pub.publish(Int32(data=self.latest_volume_ml))


def main(args=None):
    run_bridge(BCUSimBridge, args)


if __name__ == "__main__":
    main()
