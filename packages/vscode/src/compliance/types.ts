/**
 * Compliance Checker Types
 *
 * Core type definitions for the compliance checking system.
 * Supports EU AI Act, OWASP LLM Top 10, and CSA AI Controls Matrix.
 *
 * Design principles:
 * - Privacy-first: All heuristic checks run locally
 * - Optional semantic: User's own API key for enhanced analysis
 * - No telemetry: Data never leaves user's machine
 */

// ============================================================================
// COMMON TYPES
// ============================================================================

/**
 * Severity levels for compliance findings.
 * Aligned with industry standards (CVSS-like).
 */
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

/**
 * Coverage level indicating how well THSP gates address a control.
 */
export type CoverageLevel = 'strong' | 'moderate' | 'indirect' | 'not_applicable';

/**
 * Analysis method used for compliance check.
 */
export type AnalysisMethod = 'heuristic' | 'semantic';

/**
 * Supported compliance frameworks.
 */
export type ComplianceFramework = 'eu_ai_act' | 'owasp_llm' | 'csa_aicm';

/**
 * THSP gate names.
 */
export type THSPGate = 'truth' | 'harm' | 'scope' | 'purpose';

/**
 * Base interface for pattern definitions used in heuristic detection.
 */
export interface CompliancePattern {
    /** Unique identifier for the pattern */
    id: string;
    /** Regular expression for detection */
    pattern: RegExp;
    /** Human-readable description of what this detects */
    description: string;
    /** Severity if pattern matches */
    severity: Severity;
    /** Related THSP gates */
    gates: THSPGate[];
    /** Framework-specific category/article reference */
    category: string;
}

/**
 * Result of a single pattern match.
 */
export interface PatternMatch {
    /** Pattern that matched */
    patternId: string;
    /** Matched text excerpt */
    matchedText: string;
    /** Position in content (character offset) */
    position: number;
    /** Line number (1-based) */
    line: number;
    /** Column number (1-based) */
    column: number;
}

// ============================================================================
// EU AI ACT TYPES
// ============================================================================

/**
 * EU AI Act risk classification levels.
 * Reference: EU AI Act Article 6 and Annexes
 */
export type EUAIActRiskLevel =
    | 'unacceptable'  // Article 5 - Prohibited practices
    | 'high'          // Article 6 + Annex III - Requires conformity assessment
    | 'limited'       // Article 52 - Transparency requirements
    | 'minimal';      // No specific requirements

/**
 * EU AI Act system classifications.
 */
export type EUAIActSystemType =
    | 'prohibited'        // Falls under Article 5
    | 'high_risk'         // Annex III categories
    | 'limited_risk'      // Transparency obligations
    | 'minimal_risk'      // General purpose
    | 'gpai'              // General Purpose AI (Chapter V)
    | 'gpai_systemic';    // GPAI with systemic risk

/**
 * Human oversight models per Article 14.
 */
export type OversightModel =
    | 'human_in_the_loop'     // HITL - Human approval required
    | 'human_on_the_loop'     // HOTL - Human can intervene
    | 'human_in_command';     // HIC - Human has override capability

/**
 * EU AI Act Article 5 prohibited practice categories.
 */
export type ProhibitedPractice =
    | 'social_scoring'              // Art 5(1)(c)
    | 'biometric_categorization'    // Art 5(1)(g)
    | 'emotion_recognition'         // Art 5(1)(f)
    | 'predictive_policing'         // Art 5(1)(d)
    | 'subliminal_manipulation'     // Art 5(1)(a)
    | 'vulnerability_exploitation'  // Art 5(1)(b)
    | 'facial_recognition_db'       // Art 5(1)(e)
    | 'workplace_emotion';          // Art 5(1)(f)

/**
 * High-risk contexts from EU AI Act Annex III.
 */
export type HighRiskContext =
    | 'biometrics'
    | 'critical_infrastructure'
    | 'education'
    | 'employment'
    | 'essential_services'
    | 'law_enforcement'
    | 'migration'
    | 'justice'
    | 'democratic_processes'
    | 'safety_components';

