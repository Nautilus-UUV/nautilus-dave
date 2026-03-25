"""
unit conversions and topics
Units: ros commands are in mm and radians (Float32), Gazebo is in m and radians (Float64)
Topics: 
    - ros topics acu/roll and acu/tilt
    - Gazebo topics /model/{model_name}/joint/acu_roll_joint/cmd_pos and /model/{model_name}/joint/acu_tilt_joint/cmd_pos

Throttle frequency to 10Hz between ROS and Gazebo."""

import rclpy
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_publisher_for_topic,
    create_subscription_for_topic,
)
from rclpy.node import Node
from std_msgs.msg import Float32, Float64, Int32

from .constants import Conversions, SimTopics

class ACUSimBridge(Node):
    def __init__(self):
        super().__init__(
            "nautilus_acu_bridge",
            automatically_declare_parameters_from_overrides=True,
            allow_undeclared_parameters=True,
        )

        # Directly access parameters from the YAML overrides.
        model_name = self.get_parameter("model_name").value

        # ====================
        # ACU roll control
        # ====================
        #self.last_time = self.get_clock().now()
        self.roll_sub = create_subscription_for_topic(
            self, UUVTopics.ACU_ROLL, self.roll_callback
        )
        self.roll_pub = create_publisher_for_topic(self, UUVTopics.ACU_ROLL_COMMAND)

        # ==============
        # ACU tilt control
        # ==============
        self.tilt_sub = create_subscription_for_topic(
            self, UUVTopics.ACU_TILT, self.tilt_callback
        )
        self.tilt_pub = create_publisher_for_topic(self, UUVTopics.ACU_TILT_COMMAND)
        
        # 10 Hz pub timer to throttle data
        #self.pub_timer = self.create_timer(0.1, self.publish_at_rate)
    
        self.get_logger().info(f"Nautilus ACU Bridge: Listening on {UUVTopics.ACU_ROLL}")

    def roll_callback(self, msg):

        roll_msg = Float64()
        roll_msg.data = msg.data  # ROS is in radians, Gazebo expects radians, so no conversion needed
        self.roll_pub.publish(roll_msg)
    
    def tilt_callback(self, msg):
        
        tilt_msg = Float64()
        tilt_msg.data = msg.data * Conversions.CM_TO_M  # ROS is in mm, Gazebo expects m, so convert
        self.tilt_pub.publish(tilt_msg)

    """def publish_at_rate(self):
        bcu_pressure_msg = Int32(data=self.latest_volume)
        self.bcu_pressure_pub.publish(bcu_pressure_msg)"""


def main(args=None):
    rclpy.init(args=args)
    node = ACUSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
