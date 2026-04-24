"""
Centralized structural constants for the Nautilus HAL.

This module contains unit conversions and topic templates.
Tunable physical parameters should be managed via ROS 2 parameters/YAML.
"""


class Conversions:
    """Unit conversion factors."""

    M3_TO_ML = 1e6
    ML_TO_M3 = 1e-6
    M_TO_CM = 100.0
    CM_TO_M = 0.01


class SimTopics:
    """Templates for Gazebo/Simulation topics."""

    # model_name is substituted at runtime via .format(model_name=...)
    BUOYANCY_VOLUME_STATE = "/model/{model_name}/buoyancy_engine/current_volume"
    BUOYANCY_COMMAND = "/model/{model_name}/buoyancy_engine"
    ACU_ROLL_COMMAND = "/model/{model_name}/acu_roll_joint/cmd_pos"
    ACU_TILT_COMMAND = "/model/{model_name}/acu_tilt_joint/cmd_pos"
    SEA_PRESSURE = "/model/{model_name}/sea_pressure"
    SEA_PRESSURE_DEPTH = "/model/{model_name}/sea_pressure_depth"
    IMU = "/model/{model_name}/imu"
