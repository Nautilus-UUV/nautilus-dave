import rclpy
from py_pkg.uuv_ros_core import UUVTopics, create_publisher_for_topic
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import FluidPressure
from std_msgs.msg import Int32

from .constants import SimTopics


class ExternalSensorSimBridge(Node):
    def __init__(self):
        super().__init__(
            "nautilus_external_sensor_bridge",
            automatically_declare_parameters_from_overrides=True,
            allow_undeclared_parameters=True,
        )

        model_name = self.get_parameter("model_name").value

        self.latest_pressure = 0
        # 10 Hz frequency for publishing external sensors
        self.pub_timer = self.create_timer(0.1, self.publish_at_rate)

        self.pressure_pub = create_publisher_for_topic(
            self, UUVTopics.EXTERNAL_PRESSURE
        )
        self.sim_pressure_sub = self.create_subscription(
            FluidPressure,
            SimTopics.SEA_PRESSURE.format(model_name=model_name),
            self.sim_external_pressure_callback,
            10,
        )

        self.get_logger().info(
            f"Nautilus Sensor Bridge: Listening for sea pressure on "
            f"{SimTopics.SEA_PRESSURE.format(model_name=model_name)}"
        )

    def sim_external_pressure_callback(self, msg):
        """Cache the latest sea pressure (Pa) for periodic republishing.

        The dave sea_pressure_sensor plugin fills FluidPressure.fluid_pressure
        in kPa (its internal `standardPressure` is 101.325 and gradient
        `kPaPerM` is 9.80638). FluidPressure semantics require Pa, so scale
        here — downstream consumers can trust /external/pressure as true Pa.
        """
        self.latest_pressure = int(msg.fluid_pressure * 1000.0)

    def publish_at_rate(self):
        """Publish external sensors."""
        pressure_msg = Int32(data=self.latest_pressure)
        self.pressure_pub.publish(pressure_msg)


def main(args=None):
    # Catch SIGINT/SIGTERM so the process exits 0 instead of 1 on Ctrl-C —
    # otherwise launch_testing's exit-code check intermittently fails.
    rclpy.init(args=args)
    node = ExternalSensorSimBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
