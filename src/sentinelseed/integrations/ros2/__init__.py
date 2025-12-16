"""
Sentinel ROS2 Integration - Safety Middleware for Robots.

This integration provides THSP-based safety validation for ROS2 robots.
It implements a subscribe-validate-publish pattern that filters unsafe commands.

Modules:
    - SentinelSafetyNode: Lifecycle node for message validation
    - CommandSafetyFilter: Velocity command safety filter (cmd_vel)
    - StringSafetyFilter: String message safety filter
    - RobotSafetyRules: THSP rules adapted for robotics

Architecture:
    [Navigation/Controller] --/cmd_vel_raw--> [SentinelSafetyNode] --/cmd_vel--> [Robot]
                                                    |
                                                    v
                                            [THSP Validation]
                                                    |
                                                    v
                                            [/sentinel/status]

Requirements:
    - ROS2 (Humble or later recommended)
    - rclpy >= 3.0
    - geometry_msgs, std_msgs

Installation:
    pip install sentinelseed
    # ROS2 packages installed via apt/rosdep

Usage:
    # Create safety node via launch file or Python
    from sentinelseed.integrations.ros2 import SentinelSafetyNode

    import rclpy
    rclpy.init()
    node = SentinelSafetyNode(
        input_topic='/cmd_vel_raw',
        output_topic='/cmd_vel',
        max_linear_vel=1.0,
        max_angular_vel=0.5,
    )
    rclpy.spin(node)

References:
    - ROS 2 Safety Working Group: https://github.com/ros-safety
    - ROS 2 Lifecycle Nodes: https://design.ros2.org/articles/node_lifecycle.html
    - Nav2 Safety Node: https://navigation.ros.org/
"""

from sentinelseed.integrations.ros2.nodes import (
    SentinelSafetyNode,
    CommandSafetyFilter,
    StringSafetyFilter,
    SentinelDiagnostics,
)
from sentinelseed.integrations.ros2.validators import (
    RobotSafetyRules,
    CommandValidationResult,
    SafetyZone,
    VelocityLimits,
)

__all__ = [
    # Nodes
    'SentinelSafetyNode',
    'CommandSafetyFilter',
    'StringSafetyFilter',
    'SentinelDiagnostics',
    # Validators
    'RobotSafetyRules',
    'CommandValidationResult',
    'SafetyZone',
    'VelocityLimits',
]
