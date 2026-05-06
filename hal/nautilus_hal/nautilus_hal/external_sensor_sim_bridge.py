import rclpy
from geometry_msgs.msg import PointStamped
from py_pkg.uuv_ros_core import UUVTopics, create_publisher_for_topic
from rclpy.node import Node
from sensor_msgs.msg import FluidPressure
from std_msgs.msg import Int32

from .constants import Conversions, SimTopics


class ExternalSensorSimBridge(Node):
    def __init__(self):
        super().__init__(
            "nautilus_external_sensor_bridge",
            automatically_declare_parameters_from_overrides=True,
            allow_undeclared_parameters=True,
        )

        model_name = self.get_parameter("model_name").value

        self.latest_pressure = 0
        self.latest_depth = 0
        # 10 Hz frequency for publishing external sensors
        self.pub_timer = self.create_timer(0.1, self.publish_at_rate)

        self.pressure_pub = create_publisher_for_topic(
            self, UUVTopics.EXTERNAL_PRESSURE
        )
        #self.depth_pub = create_publisher_for_topic(self, UUVTopics.TEST_EXTERNAL_DEPTH)
        self.sim_pressure_sub = self.create_subscription(
            FluidPressure,
            SimTopics.SEA_PRESSURE.format(model_name=model_name),
            self.sim_external_pressure_callback,
            10,
        )
        # the topic below is implicitly created by the <Sea Pressure Sensor Plugin>
        # in model.sdf
        self.sim_depth_sub = self.create_subscription(
            PointStamped,
            SimTopics.SEA_PRESSURE_DEPTH.format(model_name=model_name),
            self.sim_depth_callback,
            10,
        )

        self.get_logger().info(
            f"Nautilus Sensor Bridge: Listening for pose on {SimTopics.SEA_PRESSURE.format(model_name=model_name)}"
        )

    def sim_external_pressure_callback(self, msg):
        """Publish depth as external pressure."""
        self.latest_pressure = int(msg.fluid_pressure)

    def sim_depth_callback(self, msg):
        """Publish depth as external pressure."""
        self.latest_depth = int(msg.point.z * Conversions.M_TO_CM)  # m to cm conversion

    def publish_at_rate(self):
        """Publish external sensors."""
        pressure_msg = Int32(data=self.latest_pressure)
        self.pressure_pub.publish(pressure_msg)

        depth_msg = Int32(data=self.latest_depth)
        # self.depth_pub.publish(depth_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ExternalSensorSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
