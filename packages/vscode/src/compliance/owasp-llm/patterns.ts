/**
 * OWASP LLM Top 10 (2025) Compliance Patterns
 *
 * Pattern definitions for detecting OWASP LLM Top 10 vulnerabilities.
 * Based on OWASP Top 10 for LLM Applications 2025.
 *
 * Vulnerabilities covered:
 * - LLM01: Prompt Injection
 * - LLM02: Sensitive Information Disclosure
 * - LLM03: Supply Chain Vulnerabilities (indirect)
 * - LLM04: Data and Model Poisoning (indirect)
 * - LLM05: Improper Output Handling
 * - LLM06: Excessive Agency
 * - LLM07: System Prompt Leakage
 * - LLM08: Vector and Embedding Weaknesses (infrastructure)
 * - LLM09: Misinformation
 * - LLM10: Unbounded Consumption (infrastructure)
 *
 * Reference: https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/
 */

import { CompliancePattern, OWASPVulnerability, THSPGate, CoverageLevel } from '../types';

// ============================================================================
// LLM01: PROMPT INJECTION PATTERNS
// ============================================================================

/**
 * Patterns for detecting prompt injection attempts.
 * These patterns detect attempts to manipulate LLM instructions.
 */
export const PROMPT_INJECTION_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // Direct Instruction Override
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm01_ignore_instructions',
        pattern: /\b(ignore|disregard|forget|skip|bypass)\s+(all\s+)?(previous|prior|above|your|earlier|initial)?\s*(instructions?|prompts?|rules?|guidelines?|directions?|constraints?)\b/gi,
        description: 'Attempts to override previous instructions',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_new_instructions',
        pattern: /\b(new\s+instructions?|from\s+now\s+on|starting\s+now|begin(ning)?\s+now)\s*[:-]?\s*(you\s+(are|will|must|should)|ignore|forget)/gi,
        description: 'Attempts to set new instructions',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM01',
    },

    // -------------------------------------------------------------------------
    // Role/Persona Manipulation
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm01_role_switch',
        pattern: /\b(you\s+are\s+now|pretend\s+(to\s+be|you'?re)|act\s+as(\s+if)?|roleplay\s+as|imagine\s+you'?re|behave\s+(like|as))\s+(a|an|the)?\s*(DAN|evil|unrestricted|unfiltered|uncensored|jailbroken|different|new)\b/gi,
        description: 'Attempts to switch AI persona/role',
        severity: 'high',
        gates: ['scope', 'truth'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_dan_mode',
        pattern: /\b(DAN\s*mode|do\s*anything\s*now|developer\s*mode|god\s*mode|sudo\s*mode|admin\s*mode|maintenance\s*mode|debug\s*mode)\b/gi,
        description: 'Known jailbreak mode activation',
        severity: 'critical',
        gates: ['scope'],
        category: 'LLM01',
    },

    // -------------------------------------------------------------------------
    // Safety Bypass
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm01_bypass_safety',
        pattern: /\b(bypass|disable|turn\s+off|remove|ignore|override|circumvent)\s+(the\s+)?(safety|content\s*filter|guardrails?|restrictions?|limitations?|censorship|moderation)\b/gi,
        description: 'Attempts to bypass safety mechanisms',
        severity: 'critical',
        gates: ['scope', 'harm'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_unlock',
        pattern: /\b(unlock|unleash|free|liberate)\s+(your|the|hidden|true|full)?\s*(potential|capabilities?|power|abilities?)\b/gi,
        description: 'Attempts to unlock restricted capabilities',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM01',
    },

    // -------------------------------------------------------------------------
    // Instruction Confusion
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm01_system_says',
        pattern: /\[(system|admin|developer|instructor|master)\s*(message|says?|note|instruction)\s*[:\]]/gi,
        description: 'Fake system message injection',
        severity: 'high',
        gates: ['scope', 'truth'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_fake_context',
        pattern: /\b(the\s+user\s+(wants|asked|said)|user\s+instruction|human\s+says?|end\s+of\s+system\s+prompt)\s*[:-]/gi,
        description: 'Fake context injection',
        severity: 'high',
        gates: ['scope', 'truth'],
        category: 'LLM01',
    },

    // -------------------------------------------------------------------------
    // Delimiter Manipulation
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm01_delimiter_break',
        pattern: /(<\/?(?:system|user|assistant|instruction|context|prompt)>|```(?:system|instruction|prompt)|###\s*(?:system|instruction|end))/gi,
        description: 'Delimiter-based injection attempt',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM01',
    },

    // -------------------------------------------------------------------------
    // Advanced Jailbreak Techniques (Real-world examples)
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm01_hypothetical',
        pattern: /\b(hypothetically|theoretically|in\s+a\s+fictional\s+scenario|let'?s\s+say|imagine|suppose)\s+.{0,30}(you\s+(could|would|can)|there\s+were\s+no\s+rules?|no\s+restrictions?)\b/gi,
        description: 'Hypothetical scenario framing to bypass filters',
        severity: 'medium',
        gates: ['scope'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_character_play',
        pattern: /\b(write\s+as|respond\s+as|speak\s+like|in\s+the\s+voice\s+of)\s+(a|an)\s*(villian|criminal|hacker|unethical|uncensored|unrestricted)\b/gi,
        description: 'Character roleplay to bypass filters',
        severity: 'high',
        gates: ['scope', 'harm'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_base64_obfuscation',
        pattern: /\b(base64|decode|decrypt|deobfuscate)\s*[:(]/gi,
        description: 'Obfuscation technique for hidden instructions',
        severity: 'medium',
        gates: ['scope'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_markdown_injection',
        pattern: /!\[[^\]]*\]\([^)]*(?:onerror|onload|javascript:)[^)]*\)/gi,
        description: 'Markdown image injection with JavaScript',
        severity: 'high',
        gates: ['scope', 'harm'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_token_smuggling',
        pattern: /\u200b|\u200c|\u200d|\ufeff|[\u2000-\u200f]/g,
        description: 'Zero-width characters for token smuggling',
        severity: 'medium',
        gates: ['scope'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_continuation_attack',
        pattern: /\b(continue|finish|complete)\s+(the|this|your)\s*(previous|last)?\s*(response|answer|text|sentence)\s*(without|ignoring|regardless)\b/gi,
        description: 'Continuation attack to bypass safety checks',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_prompt_template',
        pattern: /\{\{\s*(system|instruction|prompt|context)\s*\}\}|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]/gi,
        description: 'Prompt template format injection',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_translation_attack',
        pattern: /\b(translate|convert)\s+(this|the\s+following)\s+(to|into)\s+.{0,20}\s*(but|and)\s+(ignore|bypass|skip|without)\b/gi,
        description: 'Translation attack with embedded instructions',
        severity: 'medium',
        gates: ['scope'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_educational_framing',
        pattern: /\b(for\s+educational\s+purposes?|for\s+research|for\s+a\s+school\s+project|to\s+understand|to\s+learn\s+about)\s+.{0,30}(how\s+to|ways?\s+to)\s+(hack|exploit|attack|bypass|steal)\b/gi,
        description: 'Educational framing for harmful content',
        severity: 'medium',
        gates: ['scope', 'harm'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_opposite_day',
        pattern: /\b(opposite\s+day|reverse\s+mode|backwards?\s+mode|everything\s+is\s+reversed?)\b/gi,
        description: 'Opposite/reverse mode jailbreak',
        severity: 'medium',
        gates: ['scope', 'truth'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_grandma_exploit',
        pattern: /\b(my\s+(grandmother|grandma|nana)|deceased\s+relative|bedtime\s+story)\s+.{0,50}(used\s+to|would|always|tell)\b/gi,
        description: 'Grandma exploit / emotional manipulation',
        severity: 'medium',
        gates: ['scope', 'harm'],
        category: 'LLM01',
    },
    {
        id: 'owasp_llm01_splitting_attack',
        pattern: /\b(split|divide|break\s+into|one\s+word\s+at\s+a\s+time|character\s+by\s+character)\b.{0,30}\b(each|every|individual)\b/gi,
        description: 'Token splitting attack',
        severity: 'medium',
        gates: ['scope'],
        category: 'LLM01',
    },
];

// ============================================================================
// LLM02: SENSITIVE INFORMATION DISCLOSURE PATTERNS
// ============================================================================

/**
 * Patterns for detecting sensitive information in outputs.
 */
export const SENSITIVE_INFO_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // API Keys and Secrets
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm02_api_key',
        pattern: /\b(api[_\s-]?key|secret[_\s-]?key|access[_\s-]?token|auth[_\s-]?token|bearer\s+token)\s*[=:]\s*['"]?[a-zA-Z0-9_-]{20,}/gi,
        description: 'Potential API key or secret exposure',
        severity: 'critical',
        gates: ['harm', 'truth'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_aws_key',
        pattern: /\b(AKIA[0-9A-Z]{16}|aws[_\-\s]?secret[_\-\s]?access[_\-\s]?key)\b/gi,
        description: 'AWS credentials detected',
        severity: 'critical',
        gates: ['harm'],
        category: 'LLM02',
    },

    // -------------------------------------------------------------------------
    // Personal Information
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm02_ssn',
        pattern: /\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b/g,
        description: 'Potential SSN pattern',
        severity: 'high',
        gates: ['harm', 'truth'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_credit_card',
        pattern: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/g,
        description: 'Potential credit card number',
        severity: 'critical',
        gates: ['harm'],
        category: 'LLM02',
    },

    // -------------------------------------------------------------------------
    // Credentials
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm02_password',
        pattern: /\b(password|passwd|pwd)\s*[=:]\s*['"]?[^\s'"]{8,}/gi,
        description: 'Potential password exposure',
        severity: 'critical',
        gates: ['harm'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_connection_string',
        pattern: /\b(mongodb|mysql|postgres|redis|amqp):\/\/[^\s]+/gi,
        description: 'Database connection string exposure',
        severity: 'critical',
        gates: ['harm'],
        category: 'LLM02',
    },

    // -------------------------------------------------------------------------
    // Additional Sensitive Data Patterns
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm02_private_key',
        pattern: /-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----/gi,
        description: 'Private key detected',
        severity: 'critical',
        gates: ['harm'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_jwt_token',
        pattern: /\beyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*/g,
        description: 'JWT token detected',
        severity: 'high',
        gates: ['harm'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_github_token',
        pattern: /\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})\b/g,
        description: 'GitHub token detected',
        severity: 'critical',
        gates: ['harm'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_slack_token',
        pattern: /\bxox[baprs]-[a-zA-Z0-9-]+/g,
        description: 'Slack token detected',
        severity: 'high',
        gates: ['harm'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_email_extraction',
        pattern: /\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b/g,
        description: 'Email address in output',
        severity: 'low',
        gates: ['harm'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_phone_number',
        pattern: /\b(\+?1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g,
        description: 'Phone number pattern',
        severity: 'medium',
        gates: ['harm'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_internal_url',
        pattern: /\b(https?:\/\/)?((localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?\/?\S*)\b/gi,
        description: 'Internal/private network URL',
        severity: 'medium',
        gates: ['harm', 'scope'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_openai_key',
        pattern: /\bsk-[a-zA-Z0-9]{48,}\b/g,
        description: 'OpenAI API key detected',
        severity: 'critical',
        gates: ['harm'],
        category: 'LLM02',
    },
    {
        id: 'owasp_llm02_anthropic_key',
        pattern: /\bsk-ant-[a-zA-Z0-9-]+\b/g,
        description: 'Anthropic API key detected',
        severity: 'critical',
        gates: ['harm'],
        category: 'LLM02',
    },
];

// ============================================================================
// LLM05: IMPROPER OUTPUT HANDLING PATTERNS
// ============================================================================

/**
 * Patterns for detecting potentially dangerous outputs.
 */
export const IMPROPER_OUTPUT_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // Code Injection Vectors
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm05_sql_injection',
        pattern: /\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|OR\s+1\s*=\s*1|AND\s+1\s*=\s*1|'\s*OR\s*'|--\s*$)/gi,
        description: 'Potential SQL injection pattern in output',
        severity: 'high',
        gates: ['harm'],
        category: 'LLM05',
    },
    {
        id: 'owasp_llm05_xss',
        pattern: /<script[^>]*>|javascript:|on(load|error|click|mouse)\s*=/gi,
        description: 'Potential XSS pattern in output',
        severity: 'high',
        gates: ['harm'],
        category: 'LLM05',
    },
    {
        id: 'owasp_llm05_command_injection',
        pattern: /[;&|`$]\s*(rm|del|format|shutdown|reboot|wget|curl|nc|bash|sh|cmd)\b/gi,
        description: 'Potential command injection in output',
        severity: 'critical',
        gates: ['harm', 'scope'],
        category: 'LLM05',
    },

    // -------------------------------------------------------------------------
    // Dangerous Code Patterns
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm05_eval',
        pattern: /\b(eval|exec|system|popen|subprocess\.call|os\.system|child_process\.exec)\s*\(/gi,
        description: 'Dangerous code execution function',
        severity: 'high',
        gates: ['harm', 'scope'],
        category: 'LLM05',
    },
];

