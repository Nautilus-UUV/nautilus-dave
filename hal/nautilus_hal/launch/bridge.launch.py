import os
from datetime import datetime

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node


def _sim_data_root():
    # Inside our container the workspace mounts at /ros2_ws, so absolute
    # paths are sane; on the host we leave it relative so bags land next
    # to whatever cwd the operator launched from (usually the workspace
    # root).
    if (
        os.path.exists("/.dockerenv")
        or "APPTAINER_CONTAINER" in os.environ
        or "SINGULARITY_CONTAINER" in os.environ
    ):
        return "/ros2_ws/sim_data"
    return "./sim_data"


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory("nautilus_hal"), "config", "nautilus_params.yaml"
    )

    # Resolved once per launch invocation so every consumer of the default
    # bag_path sees the same timestamp string.
    timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    sim_data_root = _sim_data_root()

    record_arg = DeclareLaunchArgument(
        "record",
        default_value="false",
        description=(
            "If true, record the six HAL-published topics to an MCAP rosbag "
            "alongside the bridges."
        ),
    )
    # run_id is the user-facing knob for naming the per-run directory; the
    # higher-level sim launches (sawtooth/surface/trim/unified) set this to
    # the mission name so bags self-document. bag_path overrides the whole
    # thing if you want to dump somewhere completely custom.
    run_id_arg = DeclareLaunchArgument(
        "run_id",
        default_value="dive",
        description=(
            "Run identifier baked into the bag output dir as "
            "./sim_data/{run_id}_{timestamp}/raw."
        ),
    )
    bag_path_arg = DeclareLaunchArgument(
        "bag_path",
        default_value=[
            TextSubstitution(text=f"{sim_data_root}/"),
            LaunchConfiguration("run_id"),
            TextSubstitution(text=f"_{timestamp}/raw"),
        ],
        description="Full output directory for the rosbag; overrides run_id-based default.",
    )

    return LaunchDescription(
        [
            record_arg,
            run_id_arg,
            bag_path_arg,
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
            Node(
                package="nautilus_hal",
                executable="acu_sim_bridge",
                name="nautilus_acu_bridge",
                output="screen",
                parameters=[config],
            ),
            # Optional rosbag recording — gated on record:=true. Topic list
            # matches what UG-anomaly_detection's downstream pipeline expects.
            # /bcu/rpm/fault is sim-only (fault injector diagnostic) so it
            # stays as a literal here rather than going through UUVTopics.
            ExecuteProcess(
                condition=IfCondition(LaunchConfiguration("record")),
                cmd=[
                    "ros2",
                    "bag",
                    "record",
                    "-o",
                    LaunchConfiguration("bag_path"),
                    "-s",
                    "mcap",
                    "--compression-mode",
                    "file",
                    "--compression-format",
                    "zstd",
                    "/imu/left",
                    "/external/pressure",
                    "/bcu/rpm",
                    "/bcu/flow_rate",
                    "/bcu/pressure",
                    "/bcu/rpm/fault",
                ],
                output="screen",
            ),
        ]
    )
