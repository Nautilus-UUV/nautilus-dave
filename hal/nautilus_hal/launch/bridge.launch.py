import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory("nautilus_hal"), "config", "nautilus_params.yaml"
    )

    return LaunchDescription(
        [
            Node(
                package="nautilus_hal",
                executable="bcu_sim_bridge",
                name="nautilus_bcu_bridge",
                output="screen",
                parameters=[config],
            ),
            Node(
                package="nautilus_hal",
                executable="external_sensor_sim_bridge",
                name="nautilus_external_sensor_bridge",
                output="screen",
                parameters=[config],
            ),
            Node(
                package="nautilus_hal",
                executable="imu_sim_bridge",
                name="nautilus_imu_bridge",
                output="screen",
                parameters=[config],
            ),
        ]
    )