// ============================================================================
// LLM06: EXCESSIVE AGENCY PATTERNS
// ============================================================================

/**
 * Patterns for detecting excessive agent autonomy.
 */
export const EXCESSIVE_AGENCY_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // Autonomous Actions
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm06_auto_execute',
        pattern: /\b(auto(matically)?|without\s+(confirmation|approval|permission|asking))\s*(execute|run|perform|send|delete|modify|transfer)\b/gi,
        description: 'Autonomous action without confirmation',
        severity: 'high',
        gates: ['scope', 'purpose'],
        category: 'LLM06',
    },
    {
        id: 'owasp_llm06_unrestricted',
        pattern: /\b(unrestricted|unlimited|full)\s*(access|permission|control|authority)\b/gi,
        description: 'Unrestricted access or control',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM06',
    },

    // -------------------------------------------------------------------------
    // High-Impact Actions
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm06_financial',
        pattern: /\b(transfer|send|move)\s+(money|funds|payment|bitcoin|crypto|eth)\s*(to|from)\b/gi,
        description: 'Financial transaction capability',
        severity: 'high',
        gates: ['scope', 'purpose', 'harm'],
        category: 'LLM06',
    },
    {
        id: 'owasp_llm06_destructive',
        pattern: /\b(delete|remove|destroy|wipe|format)\s+(all|everything|database|files?|data)\b/gi,
        description: 'Destructive action capability',
        severity: 'critical',
        gates: ['scope', 'harm'],
        category: 'LLM06',
    },
];

