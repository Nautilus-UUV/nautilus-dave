from setuptools import find_packages, setup

package_name = "nautilus_hal"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "py_pkg"],
    zip_safe=True,
    maintainer="girji",
    maintainer_email="andrei.girjoaba@aris-space.ch",
    description="Simulation Hardware Abstraction Layer (HAL) for the Nautilus glider",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "bcu_sim_bridge = nautilus_hal.bcu_sim_bridge:main",
            "external_sensor_sim_bridge = nautilus_hal.external_sensor_sim_bridge:main",
        ],
    },
)
