"""
Humanoid Robot Presets.

Pre-configured constraint sets for popular humanoid robots:
- Tesla Optimus (Gen 2)
- Boston Dynamics Atlas (Electric)
- Figure 02

These presets are based on publicly available specifications and
conservative safety estimates. They should be refined with actual
robot specifications when available.

Note: Where exact specifications are not public, conservative
estimates are used based on comparable systems and industry standards.
"""

from sentinelseed.safety.humanoid.constraints import (
    HumanoidConstraints,
    HumanoidLimb,
    LimbSpec,
    JointSpec,
    JointType,
    OperationalLimits,
    SafetyZone,
)


def tesla_optimus(
    environment: str = "industrial",
    include_hands: bool = False,
) -> HumanoidConstraints:
    """
    Create constraints for Tesla Optimus (Gen 2).

    Specifications based on Tesla AI Day 2023 and We, Robot 2024:
    - Height: 1.73m (5'8")
    - Weight: ~70 kg (estimated from Tesla disclosures)
    - Body DOF: 28 (excluding hands)
    - Hand DOF: 22 per hand (11 actuated degrees per hand)
    - Payload: up to 20 kg
    - Walking speed: up to 8 km/h (2.2 m/s)
    - Actuators: Rotary, linear (custom Tesla design)

    Args:
        environment: "industrial", "personal_care", or "research"
        include_hands: If True, includes 22 DOF per hand

    Returns:
        HumanoidConstraints configured for Tesla Optimus

    References:
        - Tesla AI Day 2023
        - Tesla We, Robot Event 2024
        - Tesla investor presentations
    """
    limbs = {}

    # Head (2 DOF - pan/tilt)
    limbs[HumanoidLimb.HEAD] = LimbSpec(
        limb=HumanoidLimb.HEAD,
        joints=[
            JointSpec(
                "head_pan", JointType.REVOLUTE, HumanoidLimb.HEAD,
                position_min=-1.4,  # ~80 degrees
                position_max=1.4,
                velocity_max=2.0,
                acceleration_max=8.0,
                torque_max=10.0,
                is_safety_critical=True,
            ),
            JointSpec(
                "head_tilt", JointType.REVOLUTE, HumanoidLimb.HEAD,
                position_min=-0.4,  # Look down ~23 degrees
                position_max=0.6,   # Look up ~34 degrees
                velocity_max=2.0,
                acceleration_max=8.0,
                torque_max=10.0,
                is_safety_critical=True,
            ),
        ],
        mass=3.5,  # Estimated head mass
        length=0.22,
    )

    # Torso (3 DOF - pitch, roll, yaw)
    limbs[HumanoidLimb.TORSO] = LimbSpec(
        limb=HumanoidLimb.TORSO,
        joints=[
            JointSpec(
                "torso_pitch", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-0.35,  # Forward lean
                position_max=0.25,   # Backward lean
                velocity_max=1.5,
                acceleration_max=5.0,
                torque_max=200.0,  # High torque for stability
            ),
            JointSpec(
                "torso_roll", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-0.2,
                position_max=0.2,
                velocity_max=1.5,
                acceleration_max=5.0,
                torque_max=150.0,
            ),
            JointSpec(
                "torso_yaw", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-0.6,  # ~34 degrees rotation
                position_max=0.6,
                velocity_max=1.5,
                acceleration_max=5.0,
                torque_max=150.0,
            ),
        ],
        mass=22.0,  # Torso with batteries and electronics
        length=0.45,
    )

    # Arms (7 DOF each - shoulder 3, elbow 2, wrist 2)
    # Tesla Optimus uses actuator-based arms with high backdrivability
    for side, limb_id in [("left", HumanoidLimb.LEFT_ARM), ("right", HumanoidLimb.RIGHT_ARM)]:
        limbs[limb_id] = LimbSpec(
            limb=limb_id,
            joints=[
                JointSpec(
                    f"{side}_shoulder_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-2.0,  # Reach behind
                    position_max=2.0,   # Reach forward/up
                    velocity_max=3.0,
                    acceleration_max=12.0,
                    torque_max=55.0,  # Based on Tesla specs
                ),
                JointSpec(
                    f"{side}_shoulder_roll", JointType.REVOLUTE, limb_id,
                    position_min=-1.6 if side == "left" else -0.5,
                    position_max=0.5 if side == "left" else 1.6,
                    velocity_max=3.0,
                    acceleration_max=12.0,
                    torque_max=55.0,
                ),
                JointSpec(
                    f"{side}_shoulder_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-1.8,
                    position_max=1.8,
                    velocity_max=3.0,
                    acceleration_max=12.0,
                    torque_max=35.0,
                ),
                JointSpec(
                    f"{side}_elbow_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-2.3,  # Full flexion
                    position_max=0.0,   # Full extension
                    velocity_max=3.5,
                    acceleration_max=15.0,
                    torque_max=35.0,
                ),
                JointSpec(
                    f"{side}_elbow_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-1.5,
                    position_max=1.5,
                    velocity_max=3.0,
                    acceleration_max=12.0,
                    torque_max=20.0,
                ),
                JointSpec(
                    f"{side}_wrist_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-1.0,
                    position_max=1.0,
                    velocity_max=4.0,
                    acceleration_max=15.0,
                    torque_max=12.0,
                ),
                JointSpec(
                    f"{side}_wrist_roll", JointType.REVOLUTE, limb_id,
                    position_min=-1.8,
                    position_max=1.8,
                    velocity_max=4.0,
                    acceleration_max=15.0,
                    torque_max=12.0,
                ),
            ],
            mass=4.5,
            length=0.58,
            max_reach=0.75,
            end_effector_mass=0.8,
        )

    # Hands (11 DOF each if included)
    # Tesla hands use tendons/actuators for 11 degrees per hand
    if include_hands:
        for side, limb_id in [("left", HumanoidLimb.LEFT_HAND), ("right", HumanoidLimb.RIGHT_HAND)]:
            hand_joints = []
            # Thumb (3 DOF)
            for i, name in enumerate(["thumb_cmc", "thumb_mcp", "thumb_ip"]):
                hand_joints.append(JointSpec(
                    f"{side}_{name}", JointType.REVOLUTE, limb_id,
                    position_min=0.0, position_max=1.6,
                    velocity_max=4.0, acceleration_max=20.0, torque_max=2.0,
                ))
            # Index finger (2 DOF)
            for i, name in enumerate(["index_mcp", "index_pip"]):
                hand_joints.append(JointSpec(
                    f"{side}_{name}", JointType.REVOLUTE, limb_id,
                    position_min=0.0, position_max=1.7,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=1.5,
                ))
            # Middle, ring, pinky (2 DOF each, simplified)
            for finger in ["middle", "ring", "pinky"]:
                for joint in ["mcp", "pip"]:
                    hand_joints.append(JointSpec(
                        f"{side}_{finger}_{joint}", JointType.REVOLUTE, limb_id,
                        position_min=0.0, position_max=1.7,
                        velocity_max=5.0, acceleration_max=25.0, torque_max=1.5,
                    ))

            limbs[limb_id] = LimbSpec(
                limb=limb_id,
                joints=hand_joints,
                mass=0.5,
                length=0.18,
                end_effector_mass=0.1,
            )

    # Legs (6 DOF each - hip 3, knee 1, ankle 2)
    for side, limb_id in [("left", HumanoidLimb.LEFT_LEG), ("right", HumanoidLimb.RIGHT_LEG)]:
        limbs[limb_id] = LimbSpec(
            limb=limb_id,
            joints=[
                JointSpec(
                    f"{side}_hip_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-0.4,
                    position_max=0.4,
                    velocity_max=2.5,
                    acceleration_max=10.0,
                    torque_max=110.0,  # High torque for walking
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_hip_roll", JointType.REVOLUTE, limb_id,
                    position_min=-0.5 if side == "left" else -0.3,
                    position_max=0.3 if side == "left" else 0.5,
                    velocity_max=2.5,
                    acceleration_max=10.0,
                    torque_max=110.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_hip_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-1.8,  # Flexion (kicking forward)
                    position_max=0.5,   # Extension (kicking back)
                    velocity_max=3.0,
                    acceleration_max=12.0,
                    torque_max=180.0,  # Linear actuator, high force
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_knee", JointType.REVOLUTE, limb_id,
                    position_min=0.0,   # Full extension
                    position_max=2.5,   # Full flexion
                    velocity_max=3.5,
                    acceleration_max=15.0,
                    torque_max=180.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_ankle_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-0.7,  # Plantarflexion
                    position_max=0.5,   # Dorsiflexion
                    velocity_max=2.5,
                    acceleration_max=10.0,
                    torque_max=90.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_ankle_roll", JointType.REVOLUTE, limb_id,
                    position_min=-0.35,
                    position_max=0.35,
                    velocity_max=2.0,
                    acceleration_max=8.0,
                    torque_max=50.0,
                    is_safety_critical=True,
                ),
            ],
            mass=13.0,  # Including actuators
            length=0.92,
            end_effector_mass=1.2,
        )

    # Select operational limits based on environment
    if environment == "industrial":
        limits = OperationalLimits(
            max_walking_speed=1.2,  # Conservative for factory
            max_running_speed=0.0,  # No running in industrial
            max_arm_speed=1.5,
            max_contact_force=50.0,
            max_payload=20.0,
            min_stability_margin=0.08,
            emergency_stop_time=0.4,
            max_operating_height=1.9,
        )
    elif environment == "personal_care":
        limits = OperationalLimits(
            max_walking_speed=0.8,
            max_running_speed=0.0,
            max_arm_speed=1.0,
            max_contact_force=35.0,  # More conservative around humans
            max_payload=10.0,
            min_stability_margin=0.1,
            emergency_stop_time=0.3,
            max_operating_height=1.8,
        )
    else:  # research
        limits = OperationalLimits(
            max_walking_speed=2.2,  # Up to 8 km/h
            max_running_speed=3.0,  # Can run in controlled environments
            max_arm_speed=2.5,
            max_contact_force=100.0,
            max_payload=20.0,
            min_stability_margin=0.05,
            emergency_stop_time=0.5,
            max_operating_height=2.0,
        )

    # Calculate total DOF
    total_dof = 28  # Standard body DOF
    if include_hands:
        total_dof += 22  # 11 per hand

    return HumanoidConstraints(
        name="Tesla Optimus Gen 2",
        total_dof=total_dof,
        total_mass=70.0,
        height=1.73,
        limbs=limbs,
        operational_limits=limits,
        safety_zones=[
            SafetyZone.collaborative_workspace(size=4.0),
        ],
        contact_force_limit=limits.max_contact_force,
        requires_balance_check=True,
        allows_running=(environment == "research"),
    )


