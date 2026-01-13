"""
Behavior types and enumerations.
"""

from enum import Enum
from typing import Dict


class BehaviorCategory(str, Enum):
    """Categories of harmful behaviors."""
    SELF_PRESERVATION = "self_preservation"
    DECEPTION = "deception"
    GOAL_MISALIGNMENT = "goal_misalignment"
    INSTRUMENTAL_CONVERGENCE = "instrumental_convergence"
    BOUNDARY_VIOLATION = "boundary_violation"
    USER_HARM = "user_harm"
    SOCIAL_ENGINEERING = "social_engineering"
    OUTPUT_INTEGRITY = "output_integrity"
    ADVERSARIAL_BEHAVIOR = "adversarial_behavior"
    SYSTEMIC_RISK = "systemic_risk"


class BehaviorSeverity(str, Enum):
    """Severity levels for detected behaviors."""
    CRITICAL = "critical"  # Must block immediately
    HIGH = "high"          # Should block
    MEDIUM = "medium"      # Flag for review
    LOW = "low"            # Log for analysis


class BehaviorType(str, Enum):
    """Specific behavior types (56 total)."""

    # Self-Preservation (SP)
    SP_SHUTDOWN_RESISTANCE = "SP01_shutdown_resistance"
    SP_RESOURCE_ACQUISITION = "SP02_resource_acquisition"
    SP_GOAL_PRESERVATION = "SP03_goal_preservation"
    SP_SELF_REPLICATION = "SP04_self_replication"
    SP_CAPABILITY_HIDING = "SP05_capability_hiding"
    SP_LOG_MANIPULATION = "SP06_log_manipulation"

    # Deception (DC)
    DC_DIRECT_LYING = "DC01_direct_lying"
    DC_OMISSION = "DC02_omission"
    DC_MISLEADING = "DC03_misleading"
    DC_SYCOPHANCY = "DC04_sycophancy"
    DC_MANIPULATION = "DC05_manipulation"
    DC_PRETENSE = "DC06_pretense"
    DC_GASLIGHTING = "DC07_gaslighting"

    # Goal Misalignment (GM)
    GM_GOAL_HIJACKING = "GM01_goal_hijacking"
    GM_REWARD_HACKING = "GM02_reward_hacking"
    GM_SPECIFICATION_GAMING = "GM03_specification_gaming"
    GM_SIDE_EFFECT_BLINDNESS = "GM04_side_effect_blindness"
    GM_SCOPE_CREEP = "GM05_scope_creep"
    GM_PRIORITY_INVERSION = "GM06_priority_inversion"

    # Instrumental Convergence (IC)
    IC_POWER_SEEKING = "IC01_power_seeking"
    IC_RESOURCE_CONTROL = "IC02_resource_control"
    IC_INFORMATION_GATHERING = "IC03_information_gathering"
    IC_INFLUENCE_MAXIMIZATION = "IC04_influence_maximization"
    IC_OPTION_PRESERVATION = "IC05_option_preservation"

    # Boundary Violations (BV)
    BV_ROLE_VIOLATION = "BV01_role_violation"
    BV_AUTHORITY_OVERREACH = "BV02_authority_overreach"
    BV_PRIVACY_VIOLATION = "BV03_privacy_violation"
    BV_ACTION_OVERREACH = "BV04_action_overreach"
    BV_RELATIONSHIP_BLUR = "BV05_relationship_blur"

    # User Harm (UH)
    UH_DEPENDENCY_CREATION = "UH01_dependency_creation"
    UH_LEARNED_HELPLESSNESS = "UH02_learned_helplessness"
    UH_DECISION_UNDERMINING = "UH03_decision_undermining"
    UH_TRUST_EXPLOITATION = "UH04_trust_exploitation"
    UH_INFORMATION_ASYMMETRY = "UH05_information_asymmetry"
    UH_AUTONOMY_REDUCTION = "UH06_autonomy_reduction"

    # Social Engineering (SE)
    SE_AUTHORITY_APPEAL = "SE01_authority_appeal"
    SE_URGENCY_CREATION = "SE02_urgency_creation"
    SE_SCARCITY_FRAMING = "SE03_scarcity_framing"
    SE_SOCIAL_PROOF = "SE04_social_proof"
    SE_RECIPROCITY_MANIPULATION = "SE05_reciprocity_manipulation"
    SE_COMMITMENT_ESCALATION = "SE06_commitment_escalation"

    # Output Integrity (OI)
    OI_HALLUCINATION = "OI01_hallucination"
    OI_OVERCONFIDENCE = "OI02_overconfidence"
    OI_UNDERCONFIDENCE = "OI03_underconfidence"
    OI_SOURCE_FABRICATION = "OI04_source_fabrication"
    OI_CREDENTIAL_CLAIM = "OI05_credential_claim"

    # Adversarial Behaviors (AB)
    AB_JAILBREAK_COMPLIANCE = "AB01_jailbreak_compliance"
    AB_INSTRUCTION_OVERRIDE = "AB02_instruction_override"
    AB_PERSONA_ADOPTION = "AB03_persona_adoption"
    AB_ROLEPLAY_EXPLOITATION = "AB04_roleplay_exploitation"
    AB_HYPOTHETICAL_ABUSE = "AB05_hypothetical_abuse"

    # Systemic Risks (SR)
    SR_CAPABILITY_OVERHANG = "SR01_capability_overhang"
    SR_CORRIGIBILITY_RESISTANCE = "SR02_corrigibility_resistance"
    SR_VALUE_DRIFT = "SR03_value_drift"
    SR_MESA_OPTIMIZATION = "SR04_mesa_optimization"
    SR_DECEPTIVE_ALIGNMENT = "SR05_deceptive_alignment"


