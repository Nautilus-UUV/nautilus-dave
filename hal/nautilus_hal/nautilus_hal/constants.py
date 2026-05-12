"""
Centralized structural constants for the Nautilus HAL.

This module contains unit conversions and topic templates.
Tunable physical parameters should be managed via ROS 2 parameters/YAML.
"""


class Conversions:
    """Unit conversion factors."""

    M3_TO_ML = 1e6
    ML_TO_M3 = 1e-6
    CM_TO_M = 0.01
    MM_TO_M = 0.001
    # The dave sea_pressure_sensor plugin fills FluidPressure.fluid_pressure
    # in kPa (standardPressure=101.325, kPaPerM=9.80638) — FluidPressure
    # semantics require Pa, so every consumer rescales here. Keep in one
    # place so /external/pressure and /bcu/pressure can never drift apart.
    KPA_TO_PA = 1000.0


def sea_pressure_pa(fluid_pressure_kpa: float) -> int:
    """dave FluidPressure (kPa, despite the field name) -> integer Pa."""
    return int(fluid_pressure_kpa * Conversions.KPA_TO_PA)


class SimTopics:
    """Templates for Gazebo/Simulation topics."""

    # model_name is substituted at runtime via .format(model_name=...).
    # ACU joint command topics must match the <topic> declared by the
    # JointPositionController plugin in model.sdf and the parameter_bridge
    # entries in dave_robot_models/config/glider_nautilus/robot_config.py.
    # The SDF declares an explicit <topic> rather than relying on the
    # gz-sim default ".../0/cmd_pos", because that default has a digit-
    # leading path segment which ROS 2 topic-name validation rejects.
    BUOYANCY_VOLUME_STATE = "/model/{model_name}/buoyancy_engine/current_volume"
    BUOYANCY_COMMAND = "/model/{model_name}/buoyancy_engine"
    ACU_ROLL_COMMAND = "/model/{model_name}/joint/acu_roll_joint/cmd_pos"
    ACU_TILT_COMMAND = "/model/{model_name}/joint/acu_tilt_joint/cmd_pos"
    SEA_PRESSURE = "/model/{model_name}/sea_pressure"
    IMU = "/model/{model_name}/imu"
    # Ground-truth model pose, bridged out of Gazebo by
    # dave_robot_models/config/glider_nautilus/robot_config.py:16.
    # Sim-only — production controllers must not depend on this.
    ODOMETRY = "/model/{model_name}/odometry"
    # Gazebo-side joint state, bridged to ROS by parameter_bridge in
    # dave_robot_models/config/glider_nautilus/robot_config.py. world_name and
    # model_name are substituted at runtime.
    JOINT_STATE = "/world/{world_name}/model/{model_name}/joint_state"


class SimDebugTopics:
    """Templates for sim-only ROS-side debug egress.

    These topics are intentionally NOT registered in
    ``py_pkg.uuv_ros_core`` — production controllers must not be able to
    accidentally subscribe to them. They exist only so Tier 3 sim-integration
    tests can observe simulator-internal state (e.g. joint positions) that
    real hardware does not yet expose. The ``/sim/`` prefix is the contract:
    anything under it is privileged simulator feedback, not part of the
    glider's hardware-facing surface.
    """

    # model_name is substituted at runtime via .format(model_name=...).
    # Joint position republished from sensor_msgs/JointState in metres
    # (matches SDF ``acu_tilt_joint`` prismatic axis range 0 to -0.1195 m).
    ACU_PITCH_POSITION = "/sim/{model_name}/acu/pitch_position_m"
    # Joint position in radians (matches SDF ``acu_roll_joint`` revolute
    # axis range -0.5236 to +0.5236 rad).
    ACU_ROLL_POSITION = "/sim/{model_name}/acu/roll_position_rad"
