from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    namespace = LaunchConfiguration("namespace").perform(context)
    use_ardusub = LaunchConfiguration("use_ardusub")

    thruster_joints = []
    for thruster in range(1, 7):
        thruster_joints.append(f"/model/{namespace}/joint/thruster{thruster}_joint")

    bluerov2_arguments = (
        [
            f"{joint}/cmd_thrust@std_msgs/msg/Float64@gz.msgs.Double"
            for joint in thruster_joints
        ]
        + [
            f"{joint}/ang_vel@std_msgs/msg/Float64@gz.msgs.Double"
            for joint in thruster_joints
        ]
        + [
            f"{joint}/enable_deadband@std_msgs/msg/Bool@gz.msgs.Boolean"
            for joint in thruster_joints
        ]
        + [
            f"/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock",
            f"/model/{namespace}/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry",
            f"/model/{namespace}/odometry_with_covariance@nav_msgs/msg/Odometry@gz.msgs.OdometryWithCovariance",
            f"/model/{namespace}/pose@geometry_msgs/msg/PoseArray@gz.msgs.Pose_V",
            f"/model/{namespace}/imu@sensor_msgs/msg/Imu@gz.msgs.IMU",
            f"/model/{namespace}/magnetometer@sensor_msgs/msg/MagneticField@gz.msgs.Magnetometer",
            f"/model/{namespace}/camera/image@sensor_msgs/msg/Image@gz.msgs.Image",
            f"/model/{namespace}/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
        ]
    )

    bluerov2_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=bluerov2_arguments,
        output="screen",
    )

    mavros_file = LaunchConfiguration("mavros_file")
    ardusub_params = LaunchConfiguration("ardusub_params")
    ardusub_model = LaunchConfiguration("ardusub_model")
    ardusub_home = LaunchConfiguration("ardusub_home")

    imu_wait_cmd = (
        "while true; do "
        f'if gz topic -l | grep -q "/model/{namespace}/imu"; then exit 0; fi; '
        "sleep 1; "
        "done"
    )

    wait_for_imu_topic = ExecuteProcess(
        cmd=[
            "/usr/bin/env",
            "bash",
            "-lc",
            imu_wait_cmd,
        ],
        output="screen",
        condition=IfCondition(use_ardusub),
    )

    ardusub_process = ExecuteProcess(
        cmd=[
            "ardusub",
            "-w",
            "--model",
            ardusub_model,
            "--defaults",
            ardusub_params,
            "-IO",
            "--home",
            ardusub_home,
        ],
        output="screen",
        condition=IfCondition(use_ardusub),
    )

    fcu_wait_cmd = (
        "if command -v nc >/dev/null 2>&1; then "
        "while true; do nc -z 127.0.0.1 5760 && exit 0; sleep 1; done; "
        "else "
        "while true; do "
        "(echo >/dev/tcp/127.0.0.1/5760) >/dev/null 2>&1 && exit 0; "
        "sleep 1; "
        "done; "
        "fi"
    )

    wait_for_fcu_port = ExecuteProcess(
        cmd=[
            "/usr/bin/env",
            "bash",
            "-lc",
            fcu_wait_cmd,
        ],
        output="screen",
        condition=IfCondition(use_ardusub),
    )

    mavros_node = Node(
        package="mavros",
        executable="mavros_node",
        output="screen",
        parameters=[mavros_file, {"use_sim_time": True}],
        condition=IfCondition(use_ardusub),
    )

    start_imu_wait = RegisterEventHandler(
        OnProcessStart(
            target_action=bluerov2_bridge,
            on_start=[wait_for_imu_topic],
        )
    )

    start_ardusub = RegisterEventHandler(
        OnProcessExit(
            target_action=wait_for_imu_topic,
            on_exit=[
                LogInfo(msg="Gazebo IMU topic detected, launching ArduSub"),
                ardusub_process,
            ],
        )
    )

    start_fcu_wait = RegisterEventHandler(
        OnProcessStart(
            target_action=ardusub_process,
            on_start=[wait_for_fcu_port],
        )
    )

    start_mavros = RegisterEventHandler(
        OnProcessExit(
            target_action=wait_for_fcu_port,
            on_exit=[
                LogInfo(msg="ArduSub FCU port ready, launching MAVROS"),
                mavros_node,
            ],
        )
    )

    return [
        bluerov2_bridge,
        start_imu_wait,
        start_ardusub,
        start_fcu_wait,
        start_mavros,
    ]


def generate_launch_description():
    args = [
        DeclareLaunchArgument(
            "namespace",
            default_value="bluerov2",
            description="Namespace",
        ),
        DeclareLaunchArgument(
            "mavros_file",
            default_value=PathJoinSubstitution(
                [
                    FindPackageShare("dave_robot_models"),
                    "config",
                    "mavros",
                    "mavros.yaml",
                ]
            ),
            description="Path to mavros.yaml file",
        ),
        DeclareLaunchArgument(
            "use_ardusub",
            default_value="true",
            description="Launch ArduSub SITL and MAVROS",
        ),
        DeclareLaunchArgument(
            "ardusub_params",
            default_value=PathJoinSubstitution(
                [
                    FindPackageShare("dave_robot_models"),
                    "config",
                    "bluerov2",
                    "ardusub.parm",
                ]
            ),
            description="Path to ardusub.parm file",
        ),
        DeclareLaunchArgument(
            "ardusub_model",
            default_value="JSON:127.0.0.1",
            description="ArduSub SITL physics backend model string",
        ),
        DeclareLaunchArgument(
            "ardusub_home",
            default_value="35.074823,129.084798,0.0,270.0",
            description="ArduSub HOME argument (lat,lon,alt,heading)",
        ),
    ]

    return LaunchDescription(args + [OpaqueFunction(function=launch_setup)])
