import rclpy
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_publisher_for_topic,
)
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Imu

from .constants import SimTopics


class IMUSimBridge(Node):
    def __init__(self):
        super().__init__(
            "nautilus_imu_bridge",
            automatically_declare_parameters_from_overrides=True,
            allow_undeclared_parameters=True,
        )

        model_name = self.get_parameter("model_name").value

        self.imu_left_pub = create_publisher_for_topic(self, UUVTopics.IMU_LEFT)
        self.imu_right_pub = create_publisher_for_topic(self, UUVTopics.IMU_RIGHT)

        # Gazebo IMU topic (bridged by ros_gz_bridge)
        self.sim_imu_sub = self.create_subscription(
            Imu,
            SimTopics.IMU.format(model_name=model_name),
            self.sim_imu_callback,
            10,
        )

        self.get_logger().info(
            f"Nautilus IMU Bridge: Listening for IMU on {SimTopics.IMU.format(model_name=model_name)}"
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
    # Catch SIGINT/SIGTERM so the process exits 0 instead of 1 on Ctrl-C —
    # otherwise launch_testing's exit-code check intermittently fails.
    rclpy.init(args=args)
    node = IMUSimBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
