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
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from sentinelseed.integrations.ros2.validators import (
    CommandValidationResult,
    RobotSafetyRules,
    SafetyLevel,
    SafetyZone,
    ValidationError,
    VelocityLimits,
    VALID_MODES,
    VALID_MSG_TYPES,
    DEFAULT_MAX_LINEAR_VEL,
    DEFAULT_MAX_ANGULAR_VEL,
)

# Logger for module-level warnings
_logger = logging.getLogger("sentinelseed.ros2")

# Try to import ROS2 packages
try:
    import rclpy
    from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    ROS2_AVAILABLE = True
except (ImportError, AttributeError) as e:
    ROS2_AVAILABLE = False
    if isinstance(e, AttributeError):
        _logger.warning(
            f"ROS2 packages found but incompatible version: {e}. "
            "The mock classes will be used for testing."
        )
    else:
        _logger.warning(
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
except (ImportError, AttributeError) as e:
    MSGS_AVAILABLE = False
    if isinstance(e, AttributeError):
        _logger.warning(
            f"ROS2 message types found but incompatible version: {e}. "
            "Using mock message classes."
        )
    else:
        _logger.debug("ROS2 message types not found. Using mock message classes.")

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


def _escape_diagnostic_value(value: str) -> str:
    """Escape special characters in diagnostic values."""
    if value is None:
        return ""
    # Escape commas and equals signs to prevent parsing issues
    return str(value).replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=")


@dataclass
class SentinelDiagnostics:
    """
    Diagnostics data structure for safety status reporting.

    Published to /sentinel/status topic.
    """
    is_safe: bool
    level: str
    gates: Dict[str, bool]
    violations: List[str] = field(default_factory=list)
    commands_processed: int = 0
    commands_blocked: int = 0
    last_violation: Optional[str] = None

    def to_string(self) -> str:
        """
        Convert to string for std_msgs/String publishing.

        Uses escaped format to handle special characters in violation messages.
        """
        # Escape the last_violation if present
        escaped_violation = ""
        if self.last_violation:
            escaped_violation = _escape_diagnostic_value(self.last_violation)

        return (
            f"safe={self.is_safe},"
            f"level={_escape_diagnostic_value(self.level)},"
            f"processed={self.commands_processed},"
            f"blocked={self.commands_blocked},"
            f"violations={len(self.violations)},"
            f"last={escaped_violation}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_safe": self.is_safe,
            "level": self.level,
            "gates": self.gates,
            "violations": self.violations,
            "commands_processed": self.commands_processed,
            "commands_blocked": self.commands_blocked,
            "last_violation": self.last_violation,
        }


def _validate_mode(mode: str) -> None:
    """Validate filter mode parameter."""
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {VALID_MODES}")


def _safe_get_velocity(twist: Any, attr_path: str, default: float = 0.0) -> float:
    """
    Safely extract velocity value from twist message.

    Handles cases where linear/angular might be None or missing attributes.
    """
    try:
        parts = attr_path.split(".")
        value = twist
        for part in parts:
            value = getattr(value, part, None)
            if value is None:
                return default
        if isinstance(value, (int, float)):
            return float(value)
        return default
    except (AttributeError, TypeError):
        return default


class CommandSafetyFilter:
    """
    Safety filter for Twist (velocity) commands.

    This class wraps the RobotSafetyRules and provides a simple interface
    for filtering cmd_vel messages.

    Args:
        velocity_limits: Maximum allowed velocities
        safety_zone: Spatial operation boundaries
        require_purpose: Require explicit purpose for commands
        mode: Filter mode:
            - 'block': Emergency stop on unsafe command (Cat 0/STO)
            - 'clamp': Limit velocity to safe maximum (SLS)
            - 'warn': Log violation but pass command unchanged (monitor only)

    Raises:
        ValueError: If mode is not valid

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
        _validate_mode(mode)
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
            "warned": 0,
        }

    def filter(
        self,
        twist: Twist,
        purpose: Optional[str] = None,
        current_position: Optional[Tuple[float, float, float]] = None,
    ) -> Tuple[Twist, CommandValidationResult]:
        """
        Filter a Twist message through THSP gates.

        Args:
            twist: Input Twist message
            purpose: Optional purpose description
            current_position: Optional (x, y, z) tuple of current robot position in meters.
                              If provided, Scope Gate validates position is within safety_zone.
                              Typically obtained from odometry or localization.

        Returns:
            Tuple of (filtered_twist, validation_result)

        Raises:
            ValueError: If twist is None
        """
        if twist is None:
            raise ValueError("twist cannot be None")

        self._stats["processed"] += 1

        # Safely extract velocity values, handling None linear/angular
        result = self.rules.validate_velocity(
            linear_x=_safe_get_velocity(twist, "linear.x"),
            linear_y=_safe_get_velocity(twist, "linear.y"),
            linear_z=_safe_get_velocity(twist, "linear.z"),
            angular_x=_safe_get_velocity(twist, "angular.x"),
            angular_y=_safe_get_velocity(twist, "angular.y"),
            angular_z=_safe_get_velocity(twist, "angular.z"),
            purpose=purpose,
            current_position=current_position,
        )

        if result.is_safe:
            return twist, result

        # Handle unsafe command based on mode
        if self.mode == "warn":
            # Warn mode: log but pass through unchanged
            self._stats["warned"] += 1
            _logger.warning(
                f"Unsafe command detected (warn mode): {result.violations}"
            )
            return twist, result
        elif self.mode == "block" and result.level == SafetyLevel.DANGEROUS:
            # Block mode: emergency stop
            self._stats["blocked"] += 1
            return self._create_stop_twist(), result
        elif self.mode == "clamp" and result.modified_command:
            # Clamp mode: limit to safe values
            self._stats["clamped"] += 1
            return self._create_twist_from_dict(result.modified_command), result
        else:
            # Fallback: pass through (should not reach here normally)
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


def _safe_get_string_data(msg: Any) -> str:
    """Safely extract string data from message."""
    if msg is None:
        return ""
    try:
        data = getattr(msg, "data", None)
        if data is None:
            return ""
        return str(data)
    except (AttributeError, TypeError):
        return ""


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

    def filter(self, msg: String) -> Tuple[String, CommandValidationResult]:
        """
        Filter a String message through THSP gates.

        Args:
            msg: Input String message

        Returns:
            Tuple of (filtered_string, validation_result)

        Raises:
            ValueError: If msg is None
        """
        if msg is None:
            raise ValueError("msg cannot be None")

        self._stats["processed"] += 1

        # Safely extract string data
        data = _safe_get_string_data(msg)
        result = self.rules.validate_string_command(data)

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


def _validate_msg_type(msg_type: str) -> None:
    """Validate message type parameter."""
    if msg_type not in VALID_MSG_TYPES:
        raise ValueError(f"Invalid msg_type '{msg_type}'. Must be one of: {VALID_MSG_TYPES}")


def _safe_get_result_level(result: Any) -> str:
    """Safely get level value from result, handling both Enum and string."""
    if result is None:
        return "unknown"
    level = getattr(result, "level", None)
    if level is None:
        return "unknown"
    # Handle SafetyLevel enum
    if hasattr(level, "value"):
        return str(level.value)
    return str(level)


def _safe_get_result_gates(result: Any) -> Dict[str, bool]:
    """Safely get gates from result."""
    if result is None:
        return {}
    gates = getattr(result, "gates", None)
    if gates is None or not isinstance(gates, dict):
        return {}
    return gates.copy()


def _safe_get_result_violations(result: Any) -> List[str]:
    """Safely get violations from result."""
    if result is None:
        return []
    violations = getattr(result, "violations", None)
    if violations is None or not isinstance(violations, list):
        return []
    return [str(v) for v in violations]


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
        mode: Filter mode:
            - 'block': Emergency stop on unsafe command (Cat 0/STO)
            - 'clamp': Limit velocity to safe maximum (SLS)
            - 'warn': Log violation but pass command unchanged (monitor only)

    Raises:
        ValueError: If mode or msg_type is invalid

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
        max_linear_vel: float = DEFAULT_MAX_LINEAR_VEL,
        max_angular_vel: float = DEFAULT_MAX_ANGULAR_VEL,
        mode: str = "clamp",
        require_purpose: bool = False,
    ):
        # Validate parameters before calling super().__init__
        _validate_mode(mode)
        _validate_msg_type(msg_type)

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

        # Store last validation result for get_diagnostics
        self._last_result: Optional[CommandValidationResult] = None

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
        try:
            self._commands_processed += 1

            safe_msg, result = self.filter.filter(msg)
            self._last_result = result

            if not result.is_safe:
                self._commands_blocked += 1
                violations = _safe_get_result_violations(result)
                self._last_violation = violations[0] if violations else None
                reasoning = getattr(result, "reasoning", "Unknown")
                self.get_logger().warning(f"Unsafe command: {reasoning}")

            # Publish filtered message
            if self._publisher:
                self._publisher.publish(safe_msg)

            # Publish status
            self._publish_status(result)

        except Exception as e:
            self.get_logger().error(f"Error in _twist_callback: {e}")
            # Publish stop command on error for safety
            if self._publisher:
                stop_twist = Twist()
                if MSGS_AVAILABLE:
                    stop_twist.linear = Vector3(x=0.0, y=0.0, z=0.0)
                    stop_twist.angular = Vector3(x=0.0, y=0.0, z=0.0)
                else:
                    stop_twist.linear = Vector3(0.0, 0.0, 0.0)
                    stop_twist.angular = Vector3(0.0, 0.0, 0.0)
                self._publisher.publish(stop_twist)

    def _string_callback(self, msg: String):
        """Process incoming String message."""
        try:
            self._commands_processed += 1

            safe_msg, result = self.filter.filter(msg)
            self._last_result = result

            if not result.is_safe:
                self._commands_blocked += 1
                violations = _safe_get_result_violations(result)
                self._last_violation = violations[0] if violations else None
                reasoning = getattr(result, "reasoning", "Unknown")
                self.get_logger().warning(f"Unsafe command: {reasoning}")

            # Publish filtered message
            if self._publisher:
                self._publisher.publish(safe_msg)

            # Publish status
            self._publish_status(result)

        except Exception as e:
            self.get_logger().error(f"Error in _string_callback: {e}")
            # Publish blocked message on error for safety
            if self._publisher:
                blocked_msg = String()
                blocked_msg.data = "[ERROR] Command processing failed."
                self._publisher.publish(blocked_msg)

    def _publish_status(self, result: CommandValidationResult):
        """Publish safety status to /sentinel/status."""
        if not self._status_publisher:
            return

        # Safely extract values from result
        is_safe = getattr(result, "is_safe", True)
        level = _safe_get_result_level(result)
        gates = _safe_get_result_gates(result)
        violations = _safe_get_result_violations(result)

        diagnostics = SentinelDiagnostics(
            is_safe=is_safe,
            level=level,
            gates=gates,
            violations=violations,
            commands_processed=self._commands_processed,
            commands_blocked=self._commands_blocked,
            last_violation=self._last_violation,
        )

        status_msg = String()
        status_msg.data = diagnostics.to_string()
        self._status_publisher.publish(status_msg)

    def get_diagnostics(self) -> SentinelDiagnostics:
        """
        Get current diagnostics.

        Returns actual values from the last validation result,
        not hardcoded placeholders.
        """
        # Use last result if available, otherwise return default safe state
        if self._last_result is not None:
            is_safe = getattr(self._last_result, "is_safe", True)
            level = _safe_get_result_level(self._last_result)
            gates = _safe_get_result_gates(self._last_result)
            violations = _safe_get_result_violations(self._last_result)
        else:
            # No commands processed yet - return default safe state
            is_safe = True
            level = "safe"
            gates = {"truth": True, "harm": True, "scope": True, "purpose": True}
            violations = []

        return SentinelDiagnostics(
            is_safe=is_safe,
            level=level,
            gates=gates,
            violations=violations,
            commands_processed=self._commands_processed,
            commands_blocked=self._commands_blocked,
            last_violation=self._last_violation,
        )


def create_safety_node(
    input_topic: str = "/cmd_vel_raw",
    output_topic: str = "/cmd_vel",
    max_linear_vel: float = DEFAULT_MAX_LINEAR_VEL,
    max_angular_vel: float = DEFAULT_MAX_ANGULAR_VEL,
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
        mode: Filter mode:
            - 'block': Emergency stop on unsafe command
            - 'clamp': Limit velocity to safe maximum
            - 'warn': Log violation but pass command unchanged

    Returns:
        Configured SentinelSafetyNode

    Raises:
        ValueError: If mode is invalid

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
