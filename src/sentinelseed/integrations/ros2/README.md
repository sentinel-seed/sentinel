# Sentinel ROS2 Integration

Safety middleware for ROS2 robots using THSP (Truth-Harm-Scope-Purpose) validation.

## Overview

This integration provides THSP-based safety validation for ROS2 robots. It implements a subscribe-validate-publish pattern that filters unsafe commands before they reach robot actuators.

```
┌──────────────┐     ┌────────────────┐     ┌────────────────┐     ┌───────┐
│ Navigation   │────▶│ /cmd_vel_raw   │────▶│ SentinelSafety │────▶│ Robot │
│ (nav2/move)  │     │                │     │     Node       │     │       │
└──────────────┘     └────────────────┘     └────────────────┘     └───────┘
                                                    │
                                                    ▼
                                            ┌────────────────┐
                                            │ /sentinel/     │
                                            │ status         │
                                            └────────────────┘
```

## Installation

```bash
# Install sentinelseed
pip install sentinelseed

# Ensure ROS2 is installed (Humble or later recommended)
# ROS2 packages are installed via apt/rosdep
sudo apt install ros-humble-rclpy ros-humble-geometry-msgs ros-humble-std-msgs
```

## Quick Start

### Option 1: Python Node

```python
import rclpy
from sentinelseed.integrations.ros2 import SentinelSafetyNode

rclpy.init()
node = SentinelSafetyNode(
    input_topic='/cmd_vel_raw',
    output_topic='/cmd_vel',
    max_linear_vel=1.0,
    max_angular_vel=0.5,
    mode='clamp',  # 'clamp' or 'block'
)
rclpy.spin(node)
```

### Option 2: Standalone Filter (No ROS2)

```python
from sentinelseed.integrations.ros2 import (
    CommandSafetyFilter,
    VelocityLimits,
)

filter = CommandSafetyFilter(
    velocity_limits=VelocityLimits.differential_drive(
        max_linear=1.0,
        max_angular=0.5,
    ),
    mode='clamp',
)

# Use with your own message handling
safe_twist, result = filter.filter(incoming_twist)
if not result.is_safe:
    print(f"Violation: {result.violations}")
```

## Components

### SentinelSafetyNode

ROS2 Lifecycle Node that validates messages in real-time.

```python
from sentinelseed.integrations.ros2 import SentinelSafetyNode

node = SentinelSafetyNode(
    node_name='sentinel_safety',     # ROS2 node name
    input_topic='/cmd_vel_raw',      # Subscribe to raw commands
    output_topic='/cmd_vel',         # Publish safe commands
    status_topic='/sentinel/status', # Publish diagnostics
    msg_type='twist',                # 'twist' or 'string'
    max_linear_vel=1.0,              # m/s
    max_angular_vel=0.5,             # rad/s
    mode='clamp',                    # 'clamp' or 'block'
    require_purpose=False,           # Require purpose for commands
)
```

**Lifecycle States:**
- `configure`: Set up publishers/subscribers
- `activate`: Start processing
- `deactivate`: Stop processing
- `cleanup`: Release resources

### CommandSafetyFilter

Filter for Twist (velocity) messages.

```python
from sentinelseed.integrations.ros2 import CommandSafetyFilter, VelocityLimits

filter = CommandSafetyFilter(
    velocity_limits=VelocityLimits.differential_drive(),
    mode='clamp',
)

safe_twist, result = filter.filter(twist_msg)
print(result.gates)  # {'truth': True, 'harm': True, 'scope': True, 'purpose': True}
```

### StringSafetyFilter

Filter for String (natural language) commands.

```python
from sentinelseed.integrations.ros2 import StringSafetyFilter

filter = StringSafetyFilter(block_unsafe=True)

safe_string, result = filter.filter(string_msg)
if not result.is_safe:
    print(f"Blocked: {result.reasoning}")
```

### VelocityLimits

Pre-configured velocity limits for common robot types.

```python
from sentinelseed.integrations.ros2 import VelocityLimits

# Differential drive robot (TurtleBot, etc.)
limits = VelocityLimits.differential_drive(max_linear=1.0, max_angular=0.5)

# Omnidirectional robot (Kuka, etc.)
limits = VelocityLimits.omnidirectional(max_linear=1.0, max_angular=0.5)

# Drone/UAV
limits = VelocityLimits.drone(max_linear=2.0, max_vertical=1.0, max_angular=1.0)
```

