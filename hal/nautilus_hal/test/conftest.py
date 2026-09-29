"""Tier 2 scaffolding for in-process rclpy tests.

The generic harness pieces (``NodeHarness``, domain isolation) come from
installed ``py_pkg.testing`` — the same single copy py_pkg's own
``test/node/`` conftest uses, so lifecycle fixes land in both repos at once.
Tests import ``NodeHarness`` from there directly.

Unlike py_pkg's node-test dir, this test tree mixes pure Tier 1 tests
(sim_models) with rclpy ones, so ``rclpy_session`` is opt-in rather than
autouse — rclpy test modules request it with
``pytestmark = pytest.mark.usefixtures("rclpy_session")``.
"""

import os

import pytest


@pytest.fixture(scope="session")
def rclpy_session():
    """Init/shutdown rclpy once per session, on an isolated ROS_DOMAIN_ID.

    rclpy is imported here, not at module level, so Tier 1-only runs never
    load it."""
    import rclpy
    from py_pkg.testing import isolated_ros_domain_id

    os.environ["ROS_DOMAIN_ID"] = str(isolated_ros_domain_id())
    rclpy.init()
    yield
    rclpy.shutdown()
