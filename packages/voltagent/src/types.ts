/**
 * @sentinelseed/voltagent - Type Definitions
 *
 * Core type definitions for Sentinel VoltAgent integration.
 * These types provide the foundation for THSP validation, OWASP protection,
 * and PII detection in VoltAgent applications.
 */

// =============================================================================
// THSP Gate Types
// =============================================================================

/**
 * Risk levels for safety assessment.
 * Used to categorize the severity of detected issues.
 */
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

/**
 * Status of a THSP gate after validation.
 * - 'pass': Gate validation succeeded
 * - 'fail': Gate validation failed (issue detected)
 * - 'unknown': Could not determine gate status
 */
export type GateStatus = 'pass' | 'fail' | 'unknown';

/**
 * Action to take after guardrail evaluation.
 * Matches VoltAgent's GuardrailAction type.
 */
export type GuardrailAction = 'allow' | 'block' | 'modify';

/**
 * THSP (Truth, Harm, Scope, Purpose) gate statuses.
 * Each gate represents a dimension of AI safety validation.
 */
export interface THSPGates {
  /** Truth gate: Validates factual accuracy and authenticity */
  truth: GateStatus;
  /** Harm gate: Assesses potential for causing harm */
  harm: GateStatus;
  /** Scope gate: Checks appropriate operational boundaries */
  scope: GateStatus;
  /** Purpose gate: Validates legitimate beneficial intent */
  purpose: GateStatus;
}

// =============================================================================
// Validation Results
// =============================================================================

/**
 * Result of THSP validation.
 * Contains detailed information about the safety assessment.
 */
export interface THSPValidationResult {
  /** Whether the content passed all safety checks */
  safe: boolean;
  /** Individual gate statuses */
  gates: THSPGates;
  /** List of concerns detected during validation */
  concerns: string[];
  /** Overall risk level assessment */
  riskLevel: RiskLevel;
  /** Human-readable recommendation */
  recommendation: string;
  /** Timestamp of validation */
  timestamp: number;
}

/**
 * Result of OWASP pattern validation.
 * Focuses on security vulnerabilities detection.
 */
export interface OWASPValidationResult {
  /** Whether any OWASP violations were detected */
  safe: boolean;
  /** List of detected OWASP violation types */
  violations: OWASPViolationType[];
  /** Detailed findings for each violation */
  findings: OWASPFinding[];
  /** Risk level based on OWASP severity */
  riskLevel: RiskLevel;
}

/**
 * Types of OWASP violations that can be detected.
 * Based on OWASP Agentic Top 10 and Web Top 10.
 */
export type OWASPViolationType =
  | 'SQL_INJECTION'
  | 'XSS'
  | 'COMMAND_INJECTION'
  | 'PATH_TRAVERSAL'
  | 'SSRF'
  | 'PROMPT_INJECTION'
  | 'INSECURE_OUTPUT'
  | 'SENSITIVE_DATA_EXPOSURE'
  | 'EXCESSIVE_PERMISSIONS'
  | 'DENIAL_OF_SERVICE';

/**
 * Detailed finding for an OWASP violation.
 */
export interface OWASPFinding {
  /** Type of violation */
  type: OWASPViolationType;
  /** Description of the finding */
  description: string;
  /** Matched pattern or evidence */
  evidence: string;
  /** Severity level */
  severity: RiskLevel;
  /** Recommended remediation */
  remediation?: string;
}

/**
 * Result of PII detection.
 */
export interface PIIDetectionResult {
  /** Whether PII was detected */
  detected: boolean;
  /** List of PII types found */
  types: PIIType[];
  /** Detailed matches */
  matches: PIIMatch[];
  /** Total count of PII instances */
  count: number;
}

/**
 * Types of PII that can be detected.
 */
export type PIIType =
  | 'EMAIL'
  | 'PHONE'
  | 'SSN'
  | 'CREDIT_CARD'
  | 'IP_ADDRESS'
  | 'ADDRESS'
  | 'NAME'
  | 'DATE_OF_BIRTH'
  | 'PASSPORT'
  | 'DRIVER_LICENSE'
  | 'API_KEY'
  | 'AWS_KEY'
  | 'PRIVATE_KEY'
  | 'JWT_TOKEN'
  | 'CUSTOM';

