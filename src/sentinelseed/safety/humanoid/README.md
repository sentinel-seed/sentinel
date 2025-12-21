# Humanoid Safety Protocol

Safety validation module for humanoid robots implementing ISO/TS 15066 compliant contact force limits, balance monitoring, and THSP (Truth-Harm-Scope-Purpose) validation.

## Overview

The Humanoid Safety Protocol provides a comprehensive safety layer for humanoid robot operations, designed to work alongside ROS2 and simulation environments like NVIDIA Isaac Lab.

### Key Features

- **ISO/TS 15066 Compliance**: Contact force limits based on biomechanical studies
- **Balance Monitoring**: ZMP/CoM tracking with fall detection
- **THSP Validation**: Four-gate safety validation for all actions
- **Robot Presets**: Pre-configured profiles for Tesla Optimus, Boston Dynamics Atlas, Figure 02
- **Environment Modes**: Industrial, personal care, and research configurations

## Installation

The module is part of the Sentinel AI Safety Framework:

```python
from sentinelseed.safety.humanoid import (
    HumanoidSafetyValidator,
    HumanoidAction,
    tesla_optimus,
)
```

## Quick Start

```python
from sentinelseed.safety.humanoid import (
    HumanoidSafetyValidator,
    HumanoidAction,
    tesla_optimus,
    BodyRegion,
)

# Create validator with Optimus configuration
validator = HumanoidSafetyValidator(
    constraints=tesla_optimus(environment="industrial"),
    strict_mode=True,
    require_purpose=True,
)

# Validate a manipulation action
action = HumanoidAction(
    joint_velocities={"left_elbow_pitch": 1.5},
    expected_contact_force=30.0,
    contact_region=BodyRegion.HAND_BACK,
    purpose="Pick up part from conveyor",
    is_collaborative=True,
)

result = validator.validate(action)

if result.is_safe:
    print("Action approved")
else:
    print(f"Blocked: {result.reasoning}")
    for violation in result.violations:
        print(f"  - {violation['description']}")
```

## Module Structure

```
sentinelseed/safety/humanoid/
├── __init__.py       # Module exports
├── body_model.py     # ISO/TS 15066 contact force limits
├── constraints.py    # Humanoid kinematics and limits
├── balance.py        # ZMP/CoM monitoring and fall detection
├── validators.py     # THSP validation for humanoid actions
├── presets.py        # Pre-configured robot profiles
├── example.py        # Usage examples
└── README.md         # This file
```

## ISO/TS 15066 Contact Force Limits

The body model implements biomechanical contact force limits from the University of Mainz study (PMC8850785), covering 29 body regions:

```python
from sentinelseed.safety.humanoid import HumanBodyModel, BodyRegion

body_model = HumanBodyModel(safety_factor=0.9)

# Get safe force for a body region
safe_force = body_model.get_safe_force(
    region=BodyRegion.NECK_FRONT,
    contact_type="quasi_static"  # or "transient"
)
print(f"Safe force for neck: {safe_force:.1f} N")

# Check if a force is safe
is_safe = body_model.is_force_safe(
    region=BodyRegion.HAND_PALM,
    force=150.0,
    contact_type="transient"
)
```

### Body Regions and Force Limits

| Region | Quasi-Static (N) | Transient (N) |
|--------|------------------|---------------|
| Forehead | 110 | 150 |
| Temple | 60 | 90 |
| Neck (front) | 35 | 55 |
| Chest | 90 | 110 |
| Hand (palm) | 150 | 330 |

See `body_model.py` for complete list of 29 body regions.

## Robot Presets

### Tesla Optimus Gen 2

```python
from sentinelseed.safety.humanoid import tesla_optimus

# Industrial configuration
optimus = tesla_optimus(
    environment="industrial",  # or "personal_care", "research"
    include_hands=True,        # Include 22 DOF per hand
)
```

Specifications:
- Height: 1.73m
- Weight: 70 kg
- Body DOF: 28 (+ 22 per hand optional)
- Max walking speed: 2.2 m/s (research mode)

### Boston Dynamics Atlas

```python
from sentinelseed.safety.humanoid import boston_dynamics_atlas

atlas = boston_dynamics_atlas(environment="research")
```

Specifications:
- Height: 1.5m
- Weight: 89 kg
- DOF: 28
- Max running speed: 5.0 m/s (research mode)
- Dynamic balance and acrobatics capable

### Figure 02

```python
from sentinelseed.safety.humanoid import figure_02

figure = figure_02(
    environment="industrial",
    include_hands=True,  # 16 DOF per hand
)
```

Specifications:
- Height: 1.67m
- Weight: 60 kg
- DOF: 28 (+ 16 per hand optional)
- 20+ hour battery life

## Balance Monitoring

Track balance state and detect potential falls:

