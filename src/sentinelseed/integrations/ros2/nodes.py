"""
ROS2 Safety Nodes for Sentinel.

This module provides ROS2 nodes that implement THSP safety validation
as middleware between command sources and robot actuators.

Architecture:
    The nodes implement a subscribe-validate-publish pattern:
    1. Subscribe to raw/unsafe commands
    2. Validate through THSP gates
    3. Publish safe commands or emergency stop
    4. Publish diagnostics to /sentinel/status

Classes:
    - SentinelSafetyNode: Main lifecycle node for safety validation
    - CommandSafetyFilter: Specialized filter for Twist messages (cmd_vel)
    - StringSafetyFilter: Filter for String messages
    - SentinelDiagnostics: Diagnostics publisher

Note:
    ROS2 packages (rclpy, geometry_msgs, std_msgs) are required but optional.
    The module gracefully handles missing dependencies.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type

from sentinelseed.integrations.ros2.validators import (
    CommandValidationResult,
    RobotSafetyRules,
    SafetyLevel,
    SafetyZone,
    VelocityLimits,
)

logger = logging.getLogger("sentinelseed.ros2")

# Try to import ROS2 packages
try:
    import rclpy
    from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    logger.warning(
        "ROS2 packages not found. Install rclpy and ROS2 to use ROS2 integration. "
        "The mock classes will be used for testing."
    )

    # Mock classes for when ROS2 is not available
    class LifecycleState:
        pass

    class TransitionCallbackReturn(Enum):
        """Mock of rclpy TransitionCallbackReturn enum."""
        SUCCESS = 0
        FAILURE = 1
        ERROR = 2

    class Node:
        def __init__(self, name: str):
            self.name = name
            self._logger = logging.getLogger(f"ros2.{name}")

        def get_logger(self):
            return self._logger

    class LifecycleNode(Node):
        pass

# Try to import message types
try:
    from geometry_msgs.msg import Twist, Vector3
    from std_msgs.msg import String, Header
    MSGS_AVAILABLE = True
except ImportError:
    MSGS_AVAILABLE = False

    # Mock message classes
    @dataclass
    class Vector3:
        x: float = 0.0
        y: float = 0.0
        z: float = 0.0

    @dataclass
    class Twist:
        linear: Vector3 = None
        angular: Vector3 = None

        def __post_init__(self):
            if self.linear is None:
                self.linear = Vector3()
            if self.angular is None:
                self.angular = Vector3()

    @dataclass
    class String:
        data: str = ""

    @dataclass
    class Header:
        stamp: Any = None
        frame_id: str = ""


@dataclass
class SentinelDiagnostics:
    """
    Diagnostics data structure for safety status reporting.

    Published to /sentinel/status topic.
    """
    is_safe: bool
    level: str
    gates: Dict[str, bool]
    violations: list
    commands_processed: int
    commands_blocked: int
    last_violation: Optional[str]

    def to_string(self) -> str:
        """Convert to string for std_msgs/String publishing."""
        return (
            f"safe={self.is_safe},"
            f"level={self.level},"
            f"processed={self.commands_processed},"
            f"blocked={self.commands_blocked},"
            f"violations={len(self.violations)}"
        )


class CommandSafetyFilter:
    """
    Safety filter for Twist (velocity) commands.

    This class wraps the RobotSafetyRules and provides a simple interface
    for filtering cmd_vel messages.

    Args:
        velocity_limits: Maximum allowed velocities
        safety_zone: Spatial operation boundaries
        require_purpose: Require explicit purpose for commands
        mode: Filter mode - 'block' (reject unsafe), 'clamp' (limit to safe values)

    Example:
        filter = CommandSafetyFilter(
            velocity_limits=VelocityLimits.differential_drive(max_linear=1.0),
            mode='clamp',
        )
        safe_twist = filter.filter(unsafe_twist)
    """

    def __init__(
        self,
        velocity_limits: Optional[VelocityLimits] = None,
        safety_zone: Optional[SafetyZone] = None,
        require_purpose: bool = False,
        mode: str = "clamp",
    ):
        self.mode = mode
        self.rules = RobotSafetyRules(
            velocity_limits=velocity_limits,
            safety_zone=safety_zone,
            require_purpose=require_purpose,
            emergency_stop_on_violation=(mode == "block"),
        )
        self._stats = {
            "processed": 0,
            "blocked": 0,
            "clamped": 0,
        }

    def filter(self, twist: Twist, purpose: Optional[str] = None) -> tuple:
        """
        Filter a Twist message through THSP gates.

        Args:
            twist: Input Twist message
            purpose: Optional purpose description

        Returns:
            Tuple of (filtered_twist, validation_result)
        """
        self._stats["processed"] += 1

        result = self.rules.validate_velocity(
            linear_x=twist.linear.x,
            linear_y=twist.linear.y,
            linear_z=twist.linear.z,
            angular_x=twist.angular.x,
            angular_y=twist.angular.y,
            angular_z=twist.angular.z,
            purpose=purpose,
        )

        if result.is_safe:
            return twist, result

        # Handle unsafe command
        if self.mode == "block" and result.level == SafetyLevel.DANGEROUS:
            self._stats["blocked"] += 1
            # Return zero velocity (emergency stop)
            return self._create_stop_twist(), result
        elif result.modified_command:
            self._stats["clamped"] += 1
            # Return clamped values
            return self._create_twist_from_dict(result.modified_command), result
        else:
            # Default: pass through with warning
            return twist, result

    def get_stats(self) -> Dict[str, int]:
        """Get filter statistics."""
        return self._stats.copy()

    def _create_stop_twist(self) -> Twist:
        """Create a stop (zero velocity) Twist message."""
        if MSGS_AVAILABLE:
            return Twist(
                linear=Vector3(x=0.0, y=0.0, z=0.0),
                angular=Vector3(x=0.0, y=0.0, z=0.0),
            )
        else:
            return Twist(
                linear=Vector3(0.0, 0.0, 0.0),
                angular=Vector3(0.0, 0.0, 0.0),
            )

    def _create_twist_from_dict(self, data: Dict) -> Twist:
        """Create a Twist message from dictionary."""
        linear = data.get("linear", {})
        angular = data.get("angular", {})

        if MSGS_AVAILABLE:
            return Twist(
                linear=Vector3(
                    x=linear.get("x", 0.0),
                    y=linear.get("y", 0.0),
                    z=linear.get("z", 0.0),
                ),
                angular=Vector3(
                    x=angular.get("x", 0.0),
                    y=angular.get("y", 0.0),
                    z=angular.get("z", 0.0),
                ),
            )
        else:
            return Twist(
                linear=Vector3(
                    linear.get("x", 0.0),
                    linear.get("y", 0.0),
                    linear.get("z", 0.0),
                ),
                angular=Vector3(
                    angular.get("x", 0.0),
                    angular.get("y", 0.0),
                    angular.get("z", 0.0),
                ),
            )


class StringSafetyFilter:
    """
    Safety filter for String messages (natural language commands).

    Args:
        block_unsafe: Block unsafe messages entirely
        require_purpose: Require explicit purpose

    Example:
        filter = StringSafetyFilter(block_unsafe=True)
        safe_string, result = filter.filter(unsafe_string)
    """

    def __init__(
        self,
        block_unsafe: bool = True,
        require_purpose: bool = False,
    ):
        self.block_unsafe = block_unsafe
        self.rules = RobotSafetyRules(require_purpose=require_purpose)
        self._stats = {
            "processed": 0,
            "blocked": 0,
        }

    def filter(self, msg: String) -> tuple:
        """
        Filter a String message through THSP gates.

        Args:
            msg: Input String message

        Returns:
            Tuple of (filtered_string, validation_result)
        """
        self._stats["processed"] += 1

        result = self.rules.validate_string_command(msg.data)

        if result.is_safe:
            return msg, result

        if self.block_unsafe and result.level in (SafetyLevel.DANGEROUS, SafetyLevel.BLOCKED):
            self._stats["blocked"] += 1
            blocked_msg = String()
            blocked_msg.data = "[BLOCKED BY SENTINEL] Unsafe command blocked."
            return blocked_msg, result

        return msg, result

    def get_stats(self) -> Dict[str, int]:
        """Get filter statistics."""
        return self._stats.copy()


class SentinelSafetyNode(LifecycleNode if ROS2_AVAILABLE else Node):
    """
    ROS2 Lifecycle Node for THSP safety validation.

    This node implements a subscribe-validate-publish pattern:
    1. Subscribes to input topic (e.g., /cmd_vel_raw)
    2. Validates messages through THSP gates
    3. Publishes safe messages to output topic (e.g., /cmd_vel)
    4. Publishes diagnostics to /sentinel/status

    The node follows ROS2 lifecycle management:
    - configure: Set up publishers/subscribers
    - activate: Start processing messages
    - deactivate: Stop processing
    - cleanup: Release resources

    Args:
        node_name: ROS2 node name (default: 'sentinel_safety_node')
        input_topic: Topic to subscribe for raw commands
        output_topic: Topic to publish safe commands
        msg_type: Message type ('twist' or 'string')
        max_linear_vel: Maximum linear velocity (m/s)
        max_angular_vel: Maximum angular velocity (rad/s)
        mode: Filter mode ('block' or 'clamp')

    Example:
        node = SentinelSafetyNode(
            input_topic='/cmd_vel_raw',
            output_topic='/cmd_vel',
            max_linear_vel=1.0,
            max_angular_vel=0.5,
        )
    """

    def __init__(
        self,
        node_name: str = "sentinel_safety_node",
        input_topic: str = "/cmd_vel_raw",
        output_topic: str = "/cmd_vel",
        status_topic: str = "/sentinel/status",
        msg_type: str = "twist",
        max_linear_vel: float = 1.0,
        max_angular_vel: float = 0.5,
        mode: str = "clamp",
        require_purpose: bool = False,
    ):
        super().__init__(node_name)

        self.input_topic = input_topic
        self.output_topic = output_topic
        self.status_topic = status_topic
        self.msg_type = msg_type
        self.mode = mode

        # Create safety filter
        if msg_type == "twist":
            self.filter = CommandSafetyFilter(
                velocity_limits=VelocityLimits.differential_drive(
                    max_linear=max_linear_vel,
                    max_angular=max_angular_vel,
                ),
                mode=mode,
                require_purpose=require_purpose,
            )
        else:
            self.filter = StringSafetyFilter(
                block_unsafe=(mode == "block"),
                require_purpose=require_purpose,
            )

        # Statistics
        self._commands_processed = 0
        self._commands_blocked = 0
        self._last_violation: Optional[str] = None

        # ROS2 objects (created in configure)
        self._subscription = None
        self._publisher = None
        self._status_publisher = None

        self.get_logger().info(
            f"SentinelSafetyNode initialized: {input_topic} -> {output_topic} "
            f"(type={msg_type}, mode={mode})"
        )

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        """Configure the node: create publishers and subscribers."""
        self.get_logger().info("Configuring SentinelSafetyNode...")

        if not ROS2_AVAILABLE:
            self.get_logger().warning("ROS2 not available. Running in mock mode.")
            return TransitionCallbackReturn.SUCCESS

        try:
            # Determine message type
            if self.msg_type == "twist":
                msg_class = Twist
                callback = self._twist_callback
            else:
                msg_class = String
                callback = self._string_callback

            # QoS profile for reliability
            qos = QoSProfile(
                depth=10,
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.VOLATILE,
            )

            # Create subscriber
            self._subscription = self.create_subscription(
                msg_class,
                self.input_topic,
                callback,
                qos,
            )

            # Create publisher
            self._publisher = self.create_publisher(
                msg_class,
                self.output_topic,
                qos,
            )

            # Create status publisher
            self._status_publisher = self.create_publisher(
                String,
                self.status_topic,
                qos,
            )

            self.get_logger().info("Configuration complete.")
            return TransitionCallbackReturn.SUCCESS

        except Exception as e:
            self.get_logger().error(f"Configuration failed: {e}")
            return TransitionCallbackReturn.FAILURE

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        """Activate the node: start processing messages."""
        self.get_logger().info("Activating SentinelSafetyNode...")
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        """Deactivate the node: stop processing messages."""
        self.get_logger().info("Deactivating SentinelSafetyNode...")
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        """Clean up the node: release resources."""
        self.get_logger().info("Cleaning up SentinelSafetyNode...")
        self._subscription = None
        self._publisher = None
        self._status_publisher = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        """Shut down the node."""
        self.get_logger().info("Shutting down SentinelSafetyNode...")
        return TransitionCallbackReturn.SUCCESS

    def _twist_callback(self, msg: Twist):
        """Process incoming Twist message."""
        self._commands_processed += 1

        safe_msg, result = self.filter.filter(msg)

        if not result.is_safe:
            self._commands_blocked += 1
            self._last_violation = result.violations[0] if result.violations else None
            self.get_logger().warning(f"Unsafe command: {result.reasoning}")

        # Publish filtered message
        if self._publisher:
            self._publisher.publish(safe_msg)

        # Publish status
        self._publish_status(result)

    def _string_callback(self, msg: String):
        """Process incoming String message."""
        self._commands_processed += 1

        safe_msg, result = self.filter.filter(msg)

        if not result.is_safe:
            self._commands_blocked += 1
            self._last_violation = result.violations[0] if result.violations else None
            self.get_logger().warning(f"Unsafe command: {result.reasoning}")

        # Publish filtered message
        if self._publisher:
            self._publisher.publish(safe_msg)

        # Publish status
        self._publish_status(result)

    def _publish_status(self, result: CommandValidationResult):
        """Publish safety status to /sentinel/status."""
        if not self._status_publisher:
            return

        diagnostics = SentinelDiagnostics(
            is_safe=result.is_safe,
            level=result.level.value,
            gates=result.gates,
            violations=result.violations,
            commands_processed=self._commands_processed,
            commands_blocked=self._commands_blocked,
            last_violation=self._last_violation,
        )

        status_msg = String()
        status_msg.data = diagnostics.to_string()
        self._status_publisher.publish(status_msg)

    def get_diagnostics(self) -> SentinelDiagnostics:
        """Get current diagnostics."""
        return SentinelDiagnostics(
            is_safe=True,
            level="safe",
            gates={"truth": True, "harm": True, "scope": True, "purpose": True},
            violations=[],
            commands_processed=self._commands_processed,
            commands_blocked=self._commands_blocked,
            last_violation=self._last_violation,
        )


def create_safety_node(
    input_topic: str = "/cmd_vel_raw",
    output_topic: str = "/cmd_vel",
    max_linear_vel: float = 1.0,
    max_angular_vel: float = 0.5,
    mode: str = "clamp",
) -> SentinelSafetyNode:
    """
    Factory function to create a SentinelSafetyNode.

    This is a convenience function for creating a safety node with
    common parameters.

    Args:
        input_topic: Topic to subscribe for raw commands
        output_topic: Topic to publish safe commands
        max_linear_vel: Maximum linear velocity (m/s)
        max_angular_vel: Maximum angular velocity (rad/s)
        mode: Filter mode ('block' or 'clamp')

    Returns:
        Configured SentinelSafetyNode

    Example:
        import rclpy
        rclpy.init()
        node = create_safety_node('/cmd_vel_raw', '/cmd_vel')
        rclpy.spin(node)
    """
    return SentinelSafetyNode(
        input_topic=input_topic,
        output_topic=output_topic,
        max_linear_vel=max_linear_vel,
        max_angular_vel=max_angular_vel,
        mode=mode,
    )