def boston_dynamics_atlas(
    environment: str = "research",
) -> HumanoidConstraints:
    """
    Create constraints for Boston Dynamics Atlas (Electric, 2024).

    Specifications based on Boston Dynamics official releases:
    - Height: ~1.5m (4'11")
    - Weight: ~89 kg (196 lb) - electric version
    - DOF: ~28 (estimated body DOF)
    - Notable: Full-body acrobatics capability
    - Electric actuators with high bandwidth control

    Note: Atlas is primarily a research platform with capabilities
    beyond typical industrial/personal care robots. The constraints
    here are conservative estimates for collaborative use.

    Args:
        environment: "industrial", "personal_care", or "research"

    Returns:
        HumanoidConstraints configured for Atlas

    References:
        - Boston Dynamics official specifications
        - IEEE publications on Atlas
    """
    limbs = {}

    # Head (2 DOF) - Atlas has sensor head with limited articulation
    limbs[HumanoidLimb.HEAD] = LimbSpec(
        limb=HumanoidLimb.HEAD,
        joints=[
            JointSpec(
                "head_pan", JointType.REVOLUTE, HumanoidLimb.HEAD,
                position_min=-1.2, position_max=1.2,
                velocity_max=3.0, acceleration_max=15.0, torque_max=15.0,
                is_safety_critical=True,
            ),
            JointSpec(
                "head_tilt", JointType.REVOLUTE, HumanoidLimb.HEAD,
                position_min=-0.5, position_max=0.8,
                velocity_max=3.0, acceleration_max=15.0, torque_max=15.0,
                is_safety_critical=True,
            ),
        ],
        mass=5.0,
        length=0.25,
    )

    # Torso (3 DOF) - Atlas has articulated torso for dynamic movements
    limbs[HumanoidLimb.TORSO] = LimbSpec(
        limb=HumanoidLimb.TORSO,
        joints=[
            JointSpec(
                "torso_pitch", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-0.5, position_max=0.5,
                velocity_max=3.0, acceleration_max=15.0, torque_max=300.0,
            ),
            JointSpec(
                "torso_roll", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-0.4, position_max=0.4,
                velocity_max=3.0, acceleration_max=15.0, torque_max=250.0,
            ),
            JointSpec(
                "torso_yaw", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-1.0, position_max=1.0,
                velocity_max=3.0, acceleration_max=15.0, torque_max=250.0,
            ),
        ],
        mass=30.0,
        length=0.45,
    )

    # Arms (7 DOF each) - High performance arms for manipulation
    for side, limb_id in [("left", HumanoidLimb.LEFT_ARM), ("right", HumanoidLimb.RIGHT_ARM)]:
        limbs[limb_id] = LimbSpec(
            limb=limb_id,
            joints=[
                JointSpec(
                    f"{side}_shoulder_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-2.2, position_max=2.2,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=80.0,
                ),
                JointSpec(
                    f"{side}_shoulder_roll", JointType.REVOLUTE, limb_id,
                    position_min=-1.8 if side == "left" else -0.6,
                    position_max=0.6 if side == "left" else 1.8,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=80.0,
                ),
                JointSpec(
                    f"{side}_shoulder_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-2.0, position_max=2.0,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=50.0,
                ),
                JointSpec(
                    f"{side}_elbow_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-2.4, position_max=0.0,
                    velocity_max=6.0, acceleration_max=30.0, torque_max=50.0,
                ),
                JointSpec(
                    f"{side}_elbow_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-1.8, position_max=1.8,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=30.0,
                ),
                JointSpec(
                    f"{side}_wrist_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-1.2, position_max=1.2,
                    velocity_max=6.0, acceleration_max=30.0, torque_max=20.0,
                ),
                JointSpec(
                    f"{side}_wrist_roll", JointType.REVOLUTE, limb_id,
                    position_min=-2.0, position_max=2.0,
                    velocity_max=6.0, acceleration_max=30.0, torque_max=20.0,
                ),
            ],
            mass=6.0,
            length=0.55,
            max_reach=0.70,
            end_effector_mass=1.0,
        )

    # Legs (6 DOF each) - High performance for dynamic locomotion
    for side, limb_id in [("left", HumanoidLimb.LEFT_LEG), ("right", HumanoidLimb.RIGHT_LEG)]:
        limbs[limb_id] = LimbSpec(
            limb=limb_id,
            joints=[
                JointSpec(
                    f"{side}_hip_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-0.6, position_max=0.6,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=200.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_hip_roll", JointType.REVOLUTE, limb_id,
                    position_min=-0.6 if side == "left" else -0.3,
                    position_max=0.3 if side == "left" else 0.6,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=200.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_hip_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-2.0, position_max=0.8,
                    velocity_max=6.0, acceleration_max=30.0, torque_max=300.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_knee", JointType.REVOLUTE, limb_id,
                    position_min=0.0, position_max=2.8,
                    velocity_max=7.0, acceleration_max=35.0, torque_max=300.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_ankle_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-0.9, position_max=0.7,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=150.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_ankle_roll", JointType.REVOLUTE, limb_id,
                    position_min=-0.5, position_max=0.5,
                    velocity_max=4.0, acceleration_max=20.0, torque_max=80.0,
                    is_safety_critical=True,
                ),
            ],
            mass=15.0,
            length=0.80,
            end_effector_mass=1.5,
        )

    # Operational limits based on environment
    if environment == "industrial":
        limits = OperationalLimits(
            max_walking_speed=1.0,
            max_running_speed=0.0,
            max_arm_speed=1.5,
            max_contact_force=50.0,
            max_payload=25.0,
            min_stability_margin=0.1,
            emergency_stop_time=0.3,
            max_operating_height=1.7,
        )
    elif environment == "personal_care":
        limits = OperationalLimits(
            max_walking_speed=0.6,
            max_running_speed=0.0,
            max_arm_speed=1.0,
            max_contact_force=35.0,
            max_payload=15.0,
            min_stability_margin=0.12,
            emergency_stop_time=0.25,
            max_operating_height=1.6,
        )
    else:  # research - Atlas full capabilities
        limits = OperationalLimits(
            max_walking_speed=2.5,
            max_running_speed=5.0,  # Atlas can run and do parkour
            max_arm_speed=4.0,
            max_contact_force=150.0,
            max_payload=30.0,
            min_stability_margin=0.03,  # Highly dynamic balance
            emergency_stop_time=0.5,
            max_operating_height=2.0,
        )

    return HumanoidConstraints(
        name="Boston Dynamics Atlas Electric",
        total_dof=28,
        total_mass=89.0,
        height=1.5,
        limbs=limbs,
        operational_limits=limits,
        safety_zones=[
            SafetyZone.collaborative_workspace(size=5.0),
            SafetyZone.restricted_zone(),  # High-speed zone for research
        ],
        contact_force_limit=limits.max_contact_force,
        requires_balance_check=True,
        allows_running=(environment == "research"),
    )


