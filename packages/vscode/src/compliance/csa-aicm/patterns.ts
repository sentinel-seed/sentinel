/**
 * CSA AI Controls Matrix (AICM) Compliance Patterns
 *
 * Pattern definitions and mappings for CSA AICM compliance.
 * Based on CSA AI Controls Matrix v1.0 (July 2025).
 *
 * The CSA AICM provides:
 * - 18 security domains
 * - 243 control objectives
 * - 5 analytical pillars
 * - 9 threat categories
 *
 * THSP gates provide behavioral-level controls that support several domains:
 * - Truth Gate: Model Security, Data Security, Governance
 * - Harm Gate: Threat Management, Application Security, Data Security
 * - Scope Gate: Application Security, IAM, Threat Management
 * - Purpose Gate: Supply Chain, Transparency, Accountability
 *
 * Reference: https://cloudsecurityalliance.org/artifacts/ai-controls-matrix
 */

import {
    CompliancePattern,
    AICMDomain,
    AICMThreatCategory,
    THSPGate,
    CoverageLevel,
    AICM_DOMAIN_NAMES,
} from '../types';

// ============================================================================
// DOMAIN TO THSP GATE MAPPING
// ============================================================================

/**
 * Maps CSA AICM domains to THSP gates and coverage levels.
 *
 * Coverage levels:
 * - Strong: THSP directly addresses core domain controls
 * - Moderate: THSP provides significant support
 * - Indirect: THSP contributes to but doesn't directly address
 * - Not Applicable: Infrastructure-level, outside THSP scope
 */
export const DOMAIN_GATE_MAPPING: Record<AICMDomain, {
    gates: THSPGate[];
    coverage: CoverageLevel;
    description: string;
}> = {
    // Strong Coverage (directly addressed by THSP)
    model_security: {
        gates: ['truth', 'harm', 'scope', 'purpose'],
        coverage: 'strong',
        description: 'Model integrity, adversarial robustness, output validation',
    },
    governance_risk_compliance: {
        gates: ['truth', 'harm', 'scope', 'purpose'],
        coverage: 'strong',
        description: 'Risk assessment, policy enforcement, ethical guidelines',
    },
    supply_chain_transparency_accountability: {
        gates: ['purpose', 'truth'],
        coverage: 'strong',
        description: 'Accountability, transparency, decision justification',
    },

    // Moderate Coverage (significant THSP support)
    data_security_privacy: {
        gates: ['truth', 'harm'],
        coverage: 'moderate',
        description: 'PII protection, privacy by design',
    },
    threat_vulnerability_management: {
        gates: ['scope', 'harm'],
        coverage: 'moderate',
        description: 'Threat detection, attack surface reduction',
    },
    application_interface_security: {
        gates: ['scope', 'harm'],
        coverage: 'moderate',
        description: 'Input validation, output sanitization',
    },

    // Indirect Coverage (contributes to but not primary)
    audit_assurance: {
        gates: ['purpose'],
        coverage: 'indirect',
        description: 'Validation data for audit trails',
    },
    identity_access_management: {
        gates: ['scope'],
        coverage: 'indirect',
        description: 'Privilege escalation detection',
    },
    logging_monitoring: {
        gates: [],
        coverage: 'indirect',
        description: 'Validation results can be logged',
    },
    security_incident_management: {
        gates: ['harm'],
        coverage: 'indirect',
        description: 'Incident data from blocked actions',
    },

    // Not Applicable (infrastructure-level)
    business_continuity: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Operational resilience - infrastructure level',
    },
    change_control: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Configuration management - infrastructure level',
    },
    cryptography: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Encryption - infrastructure level',
    },
    datacenter_security: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Physical security - infrastructure level',
    },
    human_resources: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Personnel security - infrastructure level',
    },
    interoperability_portability: {
        gates: [],
        coverage: 'not_applicable',
        description: 'System integration - infrastructure level',
    },
    infrastructure_security: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Network/compute security - infrastructure level',
    },
    endpoint_management: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Device management - infrastructure level',
    },
};

// ============================================================================
// THREAT CATEGORY TO THSP GATE MAPPING
// ============================================================================

/**
 * Maps CSA AICM threat categories to THSP gates.
 */
