"""Generic rate-limiter used only to slow topics down before bag recording.

The IMU sensor (50 Hz) and the gz odometry publisher (100 Hz) legitimately
need to run fast for the estimator and for GT comparison, so the live streams stay
untouched. This node subscribes to one of those streams, caches the latest
message, and republishes it on a sibling topic at a fixed rate. The bag
recorder then points at the sibling, which keeps the recorded set uniform
with the 10 Hz BCU/external_sensor bridges.

Parameters:
    input_topic  = topic to subscribe to (e.g. ``/imu``)
    output_topic = throttled topic to publish on (e.g. ``/imu/throttled``)
    rate_hz      = output publish rate
    msg_type     = fully-qualified message type, e.g. ``sensor_msgs/msg/Imu``
"""

from importlib import import_module

from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from .bridge_base import SimBridgeNode, run_bridge


def _resolve_msg_type(type_str: str):
    pkg, kind, name = type_str.split("/")
    module = import_module(f"{pkg}.{kind}")
    return getattr(module, name)


class RecordThrottle(SimBridgeNode):
    def __init__(self):
        super().__init__("nautilus_record_throttle")

    def setup_bridges(self):
        self.declare_parameter("input_topic", "")
        self.declare_parameter("output_topic", "")
        self.declare_parameter("rate_hz", 10.0)
        self.declare_parameter("msg_type", "")

        input_topic = self.get_parameter("input_topic").value
        output_topic = self.get_parameter("output_topic").value
        rate_hz = float(self.get_parameter("rate_hz").value)
        msg_type_str = self.get_parameter("msg_type").value

        if not input_topic or not output_topic or not msg_type_str:
            raise ValueError(
                "record_throttle requires input_topic, output_topic, and msg_type"
            )

        msg_type = _resolve_msg_type(msg_type_str)
        self._latest = None

        # Subscribe BEST_EFFORT so we match both best-effort sensor publishers
        # (e.g. /imu on SENSOR_STREAM) and reliable ones — DDS allows a
        # best-effort request to bind to a reliable offer, but not the reverse.
        sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self._sub = self.create_subscription(msg_type, input_topic, self._on_msg, sub_qos)
        self._pub = self.create_publisher(msg_type, output_topic, 10)
        self._timer = self.create_timer(1.0 / rate_hz, self._tick)

        self.get_logger().info(
            f"record_throttle: {input_topic} -> {output_topic} @ {rate_hz} Hz "
            f"({msg_type_str})"
        )

    def _on_msg(self, msg):
        self._latest = msg

    def _tick(self):
        if self._latest is not None:
            self._pub.publish(self._latest)


def main(args=None):
    run_bridge(RecordThrottle, args)


if __name__ == "__main__":
    main()
