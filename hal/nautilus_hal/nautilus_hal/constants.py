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


class SimTopics:
    """Templates for Gazebo/Simulation topics."""

    # model_name is substituted at runtime via .format(model_name=...).
    # ACU joint command topics must match the parameter_bridge entries in
    # dave_robot_models/config/glider_nautilus/robot_config.py and the
    # default topic of gz-sim-joint-position-controller-system in model.sdf.
    BUOYANCY_VOLUME_STATE = "/model/{model_name}/buoyancy_engine/current_volume"
    BUOYANCY_COMMAND = "/model/{model_name}/buoyancy_engine"
    ACU_ROLL_COMMAND = "/model/{model_name}/joint/acu_roll_joint/cmd_pos"
    ACU_TILT_COMMAND = "/model/{model_name}/joint/acu_tilt_joint/cmd_pos"
    SEA_PRESSURE = "/model/{model_name}/sea_pressure"
    IMU = "/model/{model_name}/imu"
