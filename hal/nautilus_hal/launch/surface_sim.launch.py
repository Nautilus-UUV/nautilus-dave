"""Surface sim composition.

Brings up everything needed to fire the SURFACE mission (mission_id=2),
which drives the glider back to gauge pressure 0 from wherever it is
and self-terminates once the BCU has held neutral on the surface for a
configurable hold window:

    HAL bridges + Gazebo + glider robot
        + py_pkg control_stack    (ekf_prefilter, ekf_node, depth_node,
                                   acu_node, pathfinding_node)
        + optional MissionCommand + start auto-publish

Reused by ``test/sim/test_surface_sim.py``. Mission data is not in the
scenario YAML — for SURFACE the target is fixed at gauge 0, so the only
mission-side knob is autostart:

    ros2 launch nautilus_hal surface_sim.launch.py headless:=false \\
        mission_autostart:=true
"""

import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare

_MISSION_ID_SURFACE = 2


def _maybe_autostart(context, *_args, **_kwargs):
    """Surface autostart: target is fixed at gauge 0; autostart from launch arg."""
    autostart = (
        LaunchConfiguration("mission_autostart").perform(context).lower() == "true"
    )
    if not autostart:
        return []

    qos_args = [
        "--qos-reliability",
        "reliable",
        "--qos-durability",
        "transient_local",
    ]
    return [
        TimerAction(
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
                        f"{{mission_id: {_MISSION_ID_SURFACE}, "
                        "target_pressure_pa: 0.0, angle_rad: 0.0, "
                        "n_resurfaces: 0}",
                    ],
                    output="screen",
                )
            ],
        ),
        TimerAction(
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
        ),
    ]


def generate_launch_description():
    gui = LaunchConfiguration("gui")
    headless = LaunchConfiguration("headless")
    record = LaunchConfiguration("record")
    run_id = LaunchConfiguration("run_id")
    scenario = LaunchConfiguration("scenario")

    bridge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    FindPackageShare("nautilus_hal").find("nautilus_hal"),
                    "launch",
                    "bridge.launch.py",
                )
            ]
        ),
        launch_arguments={
            "record": record,
            "run_id": run_id,
            "scenario": scenario,
        }.items(),
    )

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

    control_stack_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    FindPackageShare("py_pkg").find("py_pkg"),
                    "launch",
                    "control_stack.launch.py",
                )
            ]
        ),
        launch_arguments={"scenario": scenario}.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "scenario",
                default_value=os.path.join(
                    FindPackageShare("py_pkg").find("py_pkg"),
                    "scenarios",
                    "library",
                    "nominal.yaml",
                ),
                description=(
                    "Path to a scenario YAML. Parameterizes the HAL bridges "
                    "(rig block) and the control stack (control block); "
                    "defaults to the installed nominal. Mission data is NOT "
                    "in the YAML — see mission_autostart."
                ),
            ),
            DeclareLaunchArgument(
                "mission_autostart",
                default_value="false",
                description=(
                    "If true, the launch publishes the surface MissionCommand "
                    "(mission_id=2, target=0.0) plus `start` ~8 s after bringup."
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
                "hold",
                default_value="false",
                description=(
                    "Informational: SURFACE self-terminates ~10 s after reaching "
                    "the surface, but the launch keeps Gazebo and the control "
                    "stack running so the operator can fire another mission."
                ),
            ),
            DeclareLaunchArgument(
                "record",
                default_value="false",
                description="If true, also record HAL topics to an MCAP rosbag.",
            ),
            DeclareLaunchArgument(
                "run_id",
                default_value="surface",
                description=(
                    "Run identifier baked into the bag output dir as "
                    "./sim_data/{run_id}_{timestamp}/raw."
                ),
            ),
            bridge_launch,
            robot_launch,
            control_stack_launch,
            OpaqueFunction(function=_maybe_autostart),
        ]
    )
