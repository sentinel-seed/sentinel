/**
 * Compliance Module
 *
 * Unified compliance checking for AI systems.
 *
 * Supports:
 * - EU AI Act (2024)
 * - OWASP LLM Top 10 (2025)
 * - CSA AI Controls Matrix (2025)
 *
 * Privacy-first design:
 * - All heuristic checks run 100% locally
 * - Semantic analysis uses user's own API key
 * - No data sent to Sentinel servers
 * - No telemetry or tracking
 *
 * @example
 * ```typescript
 * import { ComplianceChecker } from './compliance';
 *
 * const checker = new ComplianceChecker();
 *
 * // Check all frameworks
 * const result = checker.checkAll(content);
 * if (!result.compliant) {
 *   console.log('Issues found:', result.recommendations);
 * }
 *
 * // Check specific framework
 * const euResult = checker.checkEUAIAct(content);
 * if (euResult.riskLevel === 'unacceptable') {
 *   console.log('Prohibited practice detected!');
 * }
 * ```
 */

// ============================================================================
// TYPES
// ============================================================================

export * from './types';

// ============================================================================
// MAIN CHECKER
// ============================================================================

export {
    ComplianceChecker,
    createComplianceChecker,
    checkCompliance,
    checkEUAIActCompliance,
    checkOWASPCompliance,
    checkCSACompliance,
} from './complianceChecker';

// ============================================================================
// EU AI ACT
// ============================================================================

export {
    EUAIActChecker,
    checkEUAIActCompliance as checkEUAIAct,
} from './eu-ai-act';

export {
    ALL_EU_AI_ACT_PATTERNS,
    PROHIBITED_PRACTICE_PATTERNS,
    HIGH_RISK_CONTEXT_PATTERNS,
} from './eu-ai-act';

// ============================================================================
// OWASP LLM TOP 10
// ============================================================================

export {
    OWASPLLMChecker,
    checkOWASPLLMCompliance,
    hasPromptInjection,
    hasSensitiveInfo,
} from './owasp-llm';

export {
    ALL_OWASP_LLM_PATTERNS,
    INPUT_VALIDATION_PATTERNS,
    OUTPUT_VALIDATION_PATTERNS,
    VULNERABILITY_GATE_MAPPING,
} from './owasp-llm';

// ============================================================================
// CSA AI CONTROLS MATRIX
// ============================================================================

export {
    CSAAICMChecker,
    checkCSAAICMCompliance,
    getThspSupportedDomains,
} from './csa-aicm';

export {
    ALL_CSA_AICM_PATTERNS,
    DOMAIN_GATE_MAPPING,
    THREAT_GATE_MAPPING,
} from './csa-aicm';

// ============================================================================
// SEMANTIC ANALYZER
// ============================================================================

export {
    SemanticComplianceAnalyzer,
    createSemanticAnalyzer,
} from './semanticAnalyzer';

export type { SemanticAnalyzerConfig } from './semanticAnalyzer';

// ============================================================================
// UTILITIES
// ============================================================================

export {
    validateContent,
    runPatterns,
    getLineColumn,
    MAX_CONTENT_SIZE,
} from './utils';
