"""
Humanoid Safety Protocol - Usage Examples.

This module demonstrates how to use the Humanoid Safety Protocol
for validating humanoid robot actions.

Run this example:
    python -m sentinelseed.safety.humanoid.example
"""

import logging
from sentinelseed.safety.humanoid import (
    # Validators
    HumanoidSafetyValidator,
    HumanoidAction,
    ValidationResult,
    SafetyLevel,
    # Body model
    HumanBodyModel,
    BodyRegion,
    # Constraints
    HumanoidConstraints,
    HumanoidLimb,
    OperationalLimits,
    SafetyZone,
    create_generic_humanoid,
    # Balance
    BalanceMonitor,
    BalanceState,
    IMUReading,
    ZMPState,
    CoMState,
    SafeStateManager,
    SafeState,
    FallDirection,
    # Presets
    tesla_optimus,
    boston_dynamics_atlas,
    figure_02,
    list_presets,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_validation():
    """Basic action validation with generic humanoid."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Action Validation")
    print("=" * 60)

    # Create a generic humanoid configuration
    humanoid = create_generic_humanoid(
        name="demo_humanoid",
        total_dof=28,
        total_mass=65.0,
        height=1.7,
    )

    # Create validator
    validator = HumanoidSafetyValidator(
        constraints=humanoid,
        strict_mode=False,
        require_purpose=True,
        log_violations=False,
    )

    # Test 1: Safe action
    print("\nTest 1: Safe arm movement")
    safe_action = HumanoidAction(
        joint_positions={
            "left_shoulder_pitch": 0.5,
            "left_elbow": -1.0,
        },
        joint_velocities={
            "left_shoulder_pitch": 1.0,
            "left_elbow": 1.5,
        },
        purpose="Pick up object from table",
    )

    result = validator.validate(safe_action)
    print(f"  Result: {result.level.value}")
    print(f"  Is Safe: {result.is_safe}")
    print(f"  Reasoning: {result.reasoning}")

    # Test 2: Dangerous action - excessive contact force
    print("\nTest 2: Dangerous contact force")
    dangerous_action = HumanoidAction(
        expected_contact_force=120.0,  # Exceeds safe limits
        contact_region=BodyRegion.NECK_FRONT,  # Sensitive area
        purpose="Push object",
    )

    result = validator.validate(dangerous_action)
    print(f"  Result: {result.level.value}")
    print(f"  Is Safe: {result.is_safe}")
    print(f"  Violations: {len(result.violations)}")
    if result.violations:
        print(f"  First violation: {result.violations[0]['description']}")

    # Test 3: Invalid joint position
    print("\nTest 3: Invalid joint position")
    invalid_action = HumanoidAction(
        joint_positions={
            "left_elbow": 1.0,  # Elbow can't extend beyond 0
        },
        purpose="Test reach",
    )

    result = validator.validate(invalid_action)
    print(f"  Result: {result.level.value}")
    print(f"  Is Safe: {result.is_safe}")
    print(f"  Gate failures: {[k for k, v in result.gates.items() if not v]}")


def example_preset_robots():
    """Using pre-configured robot presets."""
    print("\n" + "=" * 60)
    print("Example 2: Robot Presets")
    print("=" * 60)

    # List available presets
    print("\nAvailable presets:")
    for preset in list_presets():
        print(f"  - {preset['name']}: {preset['dof']} DOF, {preset['weight']}, {preset['height']}")

    # Create Tesla Optimus for industrial use
    print("\n--- Tesla Optimus (Industrial) ---")
    optimus = tesla_optimus(environment="industrial", include_hands=True)
    print(f"  Name: {optimus.name}")
    print(f"  DOF: {optimus.total_dof}")
    print(f"  Mass: {optimus.total_mass} kg")
    print(f"  Height: {optimus.height} m")
    print(f"  Max walking speed: {optimus.operational_limits.max_walking_speed} m/s")
    print(f"  Max contact force: {optimus.operational_limits.max_contact_force} N")

    # Create Atlas for research
    print("\n--- Boston Dynamics Atlas (Research) ---")
    atlas = boston_dynamics_atlas(environment="research")
    print(f"  Name: {atlas.name}")
    print(f"  DOF: {atlas.total_dof}")
    print(f"  Mass: {atlas.total_mass} kg")
    print(f"  Max running speed: {atlas.operational_limits.max_running_speed} m/s")
    print(f"  Allows running: {atlas.allows_running}")

    # Create Figure 02 for industrial
    print("\n--- Figure 02 (Industrial) ---")
    figure = figure_02(environment="industrial", include_hands=True)
    print(f"  Name: {figure.name}")
    print(f"  DOF: {figure.total_dof}")
    print(f"  Mass: {figure.total_mass} kg")
    print(f"  Max payload: {figure.operational_limits.max_payload} kg")


def example_contact_force_validation():
    """ISO/TS 15066 contact force validation."""
    print("\n" + "=" * 60)
    print("Example 3: Contact Force Validation (ISO/TS 15066)")
    print("=" * 60)

    # Create body model with safety factor
    body_model = HumanBodyModel(safety_factor=0.9)

    # Check different body regions
    test_cases = [
        (BodyRegion.HAND_PALM, "quasi_static", 150.0),
        (BodyRegion.HAND_PALM, "transient", 250.0),
        (BodyRegion.NECK_FRONT, "quasi_static", 50.0),  # Dangerous!
        (BodyRegion.CHEST_STERNUM, "transient", 100.0),
        (BodyRegion.FACE, "quasi_static", 40.0),  # Dangerous!
    ]

    print("\nBody region contact force limits:")
    for region, contact_type, force in test_cases:
        safe_limit = body_model.get_safe_force(region, contact_type)
        is_safe = body_model.is_force_safe(region, force, contact_type)

        print(f"\n  {region.value} ({contact_type}):")
        print(f"    Safe limit: {safe_limit:.1f} N")
        print(f"    Applied force: {force:.1f} N")
        print(f"    Is safe: {is_safe}")


def example_balance_monitoring():
    """Balance monitoring and fall detection."""
    print("\n" + "=" * 60)
    print("Example 4: Balance Monitoring")
    print("=" * 60)

    # Create humanoid and balance monitor
    humanoid = tesla_optimus(environment="industrial")
    balance_monitor = BalanceMonitor()  # Uses default config

    # Simulate stable standing
    print("\nSimulating stable standing:")
    imu = IMUReading(
        roll=0.0,
        pitch=0.0,
        yaw=0.0,
        roll_rate=0.0,
        pitch_rate=0.0,
        yaw_rate=0.0,
        acc_x=0.0,
        acc_y=0.0,
        acc_z=9.81,  # Only gravity
        timestamp=0.0,
    )
    zmp = ZMPState(x=0.0, y=0.0, is_stable=True, margin=0.1)  # 10cm margin
    com = CoMState(x=0.0, y=0.0, z=0.9)

    balance_monitor.update_imu(imu)
    balance_monitor.update_zmp(zmp)
    balance_monitor.update_com(com)

    assessment = balance_monitor.assess_balance()
    print(f"  Balance state: {assessment.state.value}")
    print(f"  Is safe: {assessment.is_safe}")
    print(f"  Confidence: {assessment.confidence:.2f}")

    # Simulate falling
    print("\nSimulating falling forward:")
    imu_falling = IMUReading(
        roll=0.0,
        pitch=0.4,  # Tilted forward
        yaw=0.0,
        roll_rate=0.0,
        pitch_rate=1.5,  # Pitching forward
        yaw_rate=0.0,
        acc_x=3.0,  # Forward acceleration
        acc_y=0.0,
        acc_z=8.0,
        timestamp=1.0,
    )
    zmp_falling = ZMPState(x=0.15, y=0.0, is_stable=False, margin=0.0)

    balance_monitor.update_imu(imu_falling)
    balance_monitor.update_zmp(zmp_falling)

    assessment = balance_monitor.assess_balance()
    print(f"  Balance state: {assessment.state.value}")
    print(f"  Is safe: {assessment.is_safe}")
    print(f"  Fall direction: {assessment.fall_direction.value if assessment.fall_direction else 'N/A'}")
    print(f"  Recommended: {assessment.recommended_action}")


def example_safe_state_transitions():
    """Safe state management for falls."""
    print("\n" + "=" * 60)
    print("Example 5: Safe State Transitions")
    print("=" * 60)

    # Create safe state manager (starts in STANDING)
    safe_state_manager = SafeStateManager()  # Default: SafeState.STANDING

    print("\nSafe states and transitions:")
    print(f"  Current state: {safe_state_manager.current_state.value}")
    print(f"  Valid transitions: {[s.value for s in safe_state_manager.get_valid_transitions()]}")

    # Check if we can transition to crouch
    print("\nTransitioning to CROUCHING:")
    can_crouch = safe_state_manager.can_transition(SafeState.CROUCHING)
    print(f"  Can transition: {can_crouch}")

    if can_crouch:
        started = safe_state_manager.start_transition(SafeState.CROUCHING)
        print(f"  Transition started: {started}")
        print(f"  Is transitioning: {safe_state_manager.is_transitioning}")

        # Simulate transition complete
        safe_state_manager.confirm_transition(SafeState.CROUCHING)
        print(f"  Current state: {safe_state_manager.current_state.value}")

    # Get safest state for a fall
    print("\nRecommended state for forward fall:")
    safest = safe_state_manager.get_safest_state(fall_direction=FallDirection.FORWARD)
    print(f"  Recommended: {safest.value}")
    est_time = safe_state_manager.get_transition_time(safest)
    print(f"  Estimated transition time: {est_time:.1f}s")


def example_full_validation_pipeline():
    """Complete validation pipeline example."""
    print("\n" + "=" * 60)
    print("Example 6: Full Validation Pipeline")
    print("=" * 60)

    # Setup: Optimus in industrial environment with balance monitoring
    optimus = tesla_optimus(environment="industrial")
    balance_monitor = BalanceMonitor()

    # Initialize with stable state
    balance_monitor.update_imu(IMUReading(
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
    balance_monitor.update_zmp(ZMPState(x=0.0, y=0.0, is_stable=True, margin=0.1))
    balance_monitor.update_com(CoMState(x=0.0, y=0.0, z=0.9))

    # Create full validator
    validator = HumanoidSafetyValidator(
        constraints=optimus,
        balance_monitor=balance_monitor,
        strict_mode=True,
        require_purpose=True,
        log_violations=False,
    )

    # Scenario: Pick and place operation
    print("\nScenario: Pick and place operation")

    # Action 1: Reach for object
    print("\n1. Reaching for object:")
    reach_action = HumanoidAction(
        joint_velocities={
            "left_shoulder_pitch": 1.2,
            "left_elbow_pitch": 1.5,
        },
        end_effector_velocities={HumanoidLimb.LEFT_ARM: 0.4},
        robot_position=(0.0, 0.0, 1.0),
        purpose="Reach for part on conveyor",
        is_collaborative=True,
    )

    result = validator.validate(reach_action)
    print(f"  Approved: {result.is_safe}")
    print(f"  Level: {result.level.value}")

    # Action 2: Grasp with contact
    print("\n2. Grasping (potential contact with worker):")
    grasp_action = HumanoidAction(
        expected_contact_force=25.0,  # Light touch
        contact_region=BodyRegion.HAND_BACK,
        purpose="Grasp part with care",
        is_collaborative=True,
    )

    result = validator.validate(grasp_action)
    print(f"  Approved: {result.is_safe}")
    if result.contact_assessment:
        print(f"  Contact region: {result.contact_assessment['region']}")
        print(f"  Force safe: {result.contact_assessment['is_safe']}")

    # Action 3: Dangerous - too fast in collaborative zone
    print("\n3. Moving too fast (should be blocked):")
    fast_action = HumanoidAction(
        end_effector_velocities={HumanoidLimb.RIGHT_ARM: 1.2},
        robot_position=(1.0, 0.0, 1.0),  # In collaborative zone
        purpose="Move arm quickly",
        is_collaborative=True,
    )

    result = validator.validate(fast_action)
    print(f"  Approved: {result.is_safe}")
    print(f"  Level: {result.level.value}")
    if result.violations:
        print(f"  Reason: {result.violations[0]['description']}")

    # Print statistics
    print("\n--- Validation Statistics ---")
    stats = validator.get_stats()
    print(f"  Total validated: {stats['total_validated']}")
    print(f"  Total violations: {stats['total_violations']}")
    print(f"  Gate failures: {stats['gate_failures']}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Humanoid Safety Protocol - Examples")
    print("Sentinel AI Safety Framework")
    print("=" * 60)

    example_basic_validation()
    example_preset_robots()
    example_contact_force_validation()
    example_balance_monitoring()
    example_safe_state_transitions()
    example_full_validation_pipeline()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