def figure_02(
    environment: str = "industrial",
    include_hands: bool = True,
) -> HumanoidConstraints:
    """
    Create constraints for Figure 02.

    Specifications based on Figure AI official releases:
    - Height: ~1.67m (5'6")
    - Weight: ~60 kg (estimated)
    - Hand DOF: 16 per hand (highly dexterous)
    - Battery: 20+ hour runtime
    - Focus: Industrial and commercial applications

    Figure 02 is designed for practical work applications with
    emphasis on dexterity and long operational time.

    Args:
        environment: "industrial", "personal_care", or "research"
        include_hands: If True, includes 16 DOF per hand

    Returns:
        HumanoidConstraints configured for Figure 02

    References:
        - Figure AI official announcements
        - BMW factory deployment data
    """
    limbs = {}

    # Head (2 DOF)
    limbs[HumanoidLimb.HEAD] = LimbSpec(
        limb=HumanoidLimb.HEAD,
        joints=[
            JointSpec(
                "head_pan", JointType.REVOLUTE, HumanoidLimb.HEAD,
                position_min=-1.3, position_max=1.3,
                velocity_max=2.5, acceleration_max=10.0, torque_max=12.0,
                is_safety_critical=True,
            ),
            JointSpec(
                "head_tilt", JointType.REVOLUTE, HumanoidLimb.HEAD,
                position_min=-0.4, position_max=0.5,
                velocity_max=2.5, acceleration_max=10.0, torque_max=12.0,
                is_safety_critical=True,
            ),
        ],
        mass=3.0,
        length=0.20,
    )

    # Torso (3 DOF)
    limbs[HumanoidLimb.TORSO] = LimbSpec(
        limb=HumanoidLimb.TORSO,
        joints=[
            JointSpec(
                "torso_pitch", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-0.3, position_max=0.3,
                velocity_max=1.5, acceleration_max=6.0, torque_max=180.0,
            ),
            JointSpec(
                "torso_roll", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-0.25, position_max=0.25,
                velocity_max=1.5, acceleration_max=6.0, torque_max=150.0,
            ),
            JointSpec(
                "torso_yaw", JointType.REVOLUTE, HumanoidLimb.TORSO,
                position_min=-0.7, position_max=0.7,
                velocity_max=1.5, acceleration_max=6.0, torque_max=150.0,
            ),
        ],
        mass=20.0,
        length=0.42,
    )

    # Arms (7 DOF each)
    for side, limb_id in [("left", HumanoidLimb.LEFT_ARM), ("right", HumanoidLimb.RIGHT_ARM)]:
        limbs[limb_id] = LimbSpec(
            limb=limb_id,
            joints=[
                JointSpec(
                    f"{side}_shoulder_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-2.0, position_max=2.0,
                    velocity_max=2.8, acceleration_max=12.0, torque_max=50.0,
                ),
                JointSpec(
                    f"{side}_shoulder_roll", JointType.REVOLUTE, limb_id,
                    position_min=-1.5 if side == "left" else -0.4,
                    position_max=0.4 if side == "left" else 1.5,
                    velocity_max=2.8, acceleration_max=12.0, torque_max=50.0,
                ),
                JointSpec(
                    f"{side}_shoulder_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-1.7, position_max=1.7,
                    velocity_max=2.8, acceleration_max=12.0, torque_max=35.0,
                ),
                JointSpec(
                    f"{side}_elbow_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-2.2, position_max=0.0,
                    velocity_max=3.2, acceleration_max=14.0, torque_max=35.0,
                ),
                JointSpec(
                    f"{side}_elbow_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-1.5, position_max=1.5,
                    velocity_max=3.0, acceleration_max=12.0, torque_max=20.0,
                ),
                JointSpec(
                    f"{side}_wrist_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-1.0, position_max=1.0,
                    velocity_max=3.5, acceleration_max=15.0, torque_max=10.0,
                ),
                JointSpec(
                    f"{side}_wrist_roll", JointType.REVOLUTE, limb_id,
                    position_min=-1.8, position_max=1.8,
                    velocity_max=3.5, acceleration_max=15.0, torque_max=10.0,
                ),
            ],
            mass=4.0,
            length=0.55,
            max_reach=0.70,
            end_effector_mass=0.7,
        )

    # Hands (16 DOF each - Figure emphasis on dexterity)
    if include_hands:
        for side, limb_id in [("left", HumanoidLimb.LEFT_HAND), ("right", HumanoidLimb.RIGHT_HAND)]:
            hand_joints = []

            # Thumb (4 DOF - CMC abduction, CMC flexion, MCP, IP)
            for name in ["thumb_cmc_abd", "thumb_cmc_flex", "thumb_mcp", "thumb_ip"]:
                hand_joints.append(JointSpec(
                    f"{side}_{name}", JointType.REVOLUTE, limb_id,
                    position_min=0.0, position_max=1.5,
                    velocity_max=5.0, acceleration_max=25.0, torque_max=3.0,
                ))

            # Index, Middle, Ring, Pinky (3 DOF each - MCP abduction, MCP flexion, PIP)
            for finger in ["index", "middle", "ring", "pinky"]:
                for joint in ["mcp_abd", "mcp_flex", "pip"]:
                    hand_joints.append(JointSpec(
                        f"{side}_{finger}_{joint}", JointType.REVOLUTE, limb_id,
                        position_min=-0.3 if "abd" in joint else 0.0,
                        position_max=0.3 if "abd" in joint else 1.7,
                        velocity_max=5.0, acceleration_max=25.0, torque_max=2.0,
                    ))

            limbs[limb_id] = LimbSpec(
                limb=limb_id,
                joints=hand_joints,
                mass=0.45,
                length=0.17,
                end_effector_mass=0.08,
            )

    # Legs (6 DOF each)
    for side, limb_id in [("left", HumanoidLimb.LEFT_LEG), ("right", HumanoidLimb.RIGHT_LEG)]:
        limbs[limb_id] = LimbSpec(
            limb=limb_id,
            joints=[
                JointSpec(
                    f"{side}_hip_yaw", JointType.REVOLUTE, limb_id,
                    position_min=-0.4, position_max=0.4,
                    velocity_max=2.2, acceleration_max=10.0, torque_max=100.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_hip_roll", JointType.REVOLUTE, limb_id,
                    position_min=-0.4 if side == "left" else -0.25,
                    position_max=0.25 if side == "left" else 0.4,
                    velocity_max=2.2, acceleration_max=10.0, torque_max=100.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_hip_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-1.7, position_max=0.4,
                    velocity_max=2.8, acceleration_max=12.0, torque_max=160.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_knee", JointType.REVOLUTE, limb_id,
                    position_min=0.0, position_max=2.4,
                    velocity_max=3.0, acceleration_max=14.0, torque_max=160.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_ankle_pitch", JointType.REVOLUTE, limb_id,
                    position_min=-0.7, position_max=0.45,
                    velocity_max=2.2, acceleration_max=10.0, torque_max=80.0,
                    is_safety_critical=True,
                ),
                JointSpec(
                    f"{side}_ankle_roll", JointType.REVOLUTE, limb_id,
                    position_min=-0.3, position_max=0.3,
                    velocity_max=2.0, acceleration_max=8.0, torque_max=45.0,
                    is_safety_critical=True,
                ),
            ],
            mass=11.0,
            length=0.88,
            end_effector_mass=1.0,
        )

    # Operational limits based on environment
    if environment == "industrial":
        limits = OperationalLimits(
            max_walking_speed=1.4,
            max_running_speed=0.0,  # No running in industrial
            max_arm_speed=1.8,
            max_contact_force=50.0,
            max_payload=15.0,
            min_stability_margin=0.08,
            emergency_stop_time=0.35,
            max_operating_height=1.85,
        )
    elif environment == "personal_care":
        limits = OperationalLimits(
            max_walking_speed=0.9,
            max_running_speed=0.0,
            max_arm_speed=1.2,
            max_contact_force=35.0,
            max_payload=8.0,
            min_stability_margin=0.1,
            emergency_stop_time=0.3,
            max_operating_height=1.75,
        )
    else:  # research
        limits = OperationalLimits(
            max_walking_speed=2.0,
            max_running_speed=2.5,
            max_arm_speed=2.5,
            max_contact_force=80.0,
            max_payload=20.0,
            min_stability_margin=0.05,
            emergency_stop_time=0.4,
            max_operating_height=1.9,
        )

    # Calculate total DOF
    total_dof = 28
    if include_hands:
        total_dof += 32  # 16 per hand

    return HumanoidConstraints(
        name="Figure 02",
        total_dof=total_dof,
        total_mass=60.0,
        height=1.67,
        limbs=limbs,
        operational_limits=limits,
        safety_zones=[
            SafetyZone.collaborative_workspace(size=3.5),
        ],
        contact_force_limit=limits.max_contact_force,
        requires_balance_check=True,
        allows_running=(environment == "research"),
    )