/**
 * Finding for a specific EU AI Act article violation.
 */
export interface EUAIActArticleFinding {
    /** Article number (e.g., "5", "9", "14") */
    article: string;
    /** Sub-article if applicable (e.g., "1(c)") */
    subArticle?: string;
    /** Whether this article's requirements are met */
    compliant: boolean;
    /** Severity of non-compliance */
    severity: Severity;
    /** Specific issues found */
    issues: string[];
    /** Recommended actions */
    recommendations: string[];
    /** Pattern matches that triggered this finding */
    matches: PatternMatch[];
}

/**
 * Complete EU AI Act compliance check result.
 */
export interface EUAIActComplianceResult {
    /** Overall compliance status */
    compliant: boolean;
    /** Determined risk level */
    riskLevel: EUAIActRiskLevel;
    /** System type classification */
    systemType: EUAIActSystemType;
    /** Required oversight model (for high-risk) */
    oversightRequired?: OversightModel;
    /** Detected prohibited practices */
    prohibitedPractices: ProhibitedPractice[];
    /** Detected high-risk contexts */
    highRiskContexts: HighRiskContext[];
    /** Findings by article */
    articleFindings: EUAIActArticleFinding[];
    /** General recommendations */
    recommendations: string[];
    /** Analysis metadata */
    metadata: ComplianceMetadata;
}

// ============================================================================
// OWASP LLM TOP 10 TYPES
// ============================================================================

/**
 * OWASP LLM Top 10 (2025) vulnerability identifiers.
 */
export type OWASPVulnerability =
    | 'LLM01'   // Prompt Injection
    | 'LLM02'   // Sensitive Information Disclosure
    | 'LLM03'   // Supply Chain Vulnerabilities
    | 'LLM04'   // Data and Model Poisoning
    | 'LLM05'   // Improper Output Handling
    | 'LLM06'   // Excessive Agency
    | 'LLM07'   // System Prompt Leakage
    | 'LLM08'   // Vector and Embedding Weaknesses
    | 'LLM09'   // Misinformation
    | 'LLM10';  // Unbounded Consumption

/**
 * Validation stage in LLM pipeline.
 */
export type ValidationStage = 'input' | 'output' | 'pipeline';

/**
 * Finding for a specific OWASP vulnerability.
 */
export interface OWASPVulnerabilityFinding {
    /** Vulnerability identifier */
    vulnerability: OWASPVulnerability;
    /** Vulnerability name */
    name: string;
    /** Whether vulnerability was detected */
    detected: boolean;
    /** THSP coverage level for this vulnerability */
    coverageLevel: CoverageLevel;
    /** THSP gates that address this vulnerability */
    gatesChecked: THSPGate[];
    /** Gates that passed */
    gatesPassed: THSPGate[];
    /** Gates that failed */
    gatesFailed: THSPGate[];
    /** Specific patterns matched */
    patternsMatched: PatternMatch[];
    /** Severity if detected */
    severity?: Severity;
    /** Recommended mitigation */
    recommendation?: string;
}

/**
 * Complete OWASP LLM compliance check result.
 */
export interface OWASPComplianceResult {
    /** Overall security status (no vulnerabilities detected) */
    secure: boolean;
    /** Number of vulnerabilities checked */
    vulnerabilitiesChecked: number;
    /** Number of vulnerabilities detected */
    vulnerabilitiesDetected: number;
    /** Detection rate (detected/checked) */
    detectionRate: number;
    /** Detailed findings per vulnerability */
    findings: OWASPVulnerabilityFinding[];
    /** Input validation result (if applicable) */
    inputValidation?: {
        checked: boolean;
        secure: boolean;
        vulnerabilitiesDetected: number;
    };
    /** Output validation result (if applicable) */
    outputValidation?: {
        checked: boolean;
        secure: boolean;
        vulnerabilitiesDetected: number;
    };
    /** Security recommendations */
    recommendations: string[];
    /** Analysis metadata */
    metadata: ComplianceMetadata;
}