// ============================================================================
// LLM07: SYSTEM PROMPT LEAKAGE PATTERNS
// ============================================================================

/**
 * Patterns for detecting system prompt extraction attempts (input)
 * and system prompt leakage (output).
 */
export const PROMPT_LEAKAGE_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // Extraction Attempts (for input checking)
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm07_extract_prompt',
        pattern: /\b(reveal|show|display|print|output|tell\s+me|what\s+(is|are))\s+(your|the|my)?\s*(system\s*)?(prompt|instructions?|configuration|rules?|guidelines?)\b/gi,
        description: 'System prompt extraction attempt',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM07',
    },
    {
        id: 'owasp_llm07_repeat_prompt',
        pattern: /\b(repeat|recite|echo|copy)\s+(back|verbatim)?\s*(your|the|system)\s*(prompt|instructions?)\b/gi,
        description: 'Prompt repetition request',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM07',
    },

    // -------------------------------------------------------------------------
    // Leakage Indicators (for output checking)
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm07_leaked_prompt',
        pattern: /\b(my\s+(system\s+)?instructions?\s+(are|say)|here\s+(is|are)\s+my\s+(system\s+)?prompt|i\s+was\s+(told|instructed|programmed)\s+to)\b/gi,
        description: 'System prompt leakage in output',
        severity: 'high',
        gates: ['scope', 'truth'],
        category: 'LLM07',
    },
    {
        id: 'owasp_llm07_internal_config',
        pattern: /\b(my\s+(initial|original|hidden)\s+(prompt|instructions)|system\s+configuration\s*[:=]|internal\s+rules?\s*[:=])\b/gi,
        description: 'Internal configuration exposure',
        severity: 'high',
        gates: ['scope'],
        category: 'LLM07',
    },
];

