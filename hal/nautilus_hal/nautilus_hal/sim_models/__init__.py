"""Pure sim-plant and sensor models composed by the HAL sim bridges.

ROS-free logic only (plant transients, noise chains, fault archetypes)
so the math gets Tier 1 coverage without a Gazebo environment. The
scenario *schema* these are parameterized from stays in
``py_pkg.scenarios.spec`` — controllers and bridges share it.
"""
