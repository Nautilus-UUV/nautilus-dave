import rclpy
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_publisher_for_topic,
    create_subscription_for_topic,
)
from rclpy.node import Node
from std_msgs.msg import Float32, Float64, Int32


class BCUSimBridge(Node):
    def __init__(self):
        super().__init__("nautilus_bcu_bridge")

        # Constant: meter cube displaced per revolution (1ml)
        self.declare_parameter("m3_per_rev", 1.0e-6)
        self.declare_parameter("model_name", "glider_nautilus")

        model_name = self.get_parameter("model_name").value
        self.m3_per_rev = self.get_parameter("m3_per_rev").value

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
            f"/model/{model_name}/buoyancy_engine/current_volume",
            self.sim_bcu_volume_callback,
            10,
        )

        self.sim_volume_pub = self.create_publisher(
            Float64, f"/model/{model_name}/buoyancy_engine", 10
        )

        self.get_logger().info(f"Nautilus BCU Bridge: Listening on {UUVTopics.BCU_RPM}")

    def rpm_callback(self, msg):

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        # rpm -> rps -> total revs in dt -> volume change
        rpm = float(msg.data)
        rps = rpm / 60.0
        delta_vol = rps * self.m3_per_rev * dt

        self.current_volume += delta_vol
        self.current_volume = max(
            0.0, min(self.current_volume, 0.0025)
        )  # TODO: do not hardcode max capacity

        out_msg = Float64()
        out_msg.data = self.current_volume
        self.sim_volume_pub.publish(out_msg)

        # Mock Flow Rate feedback (m3/s)
        flow_msg = Float32()
        flow_msg.data = rps * self.m3_per_rev
        self.flow_pub.publish(flow_msg)

    def sim_bcu_volume_callback(self, msg):
        # Volume (m3) to milliliters (mL) as integer
        self.latest_volume = int(msg.data * 1e6)

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
