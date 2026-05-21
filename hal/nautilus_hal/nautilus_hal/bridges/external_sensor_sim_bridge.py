from py_pkg.scenarios.spec.rig import ExternalSensorBridgeSpec, SimSpec
from py_pkg.uuv_ros_core import UUVTopics, create_publisher_for_topic
from sensor_msgs.msg import FluidPressure
from std_msgs.msg import Int32

from ..constants import SimTopics, sea_pressure_pa
from .bridge_base import SimBridgeNode, run_bridge


class ExternalSensorSimBridge(SimBridgeNode):
    def __init__(self):
        super().__init__("nautilus_external_sensor_bridge")

    def setup_bridges(self):
        self.declare_parameter("model_name", SimSpec().model_name)
        self.declare_parameter(
            "publish_rate_hz", ExternalSensorBridgeSpec().publish_rate_hz
        )
        self.model_name = self.get_parameter("model_name").value
        self.latest_pressure = 0
        publish_rate_hz = self.get_parameter("publish_rate_hz").value
        self.pub_timer = self.create_timer(1.0 / publish_rate_hz, self.publish_at_rate)

        self.pressure_pub = create_publisher_for_topic(
            self, UUVTopics.EXTERNAL_PRESSURE
        )
        self.sim_pressure_sub = self.create_subscription(
            FluidPressure,
            SimTopics.SEA_PRESSURE.format(model_name=self.model_name),
            self.sim_external_pressure_callback,
            10,
        )

        self.get_logger().info(
            f"Nautilus Sensor Bridge: Listening for sea pressure on "
            f"{SimTopics.SEA_PRESSURE.format(model_name=self.model_name)}"
        )

    def sim_external_pressure_callback(self, msg):
        self.latest_pressure = sea_pressure_pa(msg.fluid_pressure)

    def publish_at_rate(self):
        """Publish external sensors."""
        pressure_msg = Int32(data=self.latest_pressure)
        self.pressure_pub.publish(pressure_msg)


def main(args=None):
    run_bridge(ExternalSensorSimBridge, args)


if __name__ == "__main__":
    main()
