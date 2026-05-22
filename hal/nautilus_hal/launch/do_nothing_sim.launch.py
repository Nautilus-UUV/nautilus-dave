"""Do-nothing sim composition.

Brings up the full sim + control stack but with the control commanding
nothing: the DO_NOTHING mission (mission_id=3) keeps every node live yet
publishes no setpoint, so the glider just holds its trim and drifts. On
start it also resets the controllers to their fresh, no-mission state, so
nothing carries over if you ran a mission earlier in the session.

    HAL bridges + Gazebo + glider robot
        + py_pkg control_stack    (ekf_prefilter, ekf_node, depth_node,
                                   acu_node, pathfinding_node)
        + optional MissionCommand + start auto-publish

Useful for exercising the sim, sensors, EKF, telemetry, MQTT bridge and the
operator UI without the glider moving. Mission data is not in the scenario
YAML — DO_NOTHING takes no parameters, so the only mission-side knob is
autostart:

    ros2 launch nautilus_hal do_nothing_sim.launch.py headless:=false \\
        mission_autostart:=true

Even with mission_autostart:=false the control does nothing (no mission is
loaded, so depth_node sits in its zero-RPM hold and acu_node stays quiet);
autostart just makes the Do-Nothing mission the explicit, UI-visible state.
"""

import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare

_MISSION_ID_DO_NOTHING = 3


def _build_robot_launch(context, *_args, **_kwargs):
    """Render the SDF from the scenario YAML (if hydrodynamics block set)
    and include dave_robot.launch.py with the resulting path.

    A scenario without a `rig.hydrodynamics:` block round-trips to the
    canonical model.sdf so this code path is bit-identical to today's
    launch for nominal/baseline.
    """
    from nautilus_hal.render_sdf import description_file_for_scenario

    scenario_path = LaunchConfiguration("scenario").perform(context)
    description_file = description_file_for_scenario(scenario_path)
    return [
        LogInfo(msg=f"Spawning SDF: {description_file}"),
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
                "gui": LaunchConfiguration("gui").perform(context),
                "headless": LaunchConfiguration("headless").perform(context),
                "description_file": description_file,
            }.items(),
        ),
    ]


def generate_launch_description():
    record = LaunchConfiguration("record")
    run_id = LaunchConfiguration("run_id")
    sampler_id = LaunchConfiguration("sampler_id")
    scenario = LaunchConfiguration("scenario")
    bag_path = LaunchConfiguration("bag_path")
    bag_compression = LaunchConfiguration("bag_compression")

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
            "sampler_id": sampler_id,
            "scenario": scenario,
            "bag_path": bag_path,
            "bag_compression": bag_compression,
        }.items(),
    )

    # Robot spawn is built inside `_build_robot_launch`, which resolves
    # the SDF path from the scenario YAML (canonical when nominal,
    # Jinja-rendered when a sampled `rig.hydrodynamics:` block is set).
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
        launch_arguments={
            "scenario": scenario,
            "ekf_publish_enabled": LaunchConfiguration("ekf_publish_enabled"),
        }.items(),
    )

    # Latched mission autostart (one long-lived publisher holding /path and the
    # start command transient_local for the launch lifetime). DO_NOTHING takes
    # no parameters, so we only pass mission_id; gated internally on
    # mission_autostart.
    mission_autostart_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    FindPackageShare("py_pkg").find("py_pkg"),
                    "launch",
                    "mission_autostart.launch.py",
                )
            ]
        ),
        launch_arguments={
            "mission_autostart": LaunchConfiguration("mission_autostart"),
            "mission_id": str(_MISSION_ID_DO_NOTHING),
        }.items(),
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
                    "If true, the launch publishes the Do-Nothing MissionCommand "
                    "(mission_id=3) plus `start` ~8 s after bringup, which also "
                    "resets the controllers to their fresh, no-mission state. "
                    "Either way the control commands nothing."
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
                    "Informational: DO_NOTHING never self-terminates, so the "
                    "launch holds either way. Documents intent when running from CLI."
                ),
            ),
            DeclareLaunchArgument(
                "ekf_publish_enabled",
                default_value="false",
                description=(
                    "Forwarded to control_stack.launch.py. Defaulted off "
                    "while the EKF is being tuned: /position/estimation "
                    "stays silent, the depth + ACU-pitch loops keep "
                    "running (they don't read it), and the ACU-roll loop "
                    "sits at its init value (0 deg) and commands ~0 "
                    "instead of railing on bad EKF output. Flip true once "
                    "the EKF is trusted."
                ),
            ),
            DeclareLaunchArgument(
                "record",
                default_value="false",
                description="If true, also record HAL topics to an MCAP rosbag.",
            ),
            DeclareLaunchArgument(
                "run_id",
                default_value="do_nothing",
                description=(
                    "Run identifier baked into the bag output dir as "
                    "./sim_data/[{sampler_id}/]{run_id}_{timestamp}/raw."
                ),
            ),
            DeclareLaunchArgument(
                "sampler_id",
                default_value="",
                description=(
                    "Optional parent folder for grouping bags from one sampler "
                    "invocation. Empty (default) preserves the historical layout."
                ),
            ),
            DeclareLaunchArgument(
                "bag_path",
                default_value="",
                description=(
                    "Explicit bag output directory; overrides the "
                    "sampler_id/run_id synthesis. Sweep runners set this so "
                    "they can post-process the bag deterministically."
                ),
            ),
            DeclareLaunchArgument(
                "bag_compression",
                default_value="file",
                description=(
                    "Rosbag2 compression mode. 'file' compresses each MCAP at "
                    "shutdown (default); 'none' disables it so a SIGKILL during "
                    "teardown can't strip metadata.yaml or leave half-finalized "
                    "files. Sweep runners pass 'none' and compress after each reap."
                ),
            ),
            bridge_launch,
            OpaqueFunction(function=_build_robot_launch),
            control_stack_launch,
            mission_autostart_launch,
        ]
    )
