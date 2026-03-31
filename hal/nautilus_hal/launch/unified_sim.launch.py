import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            # 1. Start-Up: Interfaces
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [
                        os.path.join(
                            get_package_share_directory("nautilus_hal"),
                            "launch",
                            "bridge.launch.py",
                        )
                    ]
                )
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
                }.items(),
            ),
        ]
    )
