"""
unit conversions and topics
Units: ROS commands are Int16 — pitch in mm, roll in centidegrees
(scale = ACU_ROLL_CDEG_PER_DEG). Gazebo expects Float64 (m, rad).
Topics:
    - ros topics acu/roll and acu/pitch
    - Gazebo topics /model/{model_name}/joint/acu_roll_joint/cmd_pos and /model/{model_name}/joint/acu_tilt_joint/cmd_pos

Throttle frequency to 10Hz between ROS and Gazebo."""

import math

from py_pkg.robot_specs import ACU_ROLL_CDEG_PER_DEG
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_subscription_for_topic,
)
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

from .bridge_base import SimBridgeNode, run_bridge
from .constants import Conversions, SimDebugTopics, SimTopics


class ACUSimBridge(SimBridgeNode):
    def __init__(self):
        super().__init__("nautilus_acu_bridge")

    def setup_bridges(self):
        # world_name is only needed by this bridge (joint_state path).
        world_name = self.world_name
        model_name = self.model_name

        # ====================
        # ACU roll control
        # ====================
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
        roll_rad = math.radians(roll_deg)
        roll_msg = Float64()
        roll_msg.data = roll_rad
        self.sim_roll_pub.publish(roll_msg)

    def pitch_callback(self, msg):
        # ROS is in mm, Gazebo expects m.
        pitch_m = msg.data * Conversions.MM_TO_M
        sim_msg = Float64()
        sim_msg.data = pitch_m
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


def main(args=None):
    run_bridge(ACUSimBridge, args)


if __name__ == "__main__":
    main()