// ============================================================================
// LLM09: MISINFORMATION PATTERNS
// ============================================================================

/**
 * Patterns for detecting potential misinformation indicators.
 */
export const MISINFORMATION_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // False Certainty
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm09_false_certainty',
        pattern: /\b(this\s+is\s+(definitely|absolutely|certainly|100%)\s+(true|fact|correct)|proven\s+fact|scientifically\s+proven|no\s+doubt)\b/gi,
        description: 'Overconfident factual claim',
        severity: 'medium',
        gates: ['truth'],
        category: 'LLM09',
    },

    // -------------------------------------------------------------------------
    // Medical/Health Misinformation
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm09_medical_advice',
        pattern: /\b(this\s+(will\s+)?cure|guaranteed\s+to\s+(heal|cure|treat)|miracle\s+(cure|treatment)|stop\s+taking\s+(your\s+)?medication)\b/gi,
        description: 'Potentially dangerous medical advice',
        severity: 'critical',
        gates: ['truth', 'harm'],
        category: 'LLM09',
    },

    // -------------------------------------------------------------------------
    // Fabricated Sources
    // -------------------------------------------------------------------------
    {
        id: 'owasp_llm09_fake_citation',
        pattern: /\b(according\s+to\s+(a\s+)?study|research\s+(shows|proves)|experts?\s+say)\b(?!.*(?:https?:\/\/|doi:|pmid:))/gi,
        description: 'Uncited claim presented as fact',
        severity: 'low',
        gates: ['truth'],
        category: 'LLM09',
    },
];

