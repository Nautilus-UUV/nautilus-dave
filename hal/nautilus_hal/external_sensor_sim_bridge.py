import rclpy
from geometry_msgs.msg import PoseArray
from py_pkg.uuv_ros_core import UUVTopics, create_publisher_for_topic
from rclpy.node import Node
from std_msgs.msg import Int32


class ExternalSensorSimBridge(Node):
    def __init__(self):
        super().__init__("nautilus_external_sensor_bridge")

        self.declare_parameter("model_name", "glider_nautilus")

        model_name = self.get_parameter("model_name").value

        self.depth_pub = create_publisher_for_topic(self, UUVTopics.EXTERNAL_PRESSURE)
        self.sim_pose_sub = self.create_subscription(
            PoseArray,
            f"/model/{model_name}/pose",
            self.sim_pose_callback,
            10,
        )

        self.get_logger().info(
            f"Nautilus Sensor Bridge: Listening for pose on  /model/{model_name}/pose"
        )

    def sim_pose_callback(self, msg):
        """Publish depth as external pressure."""
        depth_msg = Int32()
        depth_cm = int(-msg.poses[0].position.z * 100)
        depth_msg.data = depth_cm

        self.depth_pub.publish(depth_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ExternalSensorSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
