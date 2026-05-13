"""Fault injection for HAL bridges.

Each bridge owns one or more injectors. The base class handles the
random-trigger timer, the duration timer, and the continuous 10 Hz
state telemetry publish; subclasses define how the fault state mutates
the data flowing through `apply()`.

RNG injection: pass a seeded `random.Random` if you need
reproducibility (MC runs, sim-integration tests). Default
`random.Random()` keeps today's non-deterministic behaviour for ad-hoc
sim runs.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from enum import IntEnum

from rclpy.node import Node
from std_msgs.msg import Int32


class FaultState(IntEnum):
    NORMAL = 0
    DEGRADED = 1
    SEVERE = 2


class BaseFaultInjector(ABC):
    def __init__(
        self,
        node: Node,
        fault_topic: str,
        fault_probability: float = 0.05,
        fault_duration_sec: float = 5.0,
        degraded_factor: float = 0.5,
        severe_factor: float = 0.0,
        rng: random.Random | None = None,
    ):
        self.node = node
        self.state = FaultState.NORMAL

        self.fault_probability = fault_probability
        self.fault_duration_sec = fault_duration_sec
        self.degraded_factor = degraded_factor
        self.severe_factor = severe_factor
        self.fault_timer = None
        # An explicit, seeded RNG makes per-injector fault timing
        # reproducible. Falling back to `random.Random()` preserves
        # today's behaviour when nobody passes one in.
        self.rng = rng if rng is not None else random.Random()

        self.fault_pub = self.node.create_publisher(Int32, fault_topic, 10)

        self.trigger_check_timer = self.node.create_timer(
            1.0, self._random_trigger_check
        )
        self.state_pub_timer = self.node.create_timer(0.1, self._publish_state)

    def _random_trigger_check(self):
        if (
            self.state == FaultState.NORMAL
            and self.rng.random() < self.fault_probability
        ):
            self.trigger_fault(FaultState.DEGRADED, self.fault_duration_sec)

    def trigger_fault(self, target_state: FaultState, duration: float):
        self.state = target_state
        self.node.get_logger().warn(
            f"Fault injected on {self.fault_pub.topic_name}: {self.state.name} for {duration}s"
        )

        if self.fault_timer is not None:
            self.fault_timer.cancel()
        self.fault_timer = self.node.create_timer(duration, self.clear_fault)

    def clear_fault(self):
        self.state = FaultState.NORMAL
        self.node.get_logger().info(
            f"Fault cleared on {self.fault_pub.topic_name}. Returned to NORMAL."
        )
        if self.fault_timer is not None:
            self.fault_timer.cancel()
            self.fault_timer = None

    def get_telemetry_state(self) -> FaultState:
        """Hook — subclasses can mask state based on transient data."""
        return self.state

    def _publish_state(self):
        msg = Int32()
        msg.data = self.get_telemetry_state().value
        self.fault_pub.publish(msg)

    @abstractmethod
    def apply(self, data):
        """Mutate incoming data according to the current fault state."""
        pass


class BCUFaultInjector(BaseFaultInjector):
    """RPM fault injector with idle-state telemetry masking."""

    def __init__(
        self,
        node: Node,
        fault_topic: str,
        fault_probability: float,
        fault_duration_sec: float,
        degraded_factor: float = 0.5,
        severe_factor: float = 0.0,
        rng: random.Random | None = None,
    ):
        super().__init__(
            node,
            fault_topic,
            fault_probability=fault_probability,
            fault_duration_sec=fault_duration_sec,
            degraded_factor=degraded_factor,
            severe_factor=severe_factor,
            rng=rng,
        )
        self.current_rpm = 0.0

    def get_telemetry_state(self) -> FaultState:
        # When the pump isn't running the fault is invisible; report
        # NORMAL so external observers don't see a phantom degraded
        # state on a quiescent bus.
        if abs(self.current_rpm) < 1e-6:
            return FaultState.NORMAL
        return self.state

    def apply(self, rpm: float) -> float:
        self.current_rpm = rpm
        effective_state = self.get_telemetry_state()

        if effective_state == FaultState.NORMAL:
            return rpm
        if effective_state == FaultState.DEGRADED:
            return rpm * self.degraded_factor
        if effective_state == FaultState.SEVERE:
            return rpm * self.severe_factor
        return rpm
