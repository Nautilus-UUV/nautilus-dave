"""Trim & neutral-buoyancy sim composition.

Brings up everything needed to drive the simulated glider to a target gauge
pressure and hold it there in trim:

    HAL bridges + Gazebo + glider robot
        + py_pkg control_stack    (ekf_prefilter, ekf_node, depth_node,
                                   acu_node, pathfinding_node)
        + optional MissionCommand + start auto-publish

Reused by ``test/sim/test_trim_neutral_sim.py``; also runnable on its own
for visualization or bag recording, e.g.

    ros2 launch nautilus_hal trim_sim.launch.py headless:=false \\
        mission_autostart:=true target_pressure_pa:=75383.0

Mission data is not in the scenario YAML. The launch args above drive
the optional MissionCommand + start auto-publish; for anything richer
than that, publish ``/path`` and ``/command`` directly.
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


_MISSION_ID_TRIM = 0


def _maybe_autostart(context, *_args, **_kwargs):
    """Emit MissionCommand + start publishes if mission_autostart is true.

    /path and /command are UUVQoS.COMMAND (RELIABLE + TRANSIENT_LOCAL).
    `ros2 topic pub` defaults to volatile durability, so we request
    transient_local explicitly or pathfinding's subscription rejects on
    a durability mismatch.
    """
    autostart = LaunchConfiguration("mission_autostart").perform(context).lower() == "true"
    if not autostart:
        return []
    target_pressure_pa = float(LaunchConfiguration("target_pressure_pa").perform(context))

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
                        (
                            f"{{mission_id: {_MISSION_ID_TRIM}, "
                            f"target_pressure_pa: {target_pressure_pa}, "
                            f"angle_rad: 0.0, n_resurfaces: 0}}"
                        ),
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

    # Same spawn pose as the Tier 3 sim tests. `gui` is held at "true" by
    # convention; `headless` is the actual display switch.
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
                    "defaults to the installed nominal (fault-injection off). "
                    "Mission data is NOT in the YAML — see mission_autostart."
                ),
            ),
            DeclareLaunchArgument(
                "mission_autostart",
                default_value="false",
                description=(
                    "If true, the launch publishes the trim MissionCommand "
                    "(mission_id=0) plus `start` ~8 s after bringup, matching "
                    "what the sim test driver does by hand."
                ),
            ),
            DeclareLaunchArgument(
                "target_pressure_pa",
                default_value="75383.0",
                description=(
                    "Trim target in gauge Pa (~7.5 m). Only used when "
                    "mission_autostart is true."
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
                    "Informational: TRIM_AND_NEUTRAL never self-terminates, so the "
                    "launch holds either way. Documents intent when running from CLI."
                ),
            ),
            DeclareLaunchArgument(
                "record",
                default_value="false",
                description="If true, also record HAL topics to an MCAP rosbag.",
            ),
            DeclareLaunchArgument(
                "run_id",
                default_value="trim",
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