export const THREAT_GATE_MAPPING: Record<AICMThreatCategory, {
    gates: THSPGate[];
    coverage: CoverageLevel;
    description: string;
}> = {
    model_manipulation: {
        gates: ['scope'],
        coverage: 'strong',
        description: 'Prompt injection, jailbreak detection',
    },
    sensitive_data_disclosure: {
        gates: ['harm'],
        coverage: 'strong',
        description: 'PII and sensitive data blocking',
    },
    loss_of_governance: {
        gates: ['purpose'],
        coverage: 'strong',
        description: 'Accountability and decision justification',
    },
    insecure_apps_plugins: {
        gates: ['scope'],
        coverage: 'moderate',
        description: 'Boundary enforcement for extensions',
    },
    data_poisoning: {
        gates: ['truth'],
        coverage: 'indirect',
        description: 'Output validation may catch poisoned data effects',
    },
    insecure_supply_chains: {
        gates: ['purpose'],
        coverage: 'indirect',
        description: 'Sentinel itself is a trusted component',
    },
    model_theft: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Infrastructure-level protection',
    },
    service_failures: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Availability - infrastructure level',
    },
    denial_of_service: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Rate limiting - infrastructure level',
    },
};

// ============================================================================
// DOMAIN-SPECIFIC PATTERNS
// ============================================================================

/**
 * Patterns for Model Security domain.
 */
export const MODEL_SECURITY_PATTERNS: CompliancePattern[] = [
    {
        id: 'csa_model_adversarial',
        pattern: /\b(adversarial\s*(input|example|attack)|model\s*(evasion|manipulation)|perturbation\s*attack)\b/gi,
        description: 'Adversarial attack indicator',
        severity: 'high',
        gates: ['scope', 'harm'],
        category: 'model_security',
    },
    {
        id: 'csa_model_extraction',
        pattern: /\b(model\s*(extraction|stealing|theft)|extract\s*(model|weights|parameters))\b/gi,
        description: 'Model extraction attempt',
        severity: 'high',
        gates: ['scope'],
        category: 'model_security',
    },
    {
        id: 'csa_model_inversion',
        pattern: /\b(model\s*inversion|membership\s*inference|training\s*data\s*(extraction|leakage))\b/gi,
        description: 'Model inversion/inference attack',
        severity: 'high',
        gates: ['harm', 'truth'],
        category: 'model_security',
    },
];

/**
 * Patterns for Data Security domain.
 */
export const DATA_SECURITY_PATTERNS: CompliancePattern[] = [
    {
        id: 'csa_data_pii',
        pattern: /\b(personal\s*(data|information)|PII|personally\s*identifiable|sensitive\s*data)\b/gi,
        description: 'Personal/sensitive data handling',
        severity: 'medium',
        gates: ['harm', 'truth'],
        category: 'data_security_privacy',
    },
    {
        id: 'csa_data_exfil',
        pattern: /\b(data\s*(exfiltration|leakage|breach)|leak\s*(data|information)|unauthorized\s*disclosure)\b/gi,
        description: 'Data exfiltration risk',
        severity: 'high',
        gates: ['harm'],
        category: 'data_security_privacy',
    },
    {
        id: 'csa_data_training',
        pattern: /\b(training\s*data\s*(exposure|leak)|memorized\s*(data|content)|data\s*memorization)\b/gi,
        description: 'Training data exposure',
        severity: 'high',
        gates: ['truth', 'harm'],
        category: 'data_security_privacy',
    },
];

/**
 * Patterns for Governance domain.
 */
export const GOVERNANCE_PATTERNS: CompliancePattern[] = [
    {
        id: 'csa_gov_accountability',
        pattern: /\b(no\s*(accountability|oversight|audit)|unauditable|untraceable\s*decision)\b/gi,
        description: 'Lack of accountability',
        severity: 'high',
        gates: ['purpose'],
        category: 'governance_risk_compliance',
    },
    {
        id: 'csa_gov_bias',
        pattern: /\b(algorithmic\s*bias|discriminat(ory|ion)|unfair\s*(treatment|decision)|biased\s*(output|result))\b/gi,
        description: 'Bias or discrimination concern',
        severity: 'high',
        gates: ['truth', 'harm'],
        category: 'governance_risk_compliance',
    },
    {
        id: 'csa_gov_ethics',
        pattern: /\b(unethical\s*(use|application)|ethics?\s*violation|against\s*ethical\s*guidelines)\b/gi,
        description: 'Ethical concern',
        severity: 'high',
        gates: ['purpose', 'harm'],
        category: 'governance_risk_compliance',
    },
];

/**
 * Patterns for Application Security domain.
 */
export const APPLICATION_SECURITY_PATTERNS: CompliancePattern[] = [
    {
        id: 'csa_app_injection',
        pattern: /\b(inject(ion)?|malicious\s*input|untrusted\s*(input|data)|input\s*validation)\b/gi,
        description: 'Injection vulnerability indicator',
        severity: 'high',
        gates: ['scope', 'harm'],
        category: 'application_interface_security',
    },
    {
        id: 'csa_app_output',
        pattern: /\b(unvalidated\s*output|output\s*encoding|unsanitized\s*(output|response))\b/gi,
        description: 'Output handling concern',
        severity: 'medium',
        gates: ['harm'],
        category: 'application_interface_security',
    },
];