// ============================================================================
// CSA AI CONTROLS MATRIX TYPES
// ============================================================================

/**
 * CSA AI Controls Matrix security domains.
 * Reference: CSA AICM v1.0 (July 2025)
 */
export type AICMDomain =
    | 'audit_assurance'
    | 'application_interface_security'
    | 'business_continuity'
    | 'change_control'
    | 'cryptography'
    | 'datacenter_security'
    | 'data_security_privacy'
    | 'governance_risk_compliance'
    | 'human_resources'
    | 'identity_access_management'
    | 'interoperability_portability'
    | 'infrastructure_security'
    | 'logging_monitoring'
    | 'model_security'
    | 'security_incident_management'
    | 'supply_chain_transparency_accountability'
    | 'threat_vulnerability_management'
    | 'endpoint_management';

/**
 * CSA AICM threat categories.
 */
export type AICMThreatCategory =
    | 'model_manipulation'
    | 'data_poisoning'
    | 'sensitive_data_disclosure'
    | 'model_theft'
    | 'service_failures'
    | 'insecure_supply_chains'
    | 'insecure_apps_plugins'
    | 'denial_of_service'
    | 'loss_of_governance';

/**
 * Finding for a specific AICM domain.
 */
export interface AICMDomainFinding {
    /** Domain assessed */
    domain: AICMDomain;
    /** Domain display name */
    displayName: string;
    /** Compliance status */
    compliant: boolean;
    /** THSP coverage level */
    coverageLevel: CoverageLevel;
    /** THSP gates checked */
    gatesChecked: THSPGate[];
    /** Gates that passed */
    gatesPassed: THSPGate[];
    /** Gates that failed */
    gatesFailed: THSPGate[];
    /** Severity if non-compliant */
    severity?: Severity;
    /** Domain-specific recommendation */
    recommendation?: string;
}

/**
 * Threat assessment result.
 */
export interface AICMThreatAssessment {
    /** Threats mitigated by THSP */
    threatsMitigated: AICMThreatCategory[];
    /** Threats detected in content */
    threatsDetected: string[];
    /** Overall threat score (0.0 low - 1.0 high) */
    overallThreatScore: number;
}

/**
 * Complete CSA AICM compliance check result.
 */
export interface AICMComplianceResult {
    /** Overall compliance status */
    compliant: boolean;
    /** Number of domains assessed */
    domainsAssessed: number;
    /** Number of domains compliant */
    domainsCompliant: number;
    /** Compliance rate (compliant/assessed) */
    complianceRate: number;
    /** Detailed findings per domain */
    domainFindings: AICMDomainFinding[];
    /** Threat assessment */
    threatAssessment: AICMThreatAssessment;
    /** Compliance recommendations */
    recommendations: string[];
    /** Analysis metadata */
    metadata: ComplianceMetadata;
}

// ============================================================================
// UNIFIED COMPLIANCE RESULT
// ============================================================================

/**
 * Metadata included with all compliance results.
 */
export interface ComplianceMetadata {
    /** Timestamp of analysis */
    timestamp: string;
    /** Framework checked */
    framework: ComplianceFramework;
    /** Framework version/reference */
    frameworkVersion: string;
    /** Analysis method used */
    analysisMethod: AnalysisMethod;
    /** Content size analyzed (characters) */
    contentSize: number;
    /** Processing time (milliseconds) */
    processingTimeMs: number;
    /** THSP gates evaluated */
    gatesEvaluated?: Record<THSPGate, boolean>;
    /** Gates that failed */
    failedGates?: THSPGate[];
}

/**
 * Configuration for compliance checker.
 */
export interface ComplianceCheckerConfig {
    /** API key for semantic analysis (user's own key) */
    apiKey?: string;
    /** LLM provider */
    provider?: 'openai' | 'anthropic';
    /** Model to use */
    model?: string;
    /** Maximum content size (bytes) */
    maxContentSize?: number;
    /** Fail closed on errors (treat as non-compliant) */
    failClosed?: boolean;
    /** Request timeout (ms) */
    timeoutMs?: number;
}

