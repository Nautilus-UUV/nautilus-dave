import rclpy
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_publisher_for_topic,
    create_subscription_for_topic,
)
from rclpy.node import Node
from std_msgs.msg import Float32, Float64, Int32

from .constants import Conversions, SimTopics
from .fault_injection import BCUFaultInjector


class BCUSimBridge(Node):
    def __init__(self):
        super().__init__(
            "nautilus_bcu_bridge",
            automatically_declare_parameters_from_overrides=True,
            allow_undeclared_parameters=True,
        )

        # Directly access parameters from the YAML overrides.
        model_name = self.get_parameter("model_name").value
        self.m3_per_rev = self.get_parameter("m3_per_rev").value
        self.max_capacity = self.get_parameter("max_capacity_m3").value
        self.min_capacity = self.get_parameter("min_capacity_m3").value
        self.fault_probability = self.get_parameter("fault_probability_bcu").value
        self.fault_duration_sec = self.get_parameter("fault_duration_sec_bcu").value

        self.current_volume = 0.0

        # ====================
        # Fault Injection
        # ====================
        self.rpm_fault_injector = BCUFaultInjector(
            self,
            fault_topic="/bcu/rpm/fault",
            fault_probability=self.fault_probability,
            fault_duration_sec=self.fault_duration_sec,
        )

        # ====================
        # BCU RPM/flow control
        # ====================
        self.last_time = self.get_clock().now()
        self.rpm_sub = create_subscription_for_topic(
            self, UUVTopics.BCU_RPM, self.rpm_callback
        )
        self.flow_pub = create_publisher_for_topic(self, UUVTopics.BCU_FLOW_RATE)

        # ==============
        # BCU pressure
        # ==============
        self.latest_volume = 0  # in mL
        # 10 Hz pub timer to throttle data
        self.pub_timer = self.create_timer(0.1, self.publish_at_rate)
        self.bcu_pressure_pub = create_publisher_for_topic(self, UUVTopics.BCU_PRESSURE)
        self.sim_current_volume_sub = self.create_subscription(
            Float64,
            SimTopics.BUOYANCY_VOLUME_STATE.format(model_name=model_name),
            self.sim_bcu_volume_callback,
            10,
        )

        self.sim_volume_pub = self.create_publisher(
            Float64, SimTopics.BUOYANCY_COMMAND.format(model_name=model_name), 10
        )

        self.get_logger().info(f"Nautilus BCU Bridge: Listening on {UUVTopics.BCU_RPM}")

    def rpm_callback(self, msg):

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        raw_rpm = float(msg.data)
        rpm = self.rpm_fault_injector.apply(raw_rpm)

        # rpm -> rps -> total revs in dt -> volume change
        rps = rpm / 60.0
        delta_vol = rps * self.m3_per_rev * dt

        self.current_volume += delta_vol
        self.current_volume = max(
            self.min_capacity, min(self.current_volume, self.max_capacity)
        )

        out_msg = Float64()
        out_msg.data = self.current_volume
        self.sim_volume_pub.publish(out_msg)

        # Mock Flow Rate feedback (m3/s)
        flow_msg = Float32()
        flow_msg.data = rps * self.m3_per_rev
        self.flow_pub.publish(flow_msg)

    def sim_bcu_volume_callback(self, msg):
        # Volume (m3) to milliliters (mL) as integer
        self.latest_volume = int(msg.data * Conversions.M3_TO_ML)

    def publish_at_rate(self):
        bcu_pressure_msg = Int32(data=self.latest_volume)
        self.bcu_pressure_pub.publish(bcu_pressure_msg)


def main(args=None):
    rclpy.init(args=args)
    node = BCUSimBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