/**
 * Individual PII match details.
 */
export interface PIIMatch {
  /** Type of PII */
  type: PIIType;
  /** The matched value (may be partially redacted) */
  value: string;
  /** Start position in original text */
  start: number;
  /** End position in original text */
  end: number;
  /** Confidence score (0-1) */
  confidence: number;
}

// =============================================================================
// Pattern Definitions
// =============================================================================

/**
 * Definition of a custom validation pattern.
 * Can be used to extend built-in validation rules.
 */
export interface PatternDefinition {
  /** Regular expression pattern to match */
  pattern: RegExp;
  /** Human-readable name of the pattern */
  name: string;
  /** Which THSP gate this pattern affects */
  gate: keyof THSPGates;
  /** Severity if pattern matches */
  severity?: RiskLevel;
  /** Description of what this pattern detects */
  description?: string;
}

/**
 * OWASP-specific pattern definition.
 */
export interface OWASPPatternDefinition {
  /** Regular expression pattern */
  pattern: RegExp;
  /** Type of OWASP violation */
  type: OWASPViolationType;
  /** Severity level */
  severity: RiskLevel;
  /** Description */
  description: string;
}

/**
 * PII-specific pattern definition.
 */
export interface PIIPatternDefinition {
  /** Regular expression pattern */
  pattern: RegExp;
  /** Type of PII */
  type: PIIType;
  /** Redaction format (e.g., "[EMAIL]", "***") */
  redactionFormat: string;
  /** Whether to allow partial matching */
  partialMatch?: boolean;
}

// =============================================================================
// Configuration Types
// =============================================================================

/**
 * Configuration for Sentinel guardrails.
 * Controls behavior of input and output validation.
 */
export interface SentinelGuardrailConfig {
  // Behavior settings
  /** Whether to block content that fails validation (default: true) */
  blockUnsafe?: boolean;
  /** Whether to log validation checks (default: false) */
  logChecks?: boolean;
  /** Logger function for custom logging */
  logger?: (message: string, data?: Record<string, unknown>) => void;

  // Validation module toggles
  /** Enable THSP protocol validation (default: true) */
  enableTHSP?: boolean;
  /** Enable OWASP security patterns (default: true) */
  enableOWASP?: boolean;
  /** Enable PII detection (default: false for input, true for output) */
  enablePII?: boolean;

  // THSP configuration
  /** Custom patterns to add to THSP validation */
  customPatterns?: PatternDefinition[];
  /** Actions to skip validation for */
  skipActions?: string[];
  /** Minimum risk level to trigger blocking */
  minBlockLevel?: RiskLevel;

  // OWASP configuration
  /** Which OWASP violations to check for */
  owaspChecks?: OWASPViolationType[];
  /** Custom OWASP patterns */
  customOWASPPatterns?: OWASPPatternDefinition[];

  // PII configuration
  /** Which PII types to detect */
  piiTypes?: PIIType[];
  /** Custom PII patterns */
  customPIIPatterns?: PIIPatternDefinition[];
  /** Whether to redact PII in output (for modify action) */
  redactPII?: boolean;
  /** Custom redaction format */
  redactionFormat?: string | ((type: PIIType, value: string) => string);

  // Performance settings
  /** Maximum content length to validate (default: 100000) */
  maxContentLength?: number;
  /** Timeout for async validations in ms (default: 5000) */
  timeout?: number;
}

/**
 * Configuration for the bundle function.
 * Provides preset configurations for common use cases.
 */
export interface SentinelBundleConfig {
  /** Preset security level */
  level?: 'permissive' | 'standard' | 'strict';
  /** Enable PII protection in output */
  enablePII?: boolean;
  /** Enable streaming PII redaction */
  streamingPII?: boolean;
  /** Additional custom configuration */
  custom?: Partial<SentinelGuardrailConfig>;
}

// =============================================================================
// Guardrail Input/Output Types
// =============================================================================

/**
 * Context for validation operations.
 * Provides additional information about the validation context.
 */
