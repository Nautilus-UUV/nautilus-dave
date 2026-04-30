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
from rclpy.node import Node
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

        self.current_volume = 0.0

        # ====================
        # BCU RPM/flow control
        # ====================
        self.last_time = self.get_clock().now()
        self.rpm_sub = create_subscription_for_topic(
            self, UUVTopics.BCU_RPM, self.rpm_callback
        )
        self.flow_pub = create_publisher_for_topic(self, UUVTopics.BCU_FLOW_RATE)

        # ==============
        # BCU pressure
        # ==============
        self.latest_volume = 0  # in mL
        # 10 Hz pub timer to throttle data
        self.pub_timer = self.create_timer(0.1, self.publish_at_rate)
        self.bcu_pressure_pub = create_publisher_for_topic(self, UUVTopics.BCU_PRESSURE)
        self.sim_current_volume_sub = self.create_subscription(
            Float64,
            SimTopics.BUOYANCY_VOLUME_STATE.format(model_name=model_name),
            self.sim_bcu_volume_callback,
            10,
        )

        self.sim_volume_pub = self.create_publisher(
            Float64, SimTopics.BUOYANCY_COMMAND.format(model_name=model_name), 10
        )

        self.get_logger().info(f"Nautilus BCU Bridge: Listening on {UUVTopics.BCU_RPM}")

    def rpm_callback(self, msg):

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        # rpm -> rps -> total revs in dt -> volume change
        rpm = float(msg.data)
        rps = rpm / 60.0
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
        # Volume (m3) to milliliters (mL) as integer
        self.latest_volume = int(msg.data * Conversions.M3_TO_ML)

    def publish_at_rate(self):
        bcu_pressure_msg = Int32(data=self.latest_volume)
        self.bcu_pressure_pub.publish(bcu_pressure_msg)


def main(args=None):
    rclpy.init(args=args)
    node = BCUSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
