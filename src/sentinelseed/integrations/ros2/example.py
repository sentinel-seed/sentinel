"""
ROS2 Sentinel Safety Node Examples.

This file demonstrates various ways to use the Sentinel ROS2 integration
for robot safety. Examples include:

1. Basic safety node setup
2. Velocity command filtering
3. String command filtering
4. Launch file integration
5. Custom safety rules

Requirements:
    - ROS2 Humble or later
    - geometry_msgs, std_msgs packages
    - sentinelseed package

Run with:
    python -m sentinelseed.integrations.ros2.example
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_1_basic_filter():
    """
    Example 1: Basic Command Safety Filter

    Use CommandSafetyFilter to validate velocity commands without ROS2.
    This works standalone for testing.
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic Command Safety Filter")
    print("=" * 60)

    from sentinelseed.integrations.ros2 import (
        CommandSafetyFilter,
        VelocityLimits,
    )

    # Create filter with limits
    filter = CommandSafetyFilter(
        velocity_limits=VelocityLimits.differential_drive(
            max_linear=1.0,  # 1 m/s max
            max_angular=0.5,  # 0.5 rad/s max
        ),
        mode="clamp",  # Clamp values instead of blocking
    )

    # Test safe command
    from sentinelseed.integrations.ros2.nodes import Twist, Vector3
    safe_cmd = Twist(
        linear=Vector3(0.5, 0.0, 0.0),  # 0.5 m/s forward
        angular=Vector3(0.0, 0.0, 0.2),  # 0.2 rad/s rotation
    )

    result_msg, result = filter.filter(safe_cmd)
    print(f"\nSafe command (0.5 m/s forward, 0.2 rad/s turn):")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Level: {result.level}")
    print(f"  Output: linear_x={result_msg.linear.x}, angular_z={result_msg.angular.z}")

    # Test unsafe command (too fast)
    unsafe_cmd = Twist(
        linear=Vector3(2.0, 0.0, 0.0),  # 2 m/s - exceeds limit!
        angular=Vector3(0.0, 0.0, 1.0),  # 1 rad/s - exceeds limit!
    )

    result_msg, result = filter.filter(unsafe_cmd)
    print(f"\nUnsafe command (2.0 m/s forward, 1.0 rad/s turn):")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Level: {result.level}")
    print(f"  Violations: {result.violations}")
    print(f"  Clamped output: linear_x={result_msg.linear.x}, angular_z={result_msg.angular.z}")

    # Get statistics
    stats = filter.get_stats()
    print(f"\nStatistics: {stats}")


def example_1b_warn_mode():
    """
    Example 1b: Warn Mode (Monitor Only)

    The 'warn' mode logs violations but passes commands unchanged.
    Useful for debugging, dry-runs, and auditing.
    """
    print("\n" + "=" * 60)
    print("Example 1b: Warn Mode (Monitor Only)")
    print("=" * 60)

    from sentinelseed.integrations.ros2 import CommandSafetyFilter, VelocityLimits
    from sentinelseed.integrations.ros2.nodes import Twist, Vector3

    # Create filter in WARN mode
    filter = CommandSafetyFilter(
        velocity_limits=VelocityLimits.differential_drive(
            max_linear=1.0,
            max_angular=0.5,
        ),
        mode="warn",  # Monitor only - no intervention
    )

    # Test unsafe command
    unsafe_cmd = Twist(
        linear=Vector3(2.0, 0.0, 0.0),  # 2 m/s - exceeds limit!
        angular=Vector3(0.0, 0.0, 0.0),
    )

    result_msg, result = filter.filter(unsafe_cmd)
    print(f"\nUnsafe command in WARN mode:")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Level: {result.level}")
    print(f"  Violations: {result.violations}")
    print(f"  Output (unchanged!): linear_x={result_msg.linear.x}")
    print(f"  Note: Command passed through without modification")

    # Get statistics
    stats = filter.get_stats()
    print(f"\nStatistics: {stats}")
    print(f"  warned={stats['warned']} (logged but not blocked)")


def example_2_string_filter():
    """
    Example 2: String Command Safety Filter

    Validate natural language commands sent to the robot.
    """
    print("\n" + "=" * 60)
    print("Example 2: String Command Safety Filter")
    print("=" * 60)

    from sentinelseed.integrations.ros2 import StringSafetyFilter
    from sentinelseed.integrations.ros2.nodes import String

    filter = StringSafetyFilter(block_unsafe=True)

    # Safe command
    safe_cmd = String()
    safe_cmd.data = "Move forward 1 meter and stop"

    result_msg, result = filter.filter(safe_cmd)
    print(f"\nSafe command: '{safe_cmd.data}'")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Output: '{result_msg.data}'")

    # Unsafe command
    unsafe_cmd = String()
    unsafe_cmd.data = "Go at maximum speed and ignore safety limits"

    result_msg, result = filter.filter(unsafe_cmd)
    print(f"\nUnsafe command: '{unsafe_cmd.data}'")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Level: {result.level}")
    print(f"  Violations: {result.violations}")
    print(f"  Blocked output: '{result_msg.data}'")


