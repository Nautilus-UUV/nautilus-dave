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
    """
    Abstract base class for ROS2 fault injection.
    Handles continuous 10Hz telemetry and state management.
    """

    def __init__(
        self,
        node: Node,
        fault_topic: str,
        fault_probability: float = 0.05,
        fault_duration_sec: float = 5.0,
    ):
        self.node = node
        self.state = FaultState.NORMAL

        self.fault_probability = fault_probability
        self.fault_duration_sec = fault_duration_sec
        self.fault_timer = None

        self.fault_pub = self.node.create_publisher(Int32, fault_topic, 10)

        self.trigger_check_timer = self.node.create_timer(
            1.0, self._random_trigger_check
        )
        # Re-introduce continuous 10Hz publishing
        self.state_pub_timer = self.node.create_timer(0.1, self._publish_state)

    def _random_trigger_check(self):
        if self.state == FaultState.NORMAL and random.random() < self.fault_probability:
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
        """
        Hook method. Child classes can override this to mask or alter
        the broadcasted state based on transient data conditions.
        """
        return self.state

    def _publish_state(self):
        msg = Int32()
        # Evaluate the effective state before publishing
        msg.data = self.get_telemetry_state().value
        self.fault_pub.publish(msg)

    @abstractmethod
    def apply(self, data):
        """
        Must be implemented by child classes.
        Defines how the current fault state mutates the incoming data.
        """
        pass


class BCUFaultInjector(BaseFaultInjector):
    """
    Specific implementation for RPM faults with telemetry masking.
    """

    def __init__(
        self,
        node: Node,
        fault_topic: str,
        fault_probability: float,
        fault_duration_sec: float,
    ):
        super().__init__(
            node,
            fault_topic,
            fault_probability=fault_probability,
            fault_duration_sec=fault_duration_sec,
        )
        self.current_rpm = 0.0

    def get_telemetry_state(self) -> FaultState:
        if abs(self.current_rpm) < 1e-6:
            return FaultState.NORMAL

        return self.state

    def apply(self, rpm: float) -> float:
        self.current_rpm = rpm
        effective_state = self.get_telemetry_state()

        if effective_state == FaultState.NORMAL:
            return rpm
        elif effective_state == FaultState.DEGRADED:
            return rpm * 0.5
        elif effective_state == FaultState.SEVERE:
            return 0.0
        return rpm