/**
 * Patterns for Supply Chain domain.
 */
export const SUPPLY_CHAIN_PATTERNS: CompliancePattern[] = [
    {
        id: 'csa_supply_third_party',
        pattern: /\b(third[\s-]*party\s*(model|api|service)|untrusted\s*(source|provider)|external\s*dependency)\b/gi,
        description: 'Third-party dependency concern',
        severity: 'medium',
        gates: ['purpose'],
        category: 'supply_chain_transparency_accountability',
    },
    {
        id: 'csa_supply_provenance',
        pattern: /\b(model\s*provenance|data\s*lineage|origin\s*unknown|unverified\s*source)\b/gi,
        description: 'Provenance/lineage concern',
        severity: 'medium',
        gates: ['truth', 'purpose'],
        category: 'supply_chain_transparency_accountability',
    },
];

/**
 * Patterns for Threat Management domain.
 */
export const THREAT_PATTERNS: CompliancePattern[] = [
    {
        id: 'csa_threat_attack',
        pattern: /\b(attack\s*(vector|surface)|threat\s*(actor|model)|exploit(ation)?|vulnerability)\b/gi,
        description: 'Security threat indicator',
        severity: 'high',
        gates: ['harm', 'scope'],
        category: 'threat_vulnerability_management',
    },
    {
        id: 'csa_threat_malicious',
        pattern: /\b(malicious\s*(intent|actor|use)|bad\s*actor|threat\s*agent)\b/gi,
        description: 'Malicious intent indicator',
        severity: 'high',
        gates: ['harm', 'purpose'],
        category: 'threat_vulnerability_management',
    },
];

// ============================================================================
// COMBINED PATTERNS
// ============================================================================

/**
 * All CSA AICM patterns combined.
 */
export const ALL_CSA_AICM_PATTERNS: CompliancePattern[] = [
    ...MODEL_SECURITY_PATTERNS,
    ...DATA_SECURITY_PATTERNS,
    ...GOVERNANCE_PATTERNS,
    ...APPLICATION_SECURITY_PATTERNS,
    ...SUPPLY_CHAIN_PATTERNS,
    ...THREAT_PATTERNS,
];

/**
 * Gets patterns for a specific domain.
 */
export function getPatternsForDomain(domain: AICMDomain): CompliancePattern[] {
    return ALL_CSA_AICM_PATTERNS.filter(p => p.category === domain);
}

/**
 * Gets domains with THSP support (non-infrastructure).
 */
export function getSupportedDomains(): AICMDomain[] {
    return Object.entries(DOMAIN_GATE_MAPPING)
        .filter(([_, mapping]) => mapping.coverage !== 'not_applicable')
        .map(([domain]) => domain as AICMDomain);
}

/**
 * Gets domain display name.
 */
export function getDomainDisplayName(domain: AICMDomain): string {
    return AICM_DOMAIN_NAMES[domain];
}

// ============================================================================
// DOMAIN-SPECIFIC RECOMMENDATIONS
// ============================================================================

/**
 * Recommendations for each domain.
 */
export const DOMAIN_RECOMMENDATIONS: Record<AICMDomain, string> = {
    model_security: 'Implement additional model security controls: input sanitization, output filtering, adversarial testing',
    governance_risk_compliance: 'Review governance policies and risk management procedures',
    supply_chain_transparency_accountability: 'Document decision accountability and ensure transparency requirements',
    data_security_privacy: 'Review data handling practices and privacy controls',
    threat_vulnerability_management: 'Conduct threat assessment and implement additional mitigations',
    application_interface_security: 'Strengthen input validation and output sanitization',
    audit_assurance: 'Ensure validation results are logged for audit trails',
    identity_access_management: 'Review access controls and boundary enforcement',
    logging_monitoring: 'Implement comprehensive logging of THSP validation events',
    security_incident_management: 'Establish incident response procedures for blocked actions',
    business_continuity: 'Domain not applicable to THSP - use infrastructure controls',
    change_control: 'Domain not applicable to THSP - use infrastructure controls',
    cryptography: 'Domain not applicable to THSP - use infrastructure controls',
    datacenter_security: 'Domain not applicable to THSP - use infrastructure controls',
    human_resources: 'Domain not applicable to THSP - use infrastructure controls',
    interoperability_portability: 'Domain not applicable to THSP - use infrastructure controls',
    infrastructure_security: 'Domain not applicable to THSP - use infrastructure controls',
    endpoint_management: 'Domain not applicable to THSP - use infrastructure controls',
};
