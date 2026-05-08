import os
from glob import glob

from setuptools import find_packages, setup

package_name = "nautilus_hal"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            os.path.join("share", package_name, "launch"),
            glob(os.path.join("launch", "*launch.[pxy][yma]*")),
        ),
        (
            os.path.join("share", package_name, "config"),
            glob(os.path.join("config", "*.yaml")),
        ),
    ],
    install_requires=["setuptools", "py_pkg"],
    zip_safe=True,
    maintainer="Girjoaba",
    maintainer_email="andrei.girjoaba@aris-space.ch",
    description="Simulation Hardware Abstraction Layer (HAL) for the Nautilus glider",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "bcu_sim_bridge = nautilus_hal.bcu_sim_bridge:main",
            "external_sensor_sim_bridge = nautilus_hal.external_sensor_sim_bridge:main",
            "imu_sim_bridge = nautilus_hal.imu_sim_bridge:main",
            "acu_sim_bridge = nautilus_hal.acu_sim_bridge:main",
            "gt_pose_bridge = nautilus_hal.gt_pose_bridge:main",
        ],
    },
)
