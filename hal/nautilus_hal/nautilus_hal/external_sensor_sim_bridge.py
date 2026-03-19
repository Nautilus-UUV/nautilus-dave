import rclpy
from geometry_msgs.msg import PointStamped
from py_pkg.uuv_ros_core import UUVTopics, create_publisher_for_topic
from rclpy.node import Node
from sensor_msgs.msg import FluidPressure
from std_msgs.msg import Int32


class ExternalSensorSimBridge(Node):
    def __init__(self):
        super().__init__("nautilus_external_sensor_bridge")

        self.declare_parameter("model_name", "glider_nautilus")

        model_name = self.get_parameter("model_name").value

        self.pressure_pub = create_publisher_for_topic(
            self, UUVTopics.EXTERNAL_PRESSURE
        )
        self.depth_pub = create_publisher_for_topic(self, UUVTopics.TEST_EXTERNAL_DEPTH)
        self.sim_pressure_sub = self.create_subscription(
            FluidPressure,
            f"/model/{model_name}/sea_pressure",
            self.sim_external_pressure_callback,
            10,
        )
        # the topic below is implicitly created by the <Sea Pressure Sensor Plugin>
        # in model.sdf
        self.sim_depth_sub = self.create_subscription(
            PointStamped,
            f"/model/{model_name}/sea_pressure_depth",
            self.sim_depth_callback,
            10,
        )

        self.get_logger().info(
            f"Nautilus Sensor Bridge: Listening for pose on  /model/{model_name}/pose"
        )

    def sim_external_pressure_callback(self, msg):
        """Publish depth as external pressure."""
        depth_msg = Int32()
        depth_msg.data = int(msg.fluid_pressure)

        self.pressure_pub.publish(depth_msg)

    def sim_depth_callback(self, msg):
        """Publish depth as external pressure."""
        depth_msg = Int32()
        depth_msg.data = int(msg.point.z * 100)

        self.depth_pub.publish(depth_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ExternalSensorSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
