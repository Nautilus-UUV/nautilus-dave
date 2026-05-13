from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    paused = LaunchConfiguration("paused")
    gui = LaunchConfiguration("gui")
    use_sim_time = LaunchConfiguration("use_sim_time")
    debug = LaunchConfiguration("debug")
    headless = LaunchConfiguration("headless")
    verbose = LaunchConfiguration("verbose")
    namespace = LaunchConfiguration("namespace")
    world_name = LaunchConfiguration("world_name")
    description_file = LaunchConfiguration("description_file")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    z = LaunchConfiguration("z")
    roll = LaunchConfiguration("roll")
    pitch = LaunchConfiguration("pitch")
    yaw = LaunchConfiguration("yaw")
    use_ned_frame = LaunchConfiguration("use_ned_frame")

    if world_name.perform(context) != "empty.sdf":
        world_name = LaunchConfiguration("world_name").perform(context)
        world_filename = f"{world_name}.world"
        world_filepath = PathJoinSubstitution(
            [FindPackageShare("dave_worlds"), "worlds", world_filename]
        )
        gz_args = [world_filepath]
    else:
        gz_args = [world_name]

    # Display control is owned by `headless` alone. `gui` is kept in the
    # arg list for backwards compatibility but must always be `"true"` —
    # repurposing `gui=false` for headless silently broke the gz spawn
    # path in the past, which is why this file no longer gates gz startup
    # on it.
    if headless.perform(context) == "true":
        gz_args.append(" -s")
    if paused.perform(context) == "false":
        gz_args.append(" -r")
    if debug.perform(context) == "true":
        gz_args.append(" -v ")
        gz_args.append(verbose.perform(context))

    # Always include the gz_sim launch — `-s` (added above) selects
    # server-only when `gui=false`. Previously this was gated on
    # `IfCondition(gui)`, which skipped Gazebo entirely in headless mode.
    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [
                        FindPackageShare("ros_gz_sim"),
                        "launch",
                        "gz_sim.launch.py",
                    ]
                )
            ]
        ),
        launch_arguments=[
            ("gz_args", gz_args),
        ],
    )

    # description_file is always forwarded — its default mirrors
    # upload_robot.launch.py's canonical path so the existing flow is
    # bit-identical when no parent overrides. We can't conditionally
    # skip forwarding here: LaunchContext inheritance would still leak
    # this launch's value into upload_robot.launch.py and stomp on its
    # default.
    robot_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [
                        FindPackageShare("dave_robot_models"),
                        "launch",
                        "upload_robot.launch.py",
                    ]
                )
            ]
        ),
        launch_arguments={
            "gui": gui,
            "use_sim_time": use_sim_time,
            "namespace": namespace,
            "description_file": description_file,
            "x": x,
            "y": y,
            "z": z,
            "roll": roll,
            "pitch": pitch,
            "yaw": yaw,
            "use_ned_frame": use_ned_frame,
        }.items(),
    )

    include = [gz_sim_launch, robot_launch]

    return include


def generate_launch_description():

    # Declare the launch arguments with default values
    args = [
        DeclareLaunchArgument(
            "paused",
            default_value="true",
            description="Start the simulation paused",
        ),
        DeclareLaunchArgument(
            "gui",
            default_value="true",
            description="Flag to enable the gazebo gui",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Flag to indicate whether to use simulation time",
        ),
        DeclareLaunchArgument(
            "debug",
            default_value="false",
            description="Flag to enable the gazebo debug flag",
        ),
        DeclareLaunchArgument(
            "headless",
            default_value="false",
            description="Flag to enable the gazebo headless mode",
        ),
        DeclareLaunchArgument(
            "verbose",
            default_value="0",
            description="Adjust level of console verbosity",
        ),
        DeclareLaunchArgument(
            "world_name",
            default_value="empty.sdf",
            description="Gazebo world file to launch",
        ),
        DeclareLaunchArgument(
            "namespace",
            default_value="",
            description="Namespace",
        ),
        DeclareLaunchArgument(
            "x",
            default_value="0.0",
            description="Initial x position",
        ),
        DeclareLaunchArgument(
            "y",
            default_value="0.0",
            description="Initial y position",
        ),
        DeclareLaunchArgument(
            "z",
            default_value="0.0",
            description="Initial z position",
        ),
        DeclareLaunchArgument(
            "roll",
            default_value="0.0",
            description="Initial roll angle",
        ),
        DeclareLaunchArgument(
            "pitch",
            default_value="0.0",
            description="Initial pitch angle",
        ),
        DeclareLaunchArgument(
            "yaw",
            default_value="0.0",
            description="Initial yaw angle",
        ),
        DeclareLaunchArgument(
            "use_ned_frame",
            default_value="false",
            description="Flag to indicate whether to use the north-east-down frame",
        ),
        DeclareLaunchArgument(
            "description_file",
            default_value=PathJoinSubstitution(
                [
                    FindPackageShare("dave_robot_models"),
                    "description",
                    LaunchConfiguration("namespace"),
                    "model.sdf",
                ]
            ),
            description=(
                "Absolute path to the SDF to spawn. Defaults to the "
                "canonical model.sdf in dave_robot_models' share dir. "
                "HAL sim launches override this with a Jinja-rendered "
                "sample variant when the scenario YAML carries a "
                "rig.hydrodynamics block."
            ),
        ),
    ]

    return LaunchDescription(args + [OpaqueFunction(function=launch_setup)])