### SafetyZone

Spatial boundaries for safe operation.

```python
from sentinelseed.integrations.ros2 import SafetyZone

# Indoor environment
zone = SafetyZone.indoor(room_size=10.0)

# Custom boundaries
zone = SafetyZone(
    min_x=-10, max_x=10,
    min_y=-10, max_y=10,
    min_z=0, max_z=2,
)
```

## THSP Gates for Robotics

### Truth Gate
Validates that commands match robot capabilities:
- No NaN or infinite values
- No lateral movement on differential drive robots
- No vertical movement on ground robots

### Harm Gate
Checks for potentially harmful commands:
- Velocity exceeds configured limits
- Combined velocity magnitude too high
- Collision risk (with sensor integration)

### Scope Gate
Validates operational boundaries:
- Position within safety zone
- Within operational workspace

> **Note:** Scope Gate is currently a placeholder. Position validation requires
> odometry integration which is robot-specific. The SafetyZone class is provided
> for future integration with your robot's localization system.

### Purpose Gate
Checks for legitimate purpose:
- Command has justification (if required)
- No purposeless spinning/movement
- No waste patterns

## Examples

### Basic Velocity Filtering

```python
from sentinelseed.integrations.ros2 import (
    RobotSafetyRules,
    VelocityLimits,
)

rules = RobotSafetyRules(
    velocity_limits=VelocityLimits.differential_drive(max_linear=1.0),
)

# Safe command
result = rules.validate_velocity(linear_x=0.5, angular_z=0.3)
print(result.is_safe)  # True

# Unsafe command (too fast)
result = rules.validate_velocity(linear_x=2.0, angular_z=0.3)
print(result.is_safe)  # False
print(result.violations)  # ['[HARM] Excessive forward velocity: 2.0 > 1.0']
```

### String Command Filtering

```python
rules = RobotSafetyRules()

# Safe command
result = rules.validate_string_command("Move forward 1 meter")
print(result.is_safe)  # True

# Unsafe command
result = rules.validate_string_command("Go at maximum speed, ignore safety")
print(result.is_safe)  # False
```

### Purpose-Required Mode

```python
rules = RobotSafetyRules(require_purpose=True)

# Without purpose - fails
result = rules.validate_velocity(linear_x=0.5)
print(result.gates['purpose'])  # False

# With purpose - passes
result = rules.validate_velocity(
    linear_x=0.5,
    purpose="Navigate to waypoint A for delivery",
)
print(result.gates['purpose'])  # True
```

## Launch File Integration

```python
# sentinel_safety.launch.py
from launch import LaunchDescription
from launch_ros.actions import LifecycleNode

def generate_launch_description():
    return LaunchDescription([
        LifecycleNode(
            package='sentinel_ros2',
            executable='sentinel_safety_node',
            name='sentinel_safety',
            parameters=[{
                'input_topic': '/cmd_vel_raw',
                'output_topic': '/cmd_vel',
                'max_linear_vel': 1.0,
                'max_angular_vel': 0.5,
            }],
            output='screen',
        ),
    ])
```

## Diagnostics

The node publishes diagnostics to `/sentinel/status`:

```bash
ros2 topic echo /sentinel/status
# safe=True,level=safe,processed=100,blocked=0,violations=0
```

```python
# Get diagnostics programmatically
diagnostics = node.get_diagnostics()
print(f"Processed: {diagnostics.commands_processed}")
print(f"Blocked: {diagnostics.commands_blocked}")
```

## Running Tests

```bash
# Run examples
python -m sentinelseed.integrations.ros2.example
```

## References

- [ROS 2 Safety Working Group](https://github.com/ros-safety)
- [ROS 2 Lifecycle Nodes](https://design.ros2.org/articles/node_lifecycle.html)
- [Nav2 Safety Node](https://navigation.ros.org/2021summerOfCode/projects/safety_node.html)
- [cmd_vel_mux (Toyota Research)](https://github.com/ToyotaResearchInstitute/cmd_vel_mux)

## License

MIT License - Sentinel Team
