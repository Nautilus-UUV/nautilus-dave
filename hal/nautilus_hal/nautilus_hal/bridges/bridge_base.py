"""Shared base for the Nautilus HAL sim bridges.

Each concrete bridge declares the parameters it actually consumes via
``self.declare_parameter`` in ``setup_bridges``; defaults come from
``py_pkg.scenarios.spec.rig`` and ultimately from
``py_pkg.robot_specs``. The standalone ``ros2 run`` path therefore
matches today's behaviour without needing a YAML overlay.

Centralising the SIGINT-tolerant spin loop here is what
``run_bridge`` does.
"""

from typing import Type

import rclpy
from rclpy.exceptions import InvalidHandle
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class SimBridgeNode(Node):
    """Template Method base — subclasses declare params in setup_bridges."""

    def __init__(self, node_name: str) -> None:
        super().__init__(node_name)
        self.setup_bridges()

    def setup_bridges(self) -> None:
        """Subclass hook: declare parameters, publishers, subscribers, timers."""
        raise NotImplementedError


def run_bridge(node_cls: Type[SimBridgeNode], args=None) -> None:
    """SIGINT/SIGTERM-tolerant entrypoint shared by every bridge ``main``.

    Without this, launch_testing's exit-code check intermittently fails
    on Ctrl-C. ``InvalidHandle`` is also swallowed: when SIGTERM arrives
    while a timer or subscription callback is mid-publish, the
    publisher's underlying handle can be torn down before the publish
    completes. The bridge with the busiest shutdown window
    (bcu_sim_bridge — 10 Hz pub_timer plus rpm_callback both publishing)
    hit this often enough to flake the test.

    ``RuntimeError`` is also caught: rclpy.executors._take_subscription
    calls into pybind11's ``handle.take_message`` while the executor
    still has a pending wait on a subscription whose handle is being
    torn down by the SIGINT path. pybind11 raises a bare RuntimeError
    ("Unable to convert call argument '0' to Python object") which
    otherwise leaks out as exit code 1.
    """
    rclpy.init(args=args)
    node = node_cls()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException, InvalidHandle, RuntimeError):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