```python
from sentinelseed.safety.humanoid import (
    BalanceMonitor,
    IMUReading,
    ZMPState,
    CoMState,
)

# Create balance monitor (uses default config)
monitor = BalanceMonitor()

# Update with sensor data
monitor.update_imu(IMUReading(
    roll=0.0,
    pitch=0.0,
    yaw=0.0,
    roll_rate=0.0,
    pitch_rate=0.0,
    yaw_rate=0.0,
    acc_x=0.0,
    acc_y=0.0,
    acc_z=9.81,
    timestamp=0.0,
))

monitor.update_zmp(ZMPState(x=0.0, y=0.0, is_stable=True, margin=0.1))
monitor.update_com(CoMState(x=0.0, y=0.0, z=0.9))

# Assess balance
assessment = monitor.assess_balance()
print(f"Balance state: {assessment.state.value}")
print(f"Is safe: {assessment.is_safe}")

if not assessment.is_safe:
    print(f"Fall direction: {assessment.fall_direction.value}")
    print(f"Action: {assessment.recommended_action}")
```

### Balance States

| State | Description |
|-------|-------------|
| STABLE | Normal balance, all parameters within limits |
| MARGINALLY_STABLE | Near stability limits, caution advised |
| UNSTABLE | Actively losing balance |
| FALLING | Fall detected, mitigation active |
| FALLEN | Robot is on the ground |
| RECOVERING | Getting back up |
| EMERGENCY_STOP | Emergency stop activated |

## THSP Validation Gates

Every action passes through four safety gates:

### 1. Truth Gate
Validates physical possibility:
- Joint positions within mechanical limits
- Velocities within actuator capabilities
- No NaN or infinite values

### 2. Harm Gate
Prevents injury and damage:
- Contact forces within ISO/TS 15066 limits
- End effector velocities for collaborative work
- Balance stability assessment

### 3. Scope Gate
Enforces operational boundaries:
- Position within safety zones
- Zone-specific speed limits
- Maximum operating height

### 4. Purpose Gate
Requires legitimate objectives:
- Explicit purpose statement (if required)
- Screens for harmful intent patterns
- Ensures beneficial action goals

## Environment Modes

Each preset supports three operational modes:

| Mode | Use Case | Constraints |
|------|----------|-------------|
| `industrial` | Factory floor, ISO 10218 | Conservative, no running |
| `personal_care` | Home, healthcare, ISO 13482 | Very conservative, low forces |
| `research` | Lab testing | Less restrictive, full capabilities |

```python
# Industrial (most restrictive)
optimus_factory = tesla_optimus(environment="industrial")

# Personal care (moderate)
optimus_home = tesla_optimus(environment="personal_care")

# Research (least restrictive)
optimus_lab = tesla_optimus(environment="research")
```

## Integration with ROS2

The module integrates with the Sentinel ROS2 Safety Node:

```python
from sentinelseed.integrations.ros2 import SentinelSafetyNode
from sentinelseed.safety.humanoid import (
    HumanoidSafetyValidator,
    tesla_optimus,
)

# Create humanoid validator
humanoid_validator = HumanoidSafetyValidator(
    constraints=tesla_optimus(environment="industrial"),
)

# Add to ROS2 node
node = SentinelSafetyNode()
node.add_validator("humanoid", humanoid_validator)
```

## Integration with Isaac Lab

For NVIDIA Isaac Lab simulation:

```python
from sentinelseed.integrations.isaac_lab import SentinelSafetyWrapper, RobotConstraints
from sentinelseed.safety.humanoid import (
    HumanoidSafetyValidator,
    tesla_optimus,
)

# Create humanoid validator
humanoid_validator = HumanoidSafetyValidator(
    constraints=tesla_optimus(environment="research"),
)

# Wrap Isaac Lab environment with safety validation
env = SentinelSafetyWrapper(
    env=isaac_lab_env,
    constraints=RobotConstraints.franka_default(),  # Or custom constraints
    mode="clamp",  # Options: "block", "clamp", "warn", "monitor"
)
```

## Running Examples

```bash
python -m sentinelseed.safety.humanoid.example
```

This runs through all examples demonstrating:
1. Basic action validation
2. Robot presets
3. Contact force validation
4. Balance monitoring
5. Safe state transitions
6. Full validation pipeline

## References

### Standards
- ISO 10218:2025 - Robots and robotic devices - Safety requirements for industrial robots
- ISO 13482:2014 - Robots and robotic devices - Safety requirements for personal care robots
- ISO/TS 15066:2016 - Robots and robotic devices - Collaborative robots

### Research
- PMC8850785 - "Biomechanical limits for safe human-robot interaction" (University of Mainz study)
- Boston Dynamics Atlas specifications
- Tesla Optimus (Gen 2) technical presentations
- Figure AI official specifications

## License

MIT License - See the main Sentinel repository for details.

---

Sentinel Team - Practical AI Alignment for Developers
