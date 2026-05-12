import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    run_id = LaunchConfiguration("run_id")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "run_id",
                default_value="databag",
                description=(
                    "Run identifier baked into the bag output dir as "
                    "./sim_data/{run_id}_{timestamp}/raw."
                ),
            ),
            # 1. Start-Up: Interfaces + rosbag recording (bridge.launch.py
            # owns the bag path + topic list under its record/run_id args).
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [
                        os.path.join(
                            get_package_share_directory("nautilus_hal"),
                            "launch",
                            "bridge.launch.py",
                        )
                    ]
                ),
                launch_arguments={"record": "true", "run_id": run_id}.items(),
            ),
            # 2. Start-Up: BCU Oscillator
            Node(
                package="py_pkg",
                executable="bcu_oscillator",
                name="bcu_oscillator",
                output="screen",
            ),
            # 3. Start-Up: Dave Robot Simulation
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [
                        os.path.join(
                            get_package_share_directory("dave_demos"),
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
                }.items(),
            ),
        ]
    )
