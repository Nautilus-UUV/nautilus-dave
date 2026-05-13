import random

from py_pkg.scenarios.spec.rig import (
    BcuBridgeSpec,
    FaultInjectorSpec,
    PlantSpec,
    SimSpec,
)
from py_pkg.uuv_ros_core import (
    UUVTopics,
    create_publisher_for_topic,
    create_subscription_for_topic,
)
from sensor_msgs.msg import FluidPressure
from std_msgs.msg import Float32, Float64, Int32

from ..constants import Conversions, SimTopics, sea_pressure_pa
from ..injectors.fault_injection import BCUFaultInjector
from .bridge_base import SimBridgeNode, run_bridge


class BCUSimBridge(SimBridgeNode):
    def __init__(self):
        super().__init__("nautilus_bcu_bridge")

    def setup_bridges(self):
        # ====================
        # Params (defaults from the scenario dataclass, which mirrors
        # robot_specs at nominal — so ros2 run without a launch wrapper
        # still works exactly like today).
        # ====================
        sim_def = SimSpec()
        plant_def = PlantSpec()
        fault_def = FaultInjectorSpec()
        bridge_def = BcuBridgeSpec()

        self.declare_parameter("model_name", sim_def.model_name)
        self.declare_parameter("volume_per_rev_m3", plant_def.volume_per_rev_m3)
        self.declare_parameter("bladder_min_m3", plant_def.bladder_min_m3)
        self.declare_parameter("bladder_max_m3", plant_def.bladder_max_m3)
        self.declare_parameter(
            "fault_probability_per_sec", fault_def.probability_per_sec
        )
        self.declare_parameter("fault_duration_sec", fault_def.duration_sec)
        self.declare_parameter("fault_degraded_factor", fault_def.degraded_factor)
        self.declare_parameter("fault_severe_factor", fault_def.severe_factor)
        # 0 = "let `random.Random()` pick" — preserves today's
        # non-deterministic behaviour for ad-hoc sim runs. The scenario
        # compiler injects a derived seed for MC.
        self.declare_parameter("rng_seed", 0)
        self.declare_parameter("publish_rate_hz", bridge_def.publish_rate_hz)

        self.model_name = self.get_parameter("model_name").value
        self.volume_per_rev_m3 = self.get_parameter("volume_per_rev_m3").value
        self.bladder_min_m3 = self.get_parameter("bladder_min_m3").value
        self.bladder_max_m3 = self.get_parameter("bladder_max_m3").value

        # Seeded from Gazebo's first BUOYANCY_VOLUME_STATE callback (see
        # sim_bcu_volume_callback). Until then we don't push a volume back
        # to Gazebo — pushing 0.0 + delta would clobber the SDF-initialized
        # bladder state on the first RPM tick.
        self.current_volume = None

        # ====================
        # Fault Injection
        # ====================
        rng_seed = self.get_parameter("rng_seed").value
        rng = random.Random(rng_seed) if rng_seed != 0 else None
        self.rpm_fault_injector = BCUFaultInjector(
            self,
            fault_topic="/bcu/rpm/fault",
            fault_probability=self.get_parameter("fault_probability_per_sec").value,
            fault_duration_sec=self.get_parameter("fault_duration_sec").value,
            degraded_factor=self.get_parameter("fault_degraded_factor").value,
            severe_factor=self.get_parameter("fault_severe_factor").value,
            rng=rng,
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
        # BCU pressure / volume telemetry
        # ==============
        # Gazebo's buoyancy plugin only exposes bladder *volume*, not pressure.
        # On real hardware the BCU pressure transducer reads bladder pressure,
        # which for a flexible membrane in contact with seawater equals
        # ambient sea pressure to first order. So we source pressure from the
        # same sea-pressure plugin external_sensor_sim_bridge uses, and expose
        # bladder volume on its own topic.
        self.latest_volume_ml = 0  # bladder volume (mL), echoed from Gazebo
        self.latest_pressure_pa = 0  # bladder pressure (Pa), from sea pressure
        publish_rate_hz = self.get_parameter("publish_rate_hz").value
        self.pub_timer = self.create_timer(1.0 / publish_rate_hz, self.publish_at_rate)
        self.bcu_pressure_pub = create_publisher_for_topic(self, UUVTopics.BCU_PRESSURE)
        self.bcu_volume_pub = create_publisher_for_topic(self, UUVTopics.BCU_VOLUME)
        self.sim_current_volume_sub = self.create_subscription(
            Float64,
            SimTopics.BUOYANCY_VOLUME_STATE.format(model_name=self.model_name),
            self.sim_bcu_volume_callback,
            10,
        )
        self.sim_pressure_sub = self.create_subscription(
            FluidPressure,
            SimTopics.SEA_PRESSURE.format(model_name=self.model_name),
            self.sim_sea_pressure_callback,
            10,
        )

        self.sim_volume_pub = self.create_publisher(
            Float64, SimTopics.BUOYANCY_COMMAND.format(model_name=self.model_name), 10
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

        # Only integrate + push to Gazebo once we've synced to its SDF-
        # initialized bladder volume; otherwise we'd overwrite the initial
        # state. Flow-rate feedback below stays open-loop and fires regardless.
        if self.current_volume is not None:
            delta_vol = rps * self.volume_per_rev_m3 * dt

            self.current_volume += delta_vol
            self.current_volume = max(
                self.bladder_min_m3, min(self.current_volume, self.bladder_max_m3)
            )

            out_msg = Float64()
            out_msg.data = self.current_volume
            self.sim_volume_pub.publish(out_msg)

        # Mock Flow Rate feedback (m3/s)
        flow_msg = Float32()
        flow_msg.data = rps * self.volume_per_rev_m3
        self.flow_pub.publish(flow_msg)

    def sim_bcu_volume_callback(self, msg):
        # Seed current_volume from Gazebo's first volume report so subsequent
        # RPM-driven integration starts at the SDF-initialized bladder state.
        # last_time is also reset to now so the first dt after sync doesn't
        # include the time spent waiting for Gazebo's first publish.
        if self.current_volume is None:
            self.current_volume = float(msg.data)
            self.last_time = self.get_clock().now()

        # Volume (m3) to milliliters (mL) as integer
        self.latest_volume_ml = int(msg.data * Conversions.M3_TO_ML)

    def sim_sea_pressure_callback(self, msg):
        self.latest_pressure_pa = sea_pressure_pa(msg.fluid_pressure)

    def publish_at_rate(self):
        self.bcu_pressure_pub.publish(Int32(data=self.latest_pressure_pa))
        self.bcu_volume_pub.publish(Int32(data=self.latest_volume_ml))


def main(args=None):
    run_bridge(BCUSimBridge, args)


if __name__ == "__main__":
    main()
