"""Shared base for the Nautilus HAL sim bridges.

Every ``*_sim_bridge`` node loads ``nautilus_params.yaml`` and reads
``model_name`` (and sometimes ``world_name``) from the merged ``/**``
overrides, then enters the same SIGINT-tolerant spin loop. Centralising
that here means each concrete bridge only declares its topic wiring
in ``setup_bridges``.
"""

from typing import Type

import rclpy
from rclpy.exceptions import InvalidHandle
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class SimBridgeNode(Node):
    """Template Method base for the HAL sim bridges.

    Reads ``model_name`` from YAML overrides and exposes it as
    ``self.model_name``. ``world_name`` is read lazily on demand because
    only the ACU bridge needs it.
    """

    def __init__(self, node_name: str) -> None:
        super().__init__(
            node_name,
            automatically_declare_parameters_from_overrides=True,
            allow_undeclared_parameters=True,
        )
        self.model_name: str = self.get_parameter("model_name").value
        self.setup_bridges()

    @property
    def world_name(self) -> str:
        return self.get_parameter("world_name").value

    def setup_bridges(self) -> None:
        """Subclass hook: declare publishers, subscribers, timers."""
        raise NotImplementedError


def run_bridge(node_cls: Type[SimBridgeNode], args=None) -> None:
    """Standard SIGINT/SIGTERM-tolerant entrypoint.

    Without this, launch_testing's exit-code check intermittently fails
    on Ctrl-C — the underlying ament behaviour the original per-bridge
    ``main()`` blocks were each working around.

    ``InvalidHandle`` is also swallowed: when SIGTERM arrives while a
    timer or subscription callback is mid-publish, the publisher's
    underlying handle can be torn down before the publish completes.
    The bridge with the busiest shutdown window (bcu_sim_bridge — 10 Hz
    pub_timer plus rpm_callback both publishing) hit this often enough
    to flake launch_testing's exit-code check.
    """
    rclpy.init(args=args)
    node = node_cls()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException, InvalidHandle):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
