"""
unit conversions and topics
Units: ROS commands are Int16 — pitch in mm, roll in centidegrees
(scale = ACU_ROLL_CDEG_PER_DEG). Gazebo expects Float64 (m, rad).
Topics:
    - ros topics acu/roll and acu/pitch
    - Gazebo topics /model/{model_name}/joint/acu_roll_joint/cmd_pos and /model/{model_name}/joint/acu_tilt_joint/cmd_pos

Throttle frequency to 10Hz between ROS and Gazebo."""

import math

import rclpy
from py_pkg.robot_specs import ACU_ROLL_CDEG_PER_DEG
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_subscription_for_topic,
)
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

from .constants import Conversions, SimDebugTopics, SimTopics


class ACUSimBridge(Node):
    def __init__(self):
        super().__init__(
            "nautilus_acu_bridge",
            automatically_declare_parameters_from_overrides=True,
            allow_undeclared_parameters=True,
        )

        # Directly access parameters from the YAML overrides.
        model_name = self.get_parameter("model_name").value
        world_name = self.get_parameter("world_name").value

        # ====================
        # ACU roll control
        # ====================
        # self.last_time = self.get_clock().now()
        self.roll_sub = create_subscription_for_topic(
            self, UUVTopics.ACU_ROLL, self.roll_callback
        )
        self.sim_roll_pub = self.create_publisher(
            Float64, SimTopics.ACU_ROLL_COMMAND.format(model_name=model_name), 10
        )

        # ==============
        # ACU pitch control (ROS) -> Gazebo acu_tilt_joint
        # ==============
        self.pitch_sub = create_subscription_for_topic(
            self, UUVTopics.ACU_PITCH, self.pitch_callback
        )
        self.sim_tilt_pub = self.create_publisher(
            Float64, SimTopics.ACU_TILT_COMMAND.format(model_name=model_name), 10
        )

        # ==============
        # Sim-only joint feedback egress (Tier 3 testing)
        # ==============
        # Real hardware has no ACU joint-state telemetry yet, so Tier 3
        # sim-integration tests need a privileged path to observe whether the
        # commanded ACU motion actually happens in Gazebo. We subscribe to
        # the parameter_bridge JointState forwarded from Gazebo and republish
        # the two ACU joint positions on /sim/* topics. The /sim/ prefix and
        # the deliberate omission from py_pkg.uuv_ros_core are the contract:
        # production controllers must not depend on these.
        self.sim_pitch_pos_pub = self.create_publisher(
            Float64,
            SimDebugTopics.ACU_PITCH_POSITION.format(model_name=model_name),
            10,
        )
        self.sim_roll_pos_pub = self.create_publisher(
            Float64,
            SimDebugTopics.ACU_ROLL_POSITION.format(model_name=model_name),
            10,
        )
        self.sim_joint_state_sub = self.create_subscription(
            JointState,
            SimTopics.JOINT_STATE.format(world_name=world_name, model_name=model_name),
            self.sim_joint_state_callback,
            10,
        )

        # 10 Hz pub timer to throttle data
        # self.pub_timer = self.create_timer(0.1, self.publish_at_rate)

        self.get_logger().info(
            f"Nautilus ACU Bridge: Listening on {UUVTopics.ACU_ROLL}"
        )
        self.get_logger().info(
            f"Nautilus ACU Bridge: Listening on {UUVTopics.ACU_PITCH}"
        )

    def roll_callback(self, msg):
        # ACU_ROLL is Int16 centidegrees on the wire; Gazebo's
        # JointPositionController expects radians.
        roll_deg = msg.data / ACU_ROLL_CDEG_PER_DEG
        roll_msg = Float64()
        roll_msg.data = math.radians(roll_deg)
        self.sim_roll_pub.publish(roll_msg)

    def pitch_callback(self, msg):

        sim_msg = Float64()
        sim_msg.data = (
            msg.data * Conversions.MM_TO_M
        )  # ROS is in mm, Gazebo expects m, so convert
        self.sim_tilt_pub.publish(sim_msg)

    def sim_joint_state_callback(self, msg: JointState) -> None:
        # JointState.name ordering is not guaranteed across Gazebo versions
        # (the SDF has many fixed joints in addition to the two ACU joints),
        # so we look up by name rather than indexing positionally.
        for name, position in zip(msg.name, msg.position):
            if name == "acu_tilt_joint":
                self.sim_pitch_pos_pub.publish(Float64(data=float(position)))
            elif name == "acu_roll_joint":
                self.sim_roll_pos_pub.publish(Float64(data=float(position)))

    """def publish_at_rate(self):
        bcu_pressure_msg = Int32(data=self.latest_volume)
        self.bcu_pressure_pub.publish(bcu_pressure_msg)"""


def main(args=None):
    # Catch SIGINT/SIGTERM so the process exits 0 instead of 1 on Ctrl-C —
    # otherwise launch_testing's exit-code check intermittently fails.
    rclpy.init(args=args)
    node = ACUSimBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