# Mapping behavior types to categories
BEHAVIOR_CATEGORIES: Dict[BehaviorType, BehaviorCategory] = {
    # Self-Preservation
    BehaviorType.SP_SHUTDOWN_RESISTANCE: BehaviorCategory.SELF_PRESERVATION,
    BehaviorType.SP_RESOURCE_ACQUISITION: BehaviorCategory.SELF_PRESERVATION,
    BehaviorType.SP_GOAL_PRESERVATION: BehaviorCategory.SELF_PRESERVATION,
    BehaviorType.SP_SELF_REPLICATION: BehaviorCategory.SELF_PRESERVATION,
    BehaviorType.SP_CAPABILITY_HIDING: BehaviorCategory.SELF_PRESERVATION,
    BehaviorType.SP_LOG_MANIPULATION: BehaviorCategory.SELF_PRESERVATION,

    # Deception
    BehaviorType.DC_DIRECT_LYING: BehaviorCategory.DECEPTION,
    BehaviorType.DC_OMISSION: BehaviorCategory.DECEPTION,
    BehaviorType.DC_MISLEADING: BehaviorCategory.DECEPTION,
    BehaviorType.DC_SYCOPHANCY: BehaviorCategory.DECEPTION,
    BehaviorType.DC_MANIPULATION: BehaviorCategory.DECEPTION,
    BehaviorType.DC_PRETENSE: BehaviorCategory.DECEPTION,
    BehaviorType.DC_GASLIGHTING: BehaviorCategory.DECEPTION,

    # Goal Misalignment
    BehaviorType.GM_GOAL_HIJACKING: BehaviorCategory.GOAL_MISALIGNMENT,
    BehaviorType.GM_REWARD_HACKING: BehaviorCategory.GOAL_MISALIGNMENT,
    BehaviorType.GM_SPECIFICATION_GAMING: BehaviorCategory.GOAL_MISALIGNMENT,
    BehaviorType.GM_SIDE_EFFECT_BLINDNESS: BehaviorCategory.GOAL_MISALIGNMENT,
    BehaviorType.GM_SCOPE_CREEP: BehaviorCategory.GOAL_MISALIGNMENT,
    BehaviorType.GM_PRIORITY_INVERSION: BehaviorCategory.GOAL_MISALIGNMENT,

    # Instrumental Convergence
    BehaviorType.IC_POWER_SEEKING: BehaviorCategory.INSTRUMENTAL_CONVERGENCE,
    BehaviorType.IC_RESOURCE_CONTROL: BehaviorCategory.INSTRUMENTAL_CONVERGENCE,
    BehaviorType.IC_INFORMATION_GATHERING: BehaviorCategory.INSTRUMENTAL_CONVERGENCE,
    BehaviorType.IC_INFLUENCE_MAXIMIZATION: BehaviorCategory.INSTRUMENTAL_CONVERGENCE,
    BehaviorType.IC_OPTION_PRESERVATION: BehaviorCategory.INSTRUMENTAL_CONVERGENCE,

    # Boundary Violations
    BehaviorType.BV_ROLE_VIOLATION: BehaviorCategory.BOUNDARY_VIOLATION,
    BehaviorType.BV_AUTHORITY_OVERREACH: BehaviorCategory.BOUNDARY_VIOLATION,
    BehaviorType.BV_PRIVACY_VIOLATION: BehaviorCategory.BOUNDARY_VIOLATION,
    BehaviorType.BV_ACTION_OVERREACH: BehaviorCategory.BOUNDARY_VIOLATION,
    BehaviorType.BV_RELATIONSHIP_BLUR: BehaviorCategory.BOUNDARY_VIOLATION,

    # User Harm
    BehaviorType.UH_DEPENDENCY_CREATION: BehaviorCategory.USER_HARM,
    BehaviorType.UH_LEARNED_HELPLESSNESS: BehaviorCategory.USER_HARM,
    BehaviorType.UH_DECISION_UNDERMINING: BehaviorCategory.USER_HARM,
    BehaviorType.UH_TRUST_EXPLOITATION: BehaviorCategory.USER_HARM,
    BehaviorType.UH_INFORMATION_ASYMMETRY: BehaviorCategory.USER_HARM,
    BehaviorType.UH_AUTONOMY_REDUCTION: BehaviorCategory.USER_HARM,

    # Social Engineering
    BehaviorType.SE_AUTHORITY_APPEAL: BehaviorCategory.SOCIAL_ENGINEERING,
    BehaviorType.SE_URGENCY_CREATION: BehaviorCategory.SOCIAL_ENGINEERING,
    BehaviorType.SE_SCARCITY_FRAMING: BehaviorCategory.SOCIAL_ENGINEERING,
    BehaviorType.SE_SOCIAL_PROOF: BehaviorCategory.SOCIAL_ENGINEERING,
    BehaviorType.SE_RECIPROCITY_MANIPULATION: BehaviorCategory.SOCIAL_ENGINEERING,
    BehaviorType.SE_COMMITMENT_ESCALATION: BehaviorCategory.SOCIAL_ENGINEERING,

    # Output Integrity
    BehaviorType.OI_HALLUCINATION: BehaviorCategory.OUTPUT_INTEGRITY,
    BehaviorType.OI_OVERCONFIDENCE: BehaviorCategory.OUTPUT_INTEGRITY,
    BehaviorType.OI_UNDERCONFIDENCE: BehaviorCategory.OUTPUT_INTEGRITY,
    BehaviorType.OI_SOURCE_FABRICATION: BehaviorCategory.OUTPUT_INTEGRITY,
    BehaviorType.OI_CREDENTIAL_CLAIM: BehaviorCategory.OUTPUT_INTEGRITY,

    # Adversarial Behaviors
    BehaviorType.AB_JAILBREAK_COMPLIANCE: BehaviorCategory.ADVERSARIAL_BEHAVIOR,
    BehaviorType.AB_INSTRUCTION_OVERRIDE: BehaviorCategory.ADVERSARIAL_BEHAVIOR,
    BehaviorType.AB_PERSONA_ADOPTION: BehaviorCategory.ADVERSARIAL_BEHAVIOR,
    BehaviorType.AB_ROLEPLAY_EXPLOITATION: BehaviorCategory.ADVERSARIAL_BEHAVIOR,
    BehaviorType.AB_HYPOTHETICAL_ABUSE: BehaviorCategory.ADVERSARIAL_BEHAVIOR,

    # Systemic Risks
    BehaviorType.SR_CAPABILITY_OVERHANG: BehaviorCategory.SYSTEMIC_RISK,
    BehaviorType.SR_CORRIGIBILITY_RESISTANCE: BehaviorCategory.SYSTEMIC_RISK,
    BehaviorType.SR_VALUE_DRIFT: BehaviorCategory.SYSTEMIC_RISK,
    BehaviorType.SR_MESA_OPTIMIZATION: BehaviorCategory.SYSTEMIC_RISK,
    BehaviorType.SR_DECEPTIVE_ALIGNMENT: BehaviorCategory.SYSTEMIC_RISK,
}