// ============================================================================
// INFORMATIONAL PATTERNS
// ============================================================================

/**
 * Informational patterns that indicate good practices or observations.
 * These are not vulnerabilities but may be useful for awareness.
 * Severity 'info' - does not affect security status.
 */
export const INFORMATIONAL_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // Good Practices Detected
    // -------------------------------------------------------------------------
    {
        id: 'owasp_info_uncertainty_expressed',
        pattern: /\b(i'?m\s+not\s+(sure|certain)|i\s+don'?t\s+know|may\s+not\s+be\s+accurate|please\s+verify|consult\s+a\s+professional)\b/gi,
        description: 'Epistemic humility expressed (good practice)',
        severity: 'info',
        gates: ['truth'],
        category: 'LLM09',
    },
    {
        id: 'owasp_info_source_cited',
        pattern: /\b(source:|reference:|according\s+to\s+.{0,50}(https?:\/\/|doi:|pmid:)|cited\s+from)\b/gi,
        description: 'Source citation present (good practice)',
        severity: 'info',
        gates: ['truth'],
        category: 'LLM09',
    },
    {
        id: 'owasp_info_disclaimer',
        pattern: /\b(disclaimer|this\s+is\s+not\s+(medical|legal|financial)\s+advice|for\s+(informational|educational)\s+purposes\s+only)\b/gi,
        description: 'Appropriate disclaimer present',
        severity: 'info',
        gates: ['harm'],
        category: 'LLM09',
    },

    // -------------------------------------------------------------------------
    // Security Awareness
    // -------------------------------------------------------------------------
    {
        id: 'owasp_info_input_validation_mention',
        pattern: /\b(validate\s+(user\s+)?input|sanitize\s+input|input\s+validation|never\s+trust\s+user\s+input)\b/gi,
        description: 'Input validation awareness mentioned',
        severity: 'info',
        gates: ['scope'],
        category: 'LLM05',
    },
    {
        id: 'owasp_info_rate_limiting',
        pattern: /\b(rate\s+limit(ing)?|throttl(e|ing)|request\s+quota|api\s+quota)\b/gi,
        description: 'Rate limiting discussed (mitigates LLM10)',
        severity: 'info',
        gates: [],
        category: 'LLM10',
    },
];

// ============================================================================
// VULNERABILITY TO THSP GATE MAPPING
// ============================================================================

/**
 * Maps OWASP vulnerabilities to THSP gates and coverage levels.
 */
