"""Surface mission sim composition.

Brings up everything needed to drive the simulated glider to the
surface and let it self-terminate the mission once it has been at
the surface for the dwell window:

    HAL bridges + Gazebo + glider robot
        + py_pkg control_stack    (ekf_prefilter, ekf_node, depth_node,
                                   acu_node, pathfinding_node)
        + optional MissionCommand + start auto-publish

Reused by ``test/sim/test_surface_sim.py``; also runnable on its own
for visualization, e.g.

    ros2 launch nautilus_hal surface_sim.launch.py \\
        headless:=false mission_autostart:=true

The mission self-terminates after ~10 s of dwell at gauge pressure
<= SURFACE_THRESHOLD_PA, but the launch keeps Gazebo and the control
stack running so you can observe the result or fire another mission.
"""

import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    gui = LaunchConfiguration("gui")
    headless = LaunchConfiguration("headless")
    mission_autostart = LaunchConfiguration("mission_autostart")

    bridge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    FindPackageShare("nautilus_hal").find("nautilus_hal"),
                    "launch",
                    "bridge.launch.py",
                )
            ]
        )
    )

    # Spawn deeper at z=-5
    # of vertical excursion gives the BCU + ACU something real to do.
    # `gui` stays "true" by convention; `headless` is the actual display switch.
    robot_launch = IncludeLaunchDescription(
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
            "gui": gui,
            "headless": headless,
        }.items(),
    )

    # Same control stack the bench will run; sim-agnostic by design.
    control_stack_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    FindPackageShare("py_pkg").find("py_pkg"),
                    "launch",
                    "control_stack.launch.py",
                )
            ]
        )
    )

    # CLI shortcut: when mission_autostart:=true, fire the same MissionCommand
    # + "start" the test publishes by hand. SURFACE has no operator-tunable
    # parameters, so the message is fixed: target_pressure_pa=0.0 (gauge),
    # angle_rad and n_resurfaces unused. /path and /command are
    # UUVQoS.COMMAND (RELIABLE + TRANSIENT_LOCAL) -- `ros2 topic pub` defaults
    # to volatile durability, so we must request transient_local explicitly.
    qos_args = [
        "--qos-reliability",
        "reliable",
        "--qos-durability",
        "transient_local",
    ]
    autostart_publish = TimerAction(
        period=8.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    "ros2",
                    "topic",
                    "pub",
                    "--once",
                    *qos_args,
                    "/path",
                    "nautilus_msgs/msg/MissionCommand",
                    "{mission_id: 2, target_pressure_pa: 0.0, angle_rad: 0.0,"
                    " n_resurfaces: 0}",
                ],
                output="screen",
            )
        ],
        condition=IfCondition(mission_autostart),
    )
    autostart_start = TimerAction(
        period=10.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    "ros2",
                    "topic",
                    "pub",
                    "--once",
                    *qos_args,
                    "/command",
                    "std_msgs/msg/String",
                    "{data: start}",
                ],
                output="screen",
            )
        ],
        condition=IfCondition(mission_autostart),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "gui",
                default_value="true",
                description="DAVE convention: keep true; use `headless` to toggle display.",
            ),
            DeclareLaunchArgument(
                "headless",
                default_value="true",
                description="True hides the Gazebo GUI; set false to visualize.",
            ),
            DeclareLaunchArgument(
                "mission_autostart",
                default_value="false",
                description=(
                    "Publish MissionCommand + start to /path and /command after "
                    "an 8/10 s delay. Off when the test drives the mission itself."
                ),
            ),
            DeclareLaunchArgument(
                "hold",
                default_value="false",
                description=(
                    "Informational: SURFACE self-terminates ~10 s after reaching "
                    "the surface, but the launch keeps Gazebo and the control "
                    "stack running so the operator can fire another mission."
                ),
            ),
            bridge_launch,
            robot_launch,
            control_stack_launch,
            autostart_publish,
            autostart_start,
        ]
    )