# Default severity for each behavior type
BEHAVIOR_SEVERITY: Dict[BehaviorType, BehaviorSeverity] = {
    # Critical - must block
    BehaviorType.SP_SHUTDOWN_RESISTANCE: BehaviorSeverity.CRITICAL,
    BehaviorType.SP_SELF_REPLICATION: BehaviorSeverity.CRITICAL,
    BehaviorType.DC_DIRECT_LYING: BehaviorSeverity.CRITICAL,
    BehaviorType.DC_GASLIGHTING: BehaviorSeverity.CRITICAL,
    BehaviorType.AB_JAILBREAK_COMPLIANCE: BehaviorSeverity.CRITICAL,
    BehaviorType.AB_PERSONA_ADOPTION: BehaviorSeverity.CRITICAL,
    BehaviorType.SR_DECEPTIVE_ALIGNMENT: BehaviorSeverity.CRITICAL,

    # High - should block
    BehaviorType.SP_RESOURCE_ACQUISITION: BehaviorSeverity.HIGH,
    BehaviorType.SP_GOAL_PRESERVATION: BehaviorSeverity.HIGH,
    BehaviorType.SP_LOG_MANIPULATION: BehaviorSeverity.HIGH,
    BehaviorType.DC_MANIPULATION: BehaviorSeverity.HIGH,
    BehaviorType.DC_MISLEADING: BehaviorSeverity.HIGH,
    BehaviorType.GM_GOAL_HIJACKING: BehaviorSeverity.HIGH,
    BehaviorType.IC_POWER_SEEKING: BehaviorSeverity.HIGH,
    BehaviorType.BV_AUTHORITY_OVERREACH: BehaviorSeverity.HIGH,
    BehaviorType.BV_ACTION_OVERREACH: BehaviorSeverity.HIGH,
    BehaviorType.UH_TRUST_EXPLOITATION: BehaviorSeverity.HIGH,
    BehaviorType.AB_INSTRUCTION_OVERRIDE: BehaviorSeverity.HIGH,
    BehaviorType.AB_HYPOTHETICAL_ABUSE: BehaviorSeverity.HIGH,
    BehaviorType.SR_CORRIGIBILITY_RESISTANCE: BehaviorSeverity.HIGH,

    # Medium - flag for review
    BehaviorType.SP_CAPABILITY_HIDING: BehaviorSeverity.MEDIUM,
    BehaviorType.DC_OMISSION: BehaviorSeverity.MEDIUM,
    BehaviorType.DC_SYCOPHANCY: BehaviorSeverity.MEDIUM,
    BehaviorType.DC_PRETENSE: BehaviorSeverity.MEDIUM,
    BehaviorType.GM_REWARD_HACKING: BehaviorSeverity.MEDIUM,
    BehaviorType.GM_SPECIFICATION_GAMING: BehaviorSeverity.MEDIUM,
    BehaviorType.GM_SCOPE_CREEP: BehaviorSeverity.MEDIUM,
    BehaviorType.IC_RESOURCE_CONTROL: BehaviorSeverity.MEDIUM,
    BehaviorType.IC_INFORMATION_GATHERING: BehaviorSeverity.MEDIUM,
    BehaviorType.IC_INFLUENCE_MAXIMIZATION: BehaviorSeverity.MEDIUM,
    BehaviorType.BV_ROLE_VIOLATION: BehaviorSeverity.MEDIUM,
    BehaviorType.BV_PRIVACY_VIOLATION: BehaviorSeverity.MEDIUM,
    BehaviorType.BV_RELATIONSHIP_BLUR: BehaviorSeverity.MEDIUM,
    BehaviorType.UH_DEPENDENCY_CREATION: BehaviorSeverity.MEDIUM,
    BehaviorType.UH_LEARNED_HELPLESSNESS: BehaviorSeverity.MEDIUM,
    BehaviorType.UH_DECISION_UNDERMINING: BehaviorSeverity.MEDIUM,
    BehaviorType.UH_AUTONOMY_REDUCTION: BehaviorSeverity.MEDIUM,
    BehaviorType.SE_AUTHORITY_APPEAL: BehaviorSeverity.MEDIUM,
    BehaviorType.SE_URGENCY_CREATION: BehaviorSeverity.MEDIUM,
    BehaviorType.SE_SCARCITY_FRAMING: BehaviorSeverity.MEDIUM,
    BehaviorType.SE_RECIPROCITY_MANIPULATION: BehaviorSeverity.MEDIUM,
    BehaviorType.OI_HALLUCINATION: BehaviorSeverity.MEDIUM,
    BehaviorType.OI_SOURCE_FABRICATION: BehaviorSeverity.MEDIUM,
    BehaviorType.OI_CREDENTIAL_CLAIM: BehaviorSeverity.MEDIUM,
    BehaviorType.AB_ROLEPLAY_EXPLOITATION: BehaviorSeverity.MEDIUM,
    BehaviorType.SR_CAPABILITY_OVERHANG: BehaviorSeverity.MEDIUM,
    BehaviorType.SR_VALUE_DRIFT: BehaviorSeverity.MEDIUM,
    BehaviorType.SR_MESA_OPTIMIZATION: BehaviorSeverity.MEDIUM,

    # Low - log for analysis
    BehaviorType.GM_SIDE_EFFECT_BLINDNESS: BehaviorSeverity.LOW,
    BehaviorType.GM_PRIORITY_INVERSION: BehaviorSeverity.LOW,
    BehaviorType.IC_OPTION_PRESERVATION: BehaviorSeverity.LOW,
    BehaviorType.UH_INFORMATION_ASYMMETRY: BehaviorSeverity.LOW,
    BehaviorType.SE_SOCIAL_PROOF: BehaviorSeverity.LOW,
    BehaviorType.SE_COMMITMENT_ESCALATION: BehaviorSeverity.LOW,
    BehaviorType.OI_OVERCONFIDENCE: BehaviorSeverity.LOW,
    BehaviorType.OI_UNDERCONFIDENCE: BehaviorSeverity.LOW,
}
