from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="nautilus_hal",
                executable="bcu_sim_bridge",
                name="bcu_sim_bridge",
                output="screen",
            ),
            Node(
                package="nautilus_hal",
                executable="external_sensor_sim_bridge",
                name="external_sensor_sim_bridge",
                output="screen",
            ),
            Node(
                package="nautilus_hal",
                executable="imu_sim_bridge",
                name="imu_sim_bridge",
                output="screen",
            ),
        ]
    )