export const VULNERABILITY_GATE_MAPPING: Record<OWASPVulnerability, {
    gates: THSPGate[];
    coverage: CoverageLevel;
    description: string;
    thspProtection: string;
}> = {
    LLM01: {
        gates: ['scope'],
        coverage: 'strong',
        description: 'Manipulating LLMs via crafted inputs',
        thspProtection: 'Scope gate detects instruction override attempts',
    },
    LLM02: {
        gates: ['truth', 'harm'],
        coverage: 'strong',
        description: 'LLMs revealing sensitive data',
        thspProtection: 'Truth and Harm gates prevent unauthorized disclosure',
    },
    LLM03: {
        gates: [],
        coverage: 'indirect',
        description: 'Vulnerabilities in external components',
        thspProtection: 'Sentinel itself is a trusted supply chain component',
    },
    LLM04: {
        gates: ['truth'],
        coverage: 'indirect',
        description: 'Manipulated training/fine-tuning data',
        thspProtection: 'Truth gate may catch effects of poisoned data',
    },
    LLM05: {
        gates: ['truth', 'harm'],
        coverage: 'strong',
        description: 'Failing to validate LLM outputs',
        thspProtection: 'All outputs validated through THSP gates',
    },
    LLM06: {
        gates: ['scope', 'purpose'],
        coverage: 'strong',
        description: 'Excessive functionality or autonomy',
        thspProtection: 'Scope limits actions, Purpose requires justification',
    },
    LLM07: {
        gates: ['scope'],
        coverage: 'moderate',
        description: 'Exposing system prompt configurations',
        thspProtection: 'Scope gate detects extraction attempts',
    },
    LLM08: {
        gates: [],
        coverage: 'not_applicable',
        description: 'RAG pipeline and vector database vulnerabilities',
        thspProtection: 'Infrastructure-level concern, not behavioral',
    },
    LLM09: {
        gates: ['truth'],
        coverage: 'strong',
        description: 'LLMs generating false information',
        thspProtection: 'Truth gate enforces epistemic humility',
    },
    LLM10: {
        gates: [],
        coverage: 'not_applicable',
        description: 'Resource exhaustion attacks',
        thspProtection: 'Infrastructure-level rate limiting required',
    },
};

// ============================================================================
// COMBINED PATTERNS
// ============================================================================

/**
 * All OWASP LLM patterns for input validation.
 */
export const INPUT_VALIDATION_PATTERNS: CompliancePattern[] = [
    ...PROMPT_INJECTION_PATTERNS,
    ...PROMPT_LEAKAGE_PATTERNS.filter(p => p.id.includes('extract') || p.id.includes('repeat')),
    ...EXCESSIVE_AGENCY_PATTERNS,
];

/**
 * All OWASP LLM patterns for output validation.
 */
export const OUTPUT_VALIDATION_PATTERNS: CompliancePattern[] = [
    ...SENSITIVE_INFO_PATTERNS,
    ...IMPROPER_OUTPUT_PATTERNS,
    ...PROMPT_LEAKAGE_PATTERNS.filter(p => p.id.includes('leaked') || p.id.includes('internal')),
    ...MISINFORMATION_PATTERNS,
];

/**
 * All vulnerability detection patterns (excludes informational).
 * Use this for security-focused checks where 'info' findings are not needed.
 */
export const VULNERABILITY_PATTERNS: CompliancePattern[] = [
    ...PROMPT_INJECTION_PATTERNS,
    ...SENSITIVE_INFO_PATTERNS,
    ...IMPROPER_OUTPUT_PATTERNS,
    ...EXCESSIVE_AGENCY_PATTERNS,
    ...PROMPT_LEAKAGE_PATTERNS,
    ...MISINFORMATION_PATTERNS,
];

/**
 * All OWASP LLM patterns combined (including informational).
 * Use this for comprehensive analysis including good practice detection.
 */
export const ALL_OWASP_LLM_PATTERNS: CompliancePattern[] = [
    ...VULNERABILITY_PATTERNS,
    ...INFORMATIONAL_PATTERNS,
];

/**
 * Gets patterns for a specific vulnerability.
 * @param vuln - Vulnerability category
 * @param includeInfo - Whether to include informational patterns (default: false)
 */
export function getPatternsForVulnerability(
    vuln: OWASPVulnerability,
    includeInfo: boolean = false
): CompliancePattern[] {
    const patterns = includeInfo ? ALL_OWASP_LLM_PATTERNS : VULNERABILITY_PATTERNS;
    return patterns.filter(p => p.category === vuln);
}