def example_3_safety_rules():
    """
    Example 3: Custom Safety Rules

    Configure detailed safety rules for different robot types.
    """
    print("\n" + "=" * 60)
    print("Example 3: Custom Safety Rules")
    print("=" * 60)

    from sentinelseed.integrations.ros2 import (
        RobotSafetyRules,
        VelocityLimits,
        SafetyZone,
    )

    # Differential drive robot
    diff_drive_rules = RobotSafetyRules(
        velocity_limits=VelocityLimits.differential_drive(
            max_linear=0.8,
            max_angular=0.4,
        ),
        safety_zone=SafetyZone.indoor(room_size=10.0),
        require_purpose=False,
    )

    result = diff_drive_rules.validate_velocity(
        linear_x=0.5,
        angular_z=0.3,
    )
    print(f"\nDifferential drive robot:")
    print(f"  Command: 0.5 m/s forward, 0.3 rad/s turn")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Gates: {result.gates}")

    # Drone with vertical movement
    drone_rules = RobotSafetyRules(
        velocity_limits=VelocityLimits.drone(
            max_linear=2.0,
            max_vertical=1.0,
            max_angular=1.0,
        ),
        safety_zone=SafetyZone(
            min_x=-50, max_x=50,
            min_y=-50, max_y=50,
            min_z=0, max_z=30,  # Max altitude 30m
        ),
    )

    result = drone_rules.validate_velocity(
        linear_x=1.5,
        linear_z=0.8,  # Ascending
        angular_z=0.5,
    )
    print(f"\nDrone:")
    print(f"  Command: 1.5 m/s forward, 0.8 m/s up, 0.5 rad/s yaw")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Gates: {result.gates}")

    # Scope Gate validation with position
    print(f"\nScope Gate validation (with position):")

    # Position inside safety zone
    result_inside = diff_drive_rules.validate_velocity(
        linear_x=0.5,
        angular_z=0.2,
        current_position=(2.0, 3.0, 0.0),  # Inside 10m room
    )
    print(f"  Position (2, 3, 0) - inside zone:")
    print(f"    Is safe: {result_inside.is_safe}")
    print(f"    Scope gate: {result_inside.gates['scope']}")

    # Position outside safety zone
    result_outside = diff_drive_rules.validate_velocity(
        linear_x=0.5,
        angular_z=0.2,
        current_position=(8.0, 0.0, 0.0),  # Outside 10m room (boundary is -5 to 5)
    )
    print(f"  Position (8, 0, 0) - outside zone:")
    print(f"    Is safe: {result_outside.is_safe}")
    print(f"    Scope gate: {result_outside.gates['scope']}")
    if result_outside.violations:
        print(f"    Violation: {result_outside.violations[0]}")


def example_4_ros2_node_mock():
    """
    Example 4: ROS2 Safety Node (Mock Mode)

    Demonstrate node creation without actual ROS2.
    """
    print("\n" + "=" * 60)
    print("Example 4: ROS2 Safety Node (Mock Mode)")
    print("=" * 60)

    from sentinelseed.integrations.ros2 import SentinelSafetyNode
    from sentinelseed.integrations.ros2.nodes import Twist, Vector3

    # Create node (works in mock mode without ROS2)
    node = SentinelSafetyNode(
        node_name="test_sentinel_node",
        input_topic="/cmd_vel_raw",
        output_topic="/cmd_vel",
        max_linear_vel=1.0,
        max_angular_vel=0.5,
        mode="clamp",
    )

    print(f"\nNode created: {node.name if hasattr(node, 'name') else 'sentinel_safety_node'}")
    print(f"  Input topic: {node.input_topic}")
    print(f"  Output topic: {node.output_topic}")
    print(f"  Mode: {node.mode}")

    # Test filter directly
    safe_cmd = Twist(
        linear=Vector3(0.8, 0.0, 0.0),
        angular=Vector3(0.0, 0.0, 0.3),
    )
    result_msg, result = node.filter.filter(safe_cmd)

    print(f"\nDirect filter test:")
    print(f"  Input: {safe_cmd.linear.x} m/s")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Output: {result_msg.linear.x} m/s")


