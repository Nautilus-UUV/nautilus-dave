"""Fault injection for HAL bridges.

Each bridge owns one or more injectors. The base class handles the
random-trigger timer and the continuous 10 Hz state telemetry publish;
subclasses define how the current degradation level mutates the data
flowing through `apply()`.

The model is a monotonic degradation ladder: an actuator walks down a
fixed number of effectiveness steps (100 % -> 0 % in `num_levels`
equal drops) and never recovers. Each step is an independent failure
event drawn from a Poisson process with mean `mttf_sec` (the mean time
between successive degradation steps), so the wait between every step
has the same distribution. Once a level is reached it latches; the
actuator can only get worse.

RNG injection: pass a seeded `random.Random` if you need
reproducibility (MC runs, sim-integration tests). Default
`random.Random()` keeps non-deterministic behaviour for ad-hoc sim
runs.
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod

from rclpy.node import Node
from std_msgs.msg import Int32


class BaseFaultInjector(ABC):
    def __init__(
        self,
        node: Node,
        fault_topic: str,
        mttf_sec: float,
        num_levels: int = 5,
        rng: random.Random | None = None,
        tick_period_sec: float = 1.0,
    ):
        self.node = node
        # Degradation level: 0 = healthy (100 %), num_levels = fully broken (0 %).
        # Monotonically non-decreasing — there is no recovery path.
        self.level = 0
        self.num_levels = num_levels

        # Per-tick step probability from the Poisson inter-arrival model:
        # an event with mean mttf_sec, sampled once per tick_period_sec, trips
        # with probability 1 - exp(-tick/mttf). mttf <= 0 disables stepping so
        # the actuator stays healthy forever (the nominal, fault-free case).
        self.mttf_sec = mttf_sec
        if mttf_sec > 0:
            self._step_prob = 1.0 - math.exp(-tick_period_sec / mttf_sec)
        else:
            self._step_prob = 0.0

        # An explicit, seeded RNG makes per-injector fault timing
        # reproducible. Falling back to `random.Random()` preserves
        # non-deterministic behaviour when nobody passes one in.
        self.rng = rng if rng is not None else random.Random()

        self.fault_pub = self.node.create_publisher(Int32, fault_topic, 10)

        self.trigger_check_timer = self.node.create_timer(
            tick_period_sec, self._maybe_degrade
        )
        self.state_pub_timer = self.node.create_timer(0.1, self._publish_state)

    def _maybe_degrade(self):
        if self.level < self.num_levels and self.rng.random() < self._step_prob:
            self.level += 1
            self.node.get_logger().warn(
                f"Degradation on {self.fault_pub.topic_name}: "
                f"level {self.level}/{self.num_levels} "
                f"({self.effectiveness() * 100:.0f}% effectiveness)"
            )

    def effectiveness(self) -> float:
        """Fraction of commanded actuation that survives the current level.

        Level 0 -> 1.0, level num_levels -> 0.0, linear in between. With
        num_levels=5 this is the 100/80/60/40/20/0 % ladder.
        """
        return (self.num_levels - self.level) / self.num_levels

    def _publish_state(self):
        self.fault_pub.publish(Int32(data=self.level))

    @abstractmethod
    def apply(self, data):
        """Mutate incoming data according to the current degradation level."""
        pass


class BCUFaultInjector(BaseFaultInjector):
    """Pump RPM degradation: scales the commanded RPM by the effectiveness."""

    def apply(self, rpm: float) -> float:
        return rpm * self.effectiveness()
