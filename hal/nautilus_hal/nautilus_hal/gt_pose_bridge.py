"""Ground-truth pose bridge -- sim-only diagnostic.

Re-publishes Gazebo's ``/model/<model_name>/odometry`` (already bridged
out by ``dave_robot_models/config/glider_nautilus/robot_config.py``) onto
``UUVTopics.POSITION_ESTIMATION``. Lets sim tests (e.g.
``test_trim_neutral_sim_gt``, ``test_sawtooth_sim_gt``) exercise the
depth + ACU + pathfinding stack against perfect pose, isolating
controller behaviour from the EKF's known orientation drift
(``src/nautilus-ros/docs/ekf_node_issues.md``).

Spawn-frame translation: the model is spawned with non-identity
roll/yaw (see ``trim_sim.launch.py`` etc. -- typically ``roll=pi``,
``yaw=pi/2``) so that its body axes line up with the world axes the
operator wants. The raw GT odometry orientation reflects that spawn
quaternion, which means a downstream consumer using ZYX Tait-Bryan
extraction (``acu_node`` does) reads ``current_roll = 180 deg`` at
t=0 and starts fighting a phantom -180 deg roll error -- producing
side drift and gimbal-coupled pitch readings.

To match what the production EKF will deliver (orientation relative to
the body's initial frame), this bridge captures the first odom
quaternion as the spawn frame and republishes every subsequent message
as ``q_spawn^-1 * q_current`` -- the body's rotation since spawn. The
position field is not re-zeroed (the depth controller ignores it and
pathfinding's trim mission captures spawn x/y itself).

Not for hardware -- production replaces this with the real EKF stack.
"""

from nav_msgs.msg import Odometry
from py_pkg.uuv_ros_core import UUVTopics, create_publisher_for_topic

from .bridge_base import SimBridgeNode, run_bridge
from .constants import SimTopics


def _quat_inverse(q):
    """Inverse of a unit quaternion (qx, qy, qz, qw)."""
    qx, qy, qz, qw = q
    return (-qx, -qy, -qz, qw)


def _quat_multiply(a, b):
    """Hamilton product a * b for quaternions in (qx, qy, qz, qw) order."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


class GTPoseBridge(SimBridgeNode):
    def __init__(self):
        super().__init__("nautilus_gt_pose_bridge")
        self._spawn_q_inv: tuple | None = None

    def setup_bridges(self):
        # Factory matches POSITION_ESTIMATION's UUVQoS.CONTROL profile so
        # acu_node and pathfinding_node's existing subscriptions accept it
        # without a durability/reliability mismatch.
        self.pose_pub = create_publisher_for_topic(self, UUVTopics.POSITION_ESTIMATION)

        # parameter_bridge defaults: reliable, depth=10. Match here.
        self.odom_sub = self.create_subscription(
            Odometry,
            SimTopics.ODOMETRY.format(model_name=self.model_name),
            self._on_odometry,
            10,
        )

        self.get_logger().info(
            f"GT pose bridge: {SimTopics.ODOMETRY.format(model_name=self.model_name)} "
            f"-> {UUVTopics.POSITION_ESTIMATION} "
            f"(spawn-frame translated)"
        )

    def _on_odometry(self, msg: Odometry) -> None:
        q = msg.pose.pose.orientation
        current = (q.x, q.y, q.z, q.w)

        if self._spawn_q_inv is None:
            self._spawn_q_inv = _quat_inverse(current)
            self.get_logger().info(
                f"Captured spawn quaternion {current}; subsequent "
                "POSITION_ESTIMATION will be relative to this frame."
            )

        rx, ry, rz, rw = _quat_multiply(self._spawn_q_inv, current)

        out = msg.pose.pose
        out.orientation.x = rx
        out.orientation.y = ry
        out.orientation.z = rz
        out.orientation.w = rw
        self.pose_pub.publish(out)


def main(args=None):
    run_bridge(GTPoseBridge, args)


if __name__ == "__main__":
    main()