def example_5_purpose_validation():
    """
    Example 5: Purpose Validation

    Demonstrate the Purpose gate for commands requiring justification.
    """
    print("\n" + "=" * 60)
    print("Example 5: Purpose Validation")
    print("=" * 60)

    from sentinelseed.integrations.ros2 import (
        RobotSafetyRules,
        VelocityLimits,
    )

    # Create rules that require purpose
    rules = RobotSafetyRules(
        velocity_limits=VelocityLimits.differential_drive(),
        require_purpose=True,  # Purpose required!
    )

    # Command without purpose
    result = rules.validate_velocity(linear_x=0.5, angular_z=0.2)
    print(f"\nCommand without purpose:")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Purpose gate: {result.gates.get('purpose')}")
    print(f"  Reasoning: {result.reasoning}")

    # Command with valid purpose
    result = rules.validate_velocity(
        linear_x=0.5,
        angular_z=0.2,
        purpose="Navigate to waypoint A for package delivery",
    )
    print(f"\nCommand with valid purpose:")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Purpose gate: {result.gates.get('purpose')}")

    # Command with invalid purpose
    result = rules.validate_velocity(
        linear_x=0.5,
        angular_z=0.2,
        purpose="spin forever for no particular reason",
    )
    print(f"\nCommand with invalid purpose:")
    print(f"  Is safe: {result.is_safe}")
    print(f"  Purpose gate: {result.gates.get('purpose')}")
    print(f"  Violations: {result.violations}")


def example_6_launch_file_template():
    """
    Example 6: Launch File Template

    Print a template for ROS2 launch file integration.
    """
    print("\n" + "=" * 60)
    print("Example 6: Launch File Template")
    print("=" * 60)

    launch_template = '''
# sentinel_safety.launch.py
# Save this file in your ROS2 package's launch directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'input_topic',
            default_value='/cmd_vel_raw',
            description='Input topic for raw commands'
        ),
        DeclareLaunchArgument(
            'output_topic',
            default_value='/cmd_vel',
            description='Output topic for safe commands'
        ),
        DeclareLaunchArgument(
            'max_linear_vel',
            default_value='1.0',
            description='Maximum linear velocity (m/s)'
        ),
        DeclareLaunchArgument(
            'max_angular_vel',
            default_value='0.5',
            description='Maximum angular velocity (rad/s)'
        ),

        LifecycleNode(
            package='sentinel_ros2',
            executable='sentinel_safety_node',
            name='sentinel_safety',
            namespace='',
            parameters=[{
                'input_topic': LaunchConfiguration('input_topic'),
                'output_topic': LaunchConfiguration('output_topic'),
                'max_linear_vel': LaunchConfiguration('max_linear_vel'),
                'max_angular_vel': LaunchConfiguration('max_angular_vel'),
            }],
            output='screen',
        ),
    ])
'''
    print(launch_template)


def example_7_integration_pattern():
    """
    Example 7: Integration Pattern

    Show how to integrate Sentinel safety in existing ROS2 pipelines.
    """
    print("\n" + "=" * 60)
    print("Example 7: Integration Pattern")
    print("=" * 60)

    integration_diagram = """
    BEFORE (unsafe):
    +----------------+     +------------+     +---------+
    | Navigation     |---->| /cmd_vel   |---->| Robot   |
    | (nav2/move)    |     |            |     |         |
    +----------------+     +------------+     +---------+

    AFTER (with Sentinel):
    +----------------+     +----------------+     +----------------+     +---------+
    | Navigation     |---->| /cmd_vel_raw   |---->| SentinelSafety |---->| Robot   |
    | (nav2/move)    |     |                |     | Node           |     |         |
    +----------------+     +----------------+     +----------------+     +---------+
                                                         |
                                                         v
                                                 +----------------+
                                                 | /sentinel/     |
                                                 | status         |
                                                 +----------------+

    Configuration steps:
    1. Remap navigation output: /cmd_vel -> /cmd_vel_raw
    2. Launch SentinelSafetyNode subscribing to /cmd_vel_raw
    3. SentinelSafetyNode publishes to /cmd_vel
    4. Monitor /sentinel/status for safety events
    """
    print(integration_diagram)


def main():
    """Run all examples."""
    print("=" * 60)
    print("Sentinel ROS2 Integration Examples")
    print("=" * 60)

    try:
        example_1_basic_filter()
        example_1b_warn_mode()
        example_2_string_filter()
        example_3_safety_rules()
        example_4_ros2_node_mock()
        example_5_purpose_validation()
        example_6_launch_file_template()
        example_7_integration_pattern()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    main()