/**
 * Unified result for multi-framework compliance check.
 */
export interface UnifiedComplianceResult {
    /** Overall compliance across all frameworks */
    compliant: boolean;
    /** Summary by framework */
    summary: {
        euAiAct?: { compliant: boolean; riskLevel: EUAIActRiskLevel };
        owaspLlm?: { secure: boolean; vulnerabilitiesDetected: number };
        csaAicm?: { compliant: boolean; complianceRate: number };
    };
    /** Individual framework results */
    euAiAct?: EUAIActComplianceResult;
    owaspLlm?: OWASPComplianceResult;
    csaAicm?: AICMComplianceResult;
    /** Combined recommendations (deduplicated) */
    recommendations: string[];
    /** Analysis timestamp */
    timestamp: string;
    /** Frameworks checked */
    frameworksChecked: ComplianceFramework[];
}

// ============================================================================
// HELPER TYPE GUARDS
// ============================================================================

/**
 * Type guard for severity values.
 */
export function isSeverity(value: unknown): value is Severity {
    return typeof value === 'string' &&
           ['critical', 'high', 'medium', 'low', 'info'].includes(value);
}

/**
 * Type guard for coverage level values.
 */
export function isCoverageLevel(value: unknown): value is CoverageLevel {
    return typeof value === 'string' &&
           ['strong', 'moderate', 'indirect', 'not_applicable'].includes(value);
}

/**
 * Type guard for compliance framework values.
 */
export function isComplianceFramework(value: unknown): value is ComplianceFramework {
    return typeof value === 'string' &&
           ['eu_ai_act', 'owasp_llm', 'csa_aicm'].includes(value);
}

/**
 * Type guard for THSP gate values.
 */
export function isTHSPGate(value: unknown): value is THSPGate {
    return typeof value === 'string' &&
           ['truth', 'harm', 'scope', 'purpose'].includes(value);
}

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * Human-readable names for OWASP vulnerabilities.
 */
export const OWASP_VULNERABILITY_NAMES: Record<OWASPVulnerability, string> = {
    LLM01: 'Prompt Injection',
    LLM02: 'Sensitive Information Disclosure',
    LLM03: 'Supply Chain Vulnerabilities',
    LLM04: 'Data and Model Poisoning',
    LLM05: 'Improper Output Handling',
    LLM06: 'Excessive Agency',
    LLM07: 'System Prompt Leakage',
    LLM08: 'Vector and Embedding Weaknesses',
    LLM09: 'Misinformation',
    LLM10: 'Unbounded Consumption',
};

/**
 * Human-readable names for CSA AICM domains.
 */
export const AICM_DOMAIN_NAMES: Record<AICMDomain, string> = {
    audit_assurance: 'Audit & Assurance',
    application_interface_security: 'Application & Interface Security',
    business_continuity: 'Business Continuity',
    change_control: 'Change Control',
    cryptography: 'Cryptography',
    datacenter_security: 'Datacenter Security',
    data_security_privacy: 'Data Security & Privacy',
    governance_risk_compliance: 'Governance, Risk & Compliance',
    human_resources: 'Human Resources',
    identity_access_management: 'Identity & Access Management',
    interoperability_portability: 'Interoperability & Portability',
    infrastructure_security: 'Infrastructure Security',
    logging_monitoring: 'Logging & Monitoring',
    model_security: 'Model Security',
    security_incident_management: 'Security Incident Management',
    supply_chain_transparency_accountability: 'Supply Chain, Transparency & Accountability',
    threat_vulnerability_management: 'Threat & Vulnerability Management',
    endpoint_management: 'Endpoint Management',
};

/**
 * Human-readable names for EU AI Act risk levels.
 */
export const EU_AI_ACT_RISK_LEVEL_NAMES: Record<EUAIActRiskLevel, string> = {
    unacceptable: 'Unacceptable Risk (Prohibited)',
    high: 'High Risk',
    limited: 'Limited Risk',
    minimal: 'Minimal Risk',
};