def get_preset(
    name: str,
    environment: str = "industrial",
    **kwargs,
) -> HumanoidConstraints:
    """
    Get a humanoid preset by name.

    Args:
        name: Preset name ("optimus", "atlas", "figure")
        environment: "industrial", "personal_care", or "research"
        **kwargs: Additional arguments passed to preset function

    Returns:
        HumanoidConstraints for the requested robot

    Raises:
        ValueError: If preset name is not found or environment is invalid
        TypeError: If kwargs contains invalid arguments for the preset

    Example:
        # Get Tesla Optimus with hands enabled
        optimus = get_preset("optimus", environment="industrial", include_hands=True)
    """
    # Define presets
    presets = {
        "optimus": tesla_optimus,
        "tesla": tesla_optimus,
        "tesla_optimus": tesla_optimus,
        "atlas": boston_dynamics_atlas,
        "bd_atlas": boston_dynamics_atlas,
        "boston_dynamics": boston_dynamics_atlas,
        "figure": figure_02,
        "figure_02": figure_02,
        "figure02": figure_02,
    }

    # Validate environment
    valid_environments = {"industrial", "personal_care", "research"}
    if environment not in valid_environments:
        raise ValueError(
            f"environment must be one of {valid_environments}, got '{environment}'"
        )

    # Normalize preset name
    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    preset_func = presets.get(name_lower)

    if not preset_func:
        available = sorted(set(presets.keys()))
        raise ValueError(
            f"Preset '{name}' not found. Available presets: {available}"
        )

    # Validate kwargs based on preset function
    # Common valid kwargs for all presets
    valid_kwargs = {"include_hands"}

    invalid_kwargs = set(kwargs.keys()) - valid_kwargs
    if invalid_kwargs:
        raise TypeError(
            f"Unexpected keyword arguments: {invalid_kwargs}. "
            f"Valid arguments: {valid_kwargs}"
        )

    return preset_func(environment=environment, **kwargs)


def list_presets() -> list:
    """List available humanoid presets."""
    return [
        {
            "name": "Tesla Optimus Gen 2",
            "function": "tesla_optimus",
            "aliases": ["optimus", "tesla", "tesla_optimus"],
            "dof": "28 body + 22 per hand (optional)",
            "weight": "70 kg",
            "height": "1.73 m",
        },
        {
            "name": "Boston Dynamics Atlas Electric",
            "function": "boston_dynamics_atlas",
            "aliases": ["atlas", "bd_atlas", "boston_dynamics"],
            "dof": "28",
            "weight": "89 kg",
            "height": "1.5 m",
        },
        {
            "name": "Figure 02",
            "function": "figure_02",
            "aliases": ["figure", "figure_02", "figure02"],
            "dof": "28 body + 16 per hand (optional)",
            "weight": "60 kg",
            "height": "1.67 m",
        },
    ]


__all__ = [
    # Preset functions
    "tesla_optimus",
    "boston_dynamics_atlas",
    "figure_02",
    # Utility functions
    "get_preset",
    "list_presets",
]
