"""Sawtooth glide sim composition.

Brings up everything needed to drive the simulated glider through one
or more SAWTOOTH cycles -- a hard descend at -angle_rad to
target_pressure_pa, then a hard ascend at +angle_rad back to the
surface, repeated for n_resurfaces cycles before self-terminating:

    HAL bridges + Gazebo + glider robot
        + py_pkg control_stack    (ekf_prefilter, ekf_node, depth_node,
                                   acu_node, pathfinding_node)
        + optional MissionCommand + start auto-publish

Reused by ``test/sim/test_sawtooth_sim.py``; also runnable on its own
for visualization, e.g.

    ros2 launch nautilus_hal sawtooth_sim.launch.py \\
        headless:=false mission_autostart:=true \\
        target_pressure_pa:=147150.0 angle_rad:=0.6109 n_resurfaces:=1

The mission self-terminates after `n_resurfaces` resurface events, but
the launch keeps Gazebo and the controllers running so you can fire
another mission from the CLI.
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
    target_pressure_pa = LaunchConfiguration("target_pressure_pa")
    angle_rad = LaunchConfiguration("angle_rad")
    n_resurfaces = LaunchConfiguration("n_resurfaces")
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

    # Same spawn pose as unified_sim.launch.py / Tier 3 tests. `gui` is held
    # at "true" by convention; `headless` is the actual display switch.
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
    # + "start" the test publishes by hand. /path and /command are
    # UUVQoS.COMMAND (RELIABLE + TRANSIENT_LOCAL) -- `ros2 topic pub` defaults
    # to volatile durability, so we must request transient_local explicitly
    # or pathfinding's subscription rejects on a durability mismatch.
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
                    [
                        "{mission_id: 1, target_pressure_pa: ",
                        target_pressure_pa,
                        ", angle_rad: ",
                        angle_rad,
                        ", n_resurfaces: ",
                        n_resurfaces,
                        "}",
                    ],
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
                "target_pressure_pa",
                default_value="147150.0",
                description="Sawtooth deep extremum (gauge Pa). 147150 ~ 15 m.",
            ),
            DeclareLaunchArgument(
                "angle_rad",
                default_value="0.6109",
                description=(
                    "Sawtooth glide pitch magnitude (rad); alternates sign "
                    "each leg. 0.6109 ~ 35 deg."
                ),
            ),
            DeclareLaunchArgument(
                "n_resurfaces",
                default_value="1",
                description=(
                    "Number of resurface events before the mission self-"
                    "terminates. 1 = one full descend+ascend cycle."
                ),
            ),
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
                    "Informational: SAWTOOTH self-terminates after `n_resurfaces` "
                    "cycles, but the launch keeps Gazebo and the control stack "
                    "running so the operator can fire another mission."
                ),
            ),
            bridge_launch,
            robot_launch,
            control_stack_launch,
            autostart_publish,
            autostart_start,
        ]
    )