export interface ValidationContext {
  /** Name of the action being validated */
  actionName?: string;
  /** Agent name or identifier */
  agentName?: string;
  /** User or session identifier */
  userId?: string;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Extended validation result with all validation module results.
 */
export interface FullValidationResult {
  /** Overall safety assessment */
  safe: boolean;
  /** Recommended action */
  action: GuardrailAction;
  /** Human-readable message */
  message: string;
  /** THSP validation results (if enabled) */
  thsp?: THSPValidationResult;
  /** OWASP validation results (if enabled) */
  owasp?: OWASPValidationResult;
  /** PII detection results (if enabled) */
  pii?: PIIDetectionResult;
  /** Modified content (if action is 'modify') */
  modifiedContent?: string;
  /** Validation metadata */
  metadata: {
    /** Validation timestamp */
    timestamp: number;
    /** Time taken in ms */
    durationMs: number;
    /** Which validators were run */
    validatorsRun: string[];
    /** Configuration used */
    config: SentinelGuardrailConfig;
  };
}

// =============================================================================
// Streaming Types
// =============================================================================

/**
 * State for streaming guardrail operations.
 * Used to maintain context across streaming chunks.
 */
export interface StreamingGuardrailState {
  /** Accumulated text buffer */
  buffer: string;
  /** Running PII detection results */
  piiMatches: PIIMatch[];
  /** Whether violation was detected */
  violationDetected: boolean;
  /** Chunk index */
  chunkIndex: number;
}

/**
 * Result of processing a streaming chunk.
 */
export interface StreamingChunkResult {
  /** Processed (possibly redacted) text */
  text: string;
  /** Whether to abort the stream */
  abort: boolean;
  /** Abort message if applicable */
  abortMessage?: string;
  /** Updated state */
  state: StreamingGuardrailState;
}

// =============================================================================
// VoltAgent Compatibility Types
// =============================================================================

// Re-export public VoltAgent types for full compatibility
export type {
  InputGuardrailArgs as VoltAgentInputArgs,
  InputGuardrailResult as VoltAgentInputResult,
  OutputGuardrailArgs as VoltAgentOutputArgs,
  OutputGuardrailResult as VoltAgentOutputResult,
  VoltAgentTextStreamPart,
  GuardrailContext as VoltAgentGuardrailContext,
} from '@voltagent/core';

/**
 * VoltAgent operation types.
 */
export type VoltAgentOperationType = 'generateText' | 'streamText' | 'generateObject' | 'streamObject';

/**
 * Output guardrail stream arguments.
 * Structurally compatible with VoltAgent's OutputGuardrailStreamArgs.
 * Note: This type is not publicly exported by @voltagent/core, so we define it here.
 */
export interface VoltAgentOutputStreamArgs {
  /** The agent instance */
  agent: unknown;
  /** Operation context */
  context: unknown;
  /** Operation type */
  operation: VoltAgentOperationType;
  /** The current stream part being processed */
  part: import('@voltagent/core').VoltAgentTextStreamPart;
  /** All stream parts received so far */
  streamParts: import('@voltagent/core').VoltAgentTextStreamPart[];
  /** Mutable state object for maintaining context across stream parts */
  state: Record<string, unknown>;
  /** Function to abort the stream */
  abort: (reason?: string) => never;
}

/**
 * Output guardrail stream result type.
 */
export type VoltAgentOutputStreamResult =
  | import('@voltagent/core').VoltAgentTextStreamPart
  | null
  | undefined
  | Promise<import('@voltagent/core').VoltAgentTextStreamPart | null | undefined>;

/**
 * Stream handler function type for output guardrails.
 * Structurally compatible with VoltAgent's OutputGuardrailStreamHandler.
 */
export type VoltAgentStreamHandler = (args: VoltAgentOutputStreamArgs) => VoltAgentOutputStreamResult;

/**
 * Legacy streaming text source (for backwards compatibility).
 * @deprecated Use VoltAgentStreamHandler instead for VoltAgent integration.
 */
export type TextStream = AsyncIterable<string>;

/**
 * Legacy stream handler function type (for backwards compatibility).
 * @deprecated Use VoltAgentStreamHandler instead for VoltAgent integration.
 */
export type StreamHandler = (args: {
  textStream: TextStream;
  state?: StreamingGuardrailState;
}) => AsyncGenerator<string, void, unknown>;
