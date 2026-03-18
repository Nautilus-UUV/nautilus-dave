import rclpy
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_publisher_for_topic,
)
from rclpy.node import Node
from sensor_msgs.msg import Imu


class IMUSimBridge(Node):
    def __init__(self):
        super().__init__("nautilus_imu_bridge")

        self.declare_parameter("model_name", "glider_nautilus")
        model_name = self.get_parameter("model_name").value

        self.imu_left_pub = create_publisher_for_topic(self, UUVTopics.IMU_LEFT)
        self.imu_right_pub = create_publisher_for_topic(self, UUVTopics.IMU_RIGHT)

        # Gazebo IMU topic (bridged by ros_gz_bridge)
        self.sim_imu_sub = self.create_subscription(
            Imu,
            f"/model/{model_name}/imu",
            self.sim_imu_callback,
            10,
        )

        self.get_logger().info(
            f"Nautilus IMU Bridge: Listening for IMU on /model/{model_name}/imu"
        )
        self.get_logger().info(
            f"Nautilus IMU Bridge: Publishing to {UUVTopics.IMU_LEFT} and {UUVTopics.IMU_RIGHT}"
        )

    def sim_imu_callback(self, msg):
        """Bridge IMU data to UUV topics."""
        # For simulation, we map the same single IMU to both internal logic topics
        self.imu_left_pub.publish(msg)
        self.imu_right_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = IMUSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
