import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
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
                )
            ),
            # 2. Start-Up: Dave Robot Simulation
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
                    "roll": "3.141592653589793",
                    "yaw": "1.5707963267948966",
                    "namespace": "glider_nautilus",
                    "world_name": "dave_ocean_waves",
                    "paused": "false",
                    "gui": "true",
                }.items(),
            ),
        ]
    )
