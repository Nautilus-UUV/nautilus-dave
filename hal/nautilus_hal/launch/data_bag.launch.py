import os
from datetime import datetime

from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def is_running_in_docker():
    """Helper function to detect Docker environment."""
    return os.path.exists("/.dockerenv")


def generate_launch_description():
    time_str = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")

    if is_running_in_docker():
        bag_path = f"/ros2_ws/sim_data/raw/dive_{time_str}"
    else:
        bag_path = f"./sim_data/raw/dive_{time_str}"

    return LaunchDescription(
        [
            # 1. Start-Up: Interfaces
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [
                        os.path.join(
                            FindPackageShare("nautilus_hal").find("nautilus_hal"),
                            "launch",
                            "bridge.launch.py",
                        )
                    ]
                ),
                # launch_arguments={"use_sim_time": "true"}.items(),
            ),
            # 2. Start-Up: BCU Oscillator
            Node(
                package="py_pkg",
                executable="bcu_oscillator",
                name="bcu_oscillator",
                output="screen",
                # parameters=[{"use_sim_time": True}],
            ),
            # 3. Start-Up: Dave Robot Simulation
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [
                        os.path.join(
                            FindPackageShare("dave_demos").find("dave_demos"),
                            "launch",
                            "dave_robot.launch.py",
                        )
                    ]
                ),
                launch_arguments={
                    "z": "-5",
                    "namespace": "glider_nautilus",
                    "world_name": "dave_ocean_waves",
                    "paused": "false",
                    "gui": "true",
                    "headless": "true",
                    # "use_sim_time": "true",
                }.items(),
            ),
            # 4. Data Collection: Rosbag Record
            ExecuteProcess(
                cmd=[
                    "ros2",
                    "bag",
                    "record",
                    "-o",
                    bag_path,
                    "-s",
                    "mcap",
                    "--compression-mode",
                    "file",
                    "--compression-format",
                    "zstd",
                    "/imu/left",
                    "/external/pressure",
                    "/bcu/rpm",
                    "/bcu/flow_rate",
                    "/bcu/pressure",
                    "/bcu/rpm/fault",
                ],
                output="screen",
            ),
        ]
    )
