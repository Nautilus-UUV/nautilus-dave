import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64


class BCUSimBridge(Node):
    def __init__(self):
        super().__init__("nautilus_bcu_bridge")

        # Constant: meter cube displaced per revolution (1ml)
        self.declare_parameter("m3_per_rev", 1.0e-7)
        self.declare_parameter("model_name", "glider_nautilus")

        model_name = self.get_parameter("model_name").value
        self.m3_per_rev = self.get_parameter("m3_per_rev").value

        self.current_volume = 0.0
        self.last_time = self.get_clock().now()

        self.rpm_sub = self.create_subscription(
            Float64,
            "/glider/bcu/rpm_cmd",
            self.rpm_callback,
            10,
        )

        self.sim_sub = self.create_subscription(
            Float64,
            f"/model/{model_name}/buoyancy_engine/current_volume",
            self.sim_feedback_callback,
            10,
        )

        self.volume_pub = self.create_publisher(
            Float64, f"/model/{model_name}/buoyancy_engine", 10
        )

        self.get_logger().info(
            "Nautilus BCU Bridge: Listening for RPM on /glider/bcu/rpm_cmd"
        )
        self.get_logger().info(
            f"Nautilus BCU Bridge: Publishing Volume to /model/{model_name}/buoyancy_engine"
        )

    def sim_feedback_callback(self, msg):
        self.current_volume = msg.data

    def rpm_callback(self, msg):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        # rpm -> rps -> total revs in dt -> volume change
        rpm = msg.data
        rps = rpm / 60.0
        delta_vol = rps * self.m3_per_rev * dt

        self.current_volume += delta_vol
        self.current_volume = max(
            0.0, min(self.current_volume, 0.0025)
        )  # TODO: do not hardcode this

        out_msg = Float64()
        out_msg.data = self.current_volume
        self.volume_pub.publish(out_msg)


def main(args=None):
    rclpy.init(args=args)
    node = BCUSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
