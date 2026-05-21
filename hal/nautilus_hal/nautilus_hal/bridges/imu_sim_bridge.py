from py_pkg.scenarios.spec.rig import SimSpec
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_publisher_for_topic,
)
from sensor_msgs.msg import Imu

from ..constants import SimTopics
from .bridge_base import SimBridgeNode, run_bridge


class IMUSimBridge(SimBridgeNode):
    def __init__(self):
        super().__init__("nautilus_imu_bridge")

    def setup_bridges(self):
        self.declare_parameter("model_name", SimSpec().model_name)
        self.model_name = self.get_parameter("model_name").value

        self.imu_left_pub = create_publisher_for_topic(self, UUVTopics.IMU_LEFT)
        self.imu_right_pub = create_publisher_for_topic(self, UUVTopics.IMU_RIGHT)

        # Gazebo IMU topic (bridged by ros_gz_bridge)
        self.sim_imu_sub = self.create_subscription(
            Imu,
            SimTopics.IMU.format(model_name=self.model_name),
            self.sim_imu_callback,
            10,
        )

        self.get_logger().info(
            f"Nautilus IMU Bridge: Listening for IMU on "
            f"{SimTopics.IMU.format(model_name=self.model_name)}"
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
    run_bridge(IMUSimBridge, args)


if __name__ == "__main__":
    main()
