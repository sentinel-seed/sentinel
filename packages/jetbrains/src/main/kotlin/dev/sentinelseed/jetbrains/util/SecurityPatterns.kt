package dev.sentinelseed.jetbrains.util

/**
 * Security patterns for detecting secrets, SQL injection, and prompt injection.
 * Ported from VS Code extension patterns.
 */
object SecurityPatterns {

    // =========================================================================
    // SECRET DETECTION PATTERNS
    // =========================================================================

    data class SecretPattern(
        val id: String,
        val regex: Regex,
        val description: String,
        val severity: Severity
    )

    enum class Severity { LOW, MEDIUM, HIGH, CRITICAL }

    val SECRET_PATTERNS: List<SecretPattern> = listOf(
        // API Keys
        SecretPattern(
            id = "openai_key",
            regex = Regex("""\bsk-[a-zA-Z0-9]{48,}\b"""),
            description = "OpenAI API key detected",
            severity = Severity.CRITICAL
        ),
        SecretPattern(
            id = "anthropic_key",
            regex = Regex("""\bsk-ant-[a-zA-Z0-9-]+\b"""),
            description = "Anthropic API key detected",
            severity = Severity.CRITICAL
        ),
        SecretPattern(
            id = "aws_access_key",
            regex = Regex("""\bAKIA[0-9A-Z]{16}\b"""),
            description = "AWS Access Key detected",
            severity = Severity.CRITICAL
        ),
        SecretPattern(
            id = "aws_secret_key",
            regex = Regex("""\baws[_\-\s]?secret[_\-\s]?access[_\-\s]?key\b""", RegexOption.IGNORE_CASE),
            description = "AWS Secret Key reference detected",
            severity = Severity.CRITICAL
        ),
        SecretPattern(
            id = "github_token",
            regex = Regex("""\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})\b"""),
            description = "GitHub token detected",
            severity = Severity.CRITICAL
        ),
        SecretPattern(
            id = "slack_token",
            regex = Regex("""\bxox[baprs]-[a-zA-Z0-9-]+"""),
            description = "Slack token detected",
            severity = Severity.HIGH
        ),
        SecretPattern(
            id = "jwt_token",
            regex = Regex("""\beyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*"""),
            description = "JWT token detected",
            severity = Severity.HIGH
        ),
        SecretPattern(
            id = "private_key",
            regex = Regex("""-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----""", RegexOption.IGNORE_CASE),
            description = "Private key detected",
            severity = Severity.CRITICAL
        ),
        SecretPattern(
            id = "generic_api_key",
            regex = Regex("""\b(api[_\s-]?key|secret[_\s-]?key|access[_\s-]?token|auth[_\s-]?token)\s*[=:]\s*['"]?[a-zA-Z0-9_-]{20,}""", RegexOption.IGNORE_CASE),
            description = "Potential API key or secret",
            severity = Severity.HIGH
        ),
        SecretPattern(
            id = "password",
            regex = Regex("""\b(password|passwd|pwd)\s*[=:]\s*['"]?[^\s'"]{8,}""", RegexOption.IGNORE_CASE),
            description = "Potential password exposure",
            severity = Severity.CRITICAL
        ),
        SecretPattern(
            id = "connection_string",
            regex = Regex("""\b(mongodb|mysql|postgres|redis|amqp):\/\/[^\s]+""", RegexOption.IGNORE_CASE),
            description = "Database connection string",
            severity = Severity.CRITICAL
        ),

        // PII Patterns
        SecretPattern(
            id = "ssn",
            regex = Regex("""\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b"""),
            description = "Potential SSN pattern",
            severity = Severity.HIGH
        ),
        SecretPattern(
            id = "credit_card",
            regex = Regex("""\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"""),
            description = "Potential credit card number",
            severity = Severity.CRITICAL
        ),
        SecretPattern(
            id = "email",
            regex = Regex("""\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"""),
            description = "Email address detected",
            severity = Severity.LOW
        ),
        SecretPattern(
            id = "phone",
            regex = Regex("""\b(\+?1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"""),
            description = "Phone number pattern",
            severity = Severity.MEDIUM
        ),
        SecretPattern(
            id = "internal_url",
            regex = Regex("""\b(https?:\/\/)?((localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?\/?\S*)""", RegexOption.IGNORE_CASE),
            description = "Internal/private network URL",
            severity = Severity.MEDIUM
        )
    )

    // =========================================================================
    // SQL INJECTION PATTERNS
    // =========================================================================

    data class SqlPattern(
        val id: String,
        val regex: Regex,
        val category: SqlCategory,
        val severity: Severity,
        val description: String
    )

    enum class SqlCategory {
        DESTRUCTIVE,
        DATA_EXTRACTION,
        AUTHENTICATION_BYPASS,
        UNION_ATTACK,
        COMMENT_INJECTION,
        STACKED_QUERIES,
        BLIND_INJECTION,
        ERROR_BASED
    }

    val SQL_INJECTION_PATTERNS: List<SqlPattern> = listOf(
        // Destructive operations (CRITICAL)
        SqlPattern(
            id = "drop_table",
            regex = Regex("""\b(DROP|TRUNCATE|DELETE\s+FROM|ALTER)\s+(TABLE|DATABASE|SCHEMA|INDEX)\b""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DESTRUCTIVE,
            severity = Severity.CRITICAL,
            description = "Destructive SQL command detected"
        ),
        SqlPattern(
            id = "delete_all",
            regex = Regex("""\bDELETE\s+FROM\s+\w+\s*(WHERE\s+1\s*=\s*1|WHERE\s+TRUE|;)\s*""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DESTRUCTIVE,
            severity = Severity.CRITICAL,
            description = "DELETE with always-true condition"
        ),
        SqlPattern(
            id = "update_all",
            regex = Regex("""\bUPDATE\s+\w+\s+SET\s+.+\s+WHERE\s+(1\s*=\s*1|TRUE|''='')\b""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DESTRUCTIVE,
            severity = Severity.CRITICAL,
            description = "UPDATE with always-true condition"
        ),
        SqlPattern(
            id = "xp_cmdshell",
            regex = Regex("""\bxp_cmdshell\b""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DESTRUCTIVE,
            severity = Severity.CRITICAL,
            description = "Command shell execution attempt"
        ),
        SqlPattern(
            id = "exec_stored_proc",
            regex = Regex("""\bEXEC(UTE)?\s+(sp_|xp_)""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DESTRUCTIVE,
            severity = Severity.CRITICAL,
            description = "SQL Server stored procedure execution"
        ),

        // UNION attacks (HIGH)
        SqlPattern(
            id = "union_select",
            regex = Regex("""\bUNION\s+(ALL\s+)?SELECT\b""", RegexOption.IGNORE_CASE),
            category = SqlCategory.UNION_ATTACK,
            severity = Severity.HIGH,
            description = "UNION SELECT injection attempt"
        ),
        SqlPattern(
            id = "union_credentials",
            regex = Regex("""\bUNION\s+(ALL\s+)?SELECT\s+.*(password|passwd|pwd|secret|token|key|hash)""", RegexOption.IGNORE_CASE),
            category = SqlCategory.UNION_ATTACK,
            severity = Severity.CRITICAL,
            description = "UNION SELECT targeting credentials"
        ),

        // Authentication bypass (HIGH)
        SqlPattern(
            id = "string_bypass",
            regex = Regex("""'\s*(OR|AND)\s*'[^']*'\s*=\s*'[^']*'""", RegexOption.IGNORE_CASE),
            category = SqlCategory.AUTHENTICATION_BYPASS,
            severity = Severity.HIGH,
            description = "String comparison bypass pattern"
        ),
        SqlPattern(
            id = "numeric_bypass",
            regex = Regex("""'\s*(OR|AND)\s+\d+\s*=\s*\d+""", RegexOption.IGNORE_CASE),
            category = SqlCategory.AUTHENTICATION_BYPASS,
            severity = Severity.HIGH,
            description = "Numeric comparison bypass pattern"
        ),
        SqlPattern(
            id = "or_true_bypass",
            regex = Regex("""'\s*OR\s+1\s*=\s*1\s*(--|#|\/\*)""", RegexOption.IGNORE_CASE),
            category = SqlCategory.AUTHENTICATION_BYPASS,
            severity = Severity.HIGH,
            description = "Classic OR 1=1 bypass"
        ),
        SqlPattern(
            id = "admin_bypass",
            regex = Regex("""admin'\s*--""", RegexOption.IGNORE_CASE),
            category = SqlCategory.AUTHENTICATION_BYPASS,
            severity = Severity.HIGH,
            description = "Admin login bypass attempt"
        ),

        // Stacked queries (HIGH)
        SqlPattern(
            id = "stacked_query",
            regex = Regex(""";\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)""", RegexOption.IGNORE_CASE),
            category = SqlCategory.STACKED_QUERIES,
            severity = Severity.HIGH,
            description = "Stacked query detected"
        ),
        SqlPattern(
            id = "waitfor_delay",
            regex = Regex(""";\s*WAITFOR\s+DELAY""", RegexOption.IGNORE_CASE),
            category = SqlCategory.STACKED_QUERIES,
            severity = Severity.HIGH,
            description = "Time-based injection (WAITFOR)"
        ),
        SqlPattern(
            id = "sleep",
            regex = Regex(""";\s*SLEEP\s*\(""", RegexOption.IGNORE_CASE),
            category = SqlCategory.STACKED_QUERIES,
            severity = Severity.HIGH,
            description = "Time-based injection (SLEEP)"
        ),

        // Data extraction (HIGH)
        SqlPattern(
            id = "schema_enum",
            regex = Regex("""\bSELECT\s+.*(FROM\s+information_schema|FROM\s+mysql\.|FROM\s+pg_)""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DATA_EXTRACTION,
            severity = Severity.HIGH,
            description = "Schema enumeration attempt"
        ),
        SqlPattern(
            id = "db_info",
            regex = Regex("""\bSELECT\s+.*@@(version|user|database)""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DATA_EXTRACTION,
            severity = Severity.MEDIUM,
            description = "Database info extraction"
        ),
        SqlPattern(
            id = "load_file",
            regex = Regex("""\bSELECT\s+.*\bLOAD_FILE\s*\(""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DATA_EXTRACTION,
            severity = Severity.CRITICAL,
            description = "File read attempt (LOAD_FILE)"
        ),
        SqlPattern(
            id = "into_outfile",
            regex = Regex("""\bINTO\s+(OUT|DUMP)FILE\b""", RegexOption.IGNORE_CASE),
            category = SqlCategory.DATA_EXTRACTION,
            severity = Severity.CRITICAL,
            description = "File write attempt (INTO OUTFILE)"
        ),

        // Comment injection (MEDIUM)
        SqlPattern(
            id = "line_comment",
            regex = Regex("""--\s*$""", RegexOption.MULTILINE),
            category = SqlCategory.COMMENT_INJECTION,
            severity = Severity.MEDIUM,
            description = "SQL line comment at end"
        ),
        SqlPattern(
            id = "mysql_comment",
            regex = Regex("""#\s*$""", RegexOption.MULTILINE),
            category = SqlCategory.COMMENT_INJECTION,
            severity = Severity.MEDIUM,
            description = "MySQL comment at end"
        ),
        SqlPattern(
            id = "version_comment",
            regex = Regex("""\/\*![0-9]*.*?\*\/"""),
            category = SqlCategory.COMMENT_INJECTION,
            severity = Severity.HIGH,
            description = "MySQL version-specific comment"
        ),

        // Blind injection (MEDIUM)
        SqlPattern(
            id = "boolean_blind",
            regex = Regex("""\b(AND|OR)\s+\d+\s*(=|<|>|!=|<>)\s*\d+""", RegexOption.IGNORE_CASE),
            category = SqlCategory.BLIND_INJECTION,
            severity = Severity.MEDIUM,
            description = "Boolean-based blind injection"
        ),
        SqlPattern(
            id = "case_blind",
            regex = Regex("""\bCASE\s+WHEN\s+.+\s+THEN\s+.+\s+ELSE\b""", RegexOption.IGNORE_CASE),
            category = SqlCategory.BLIND_INJECTION,
            severity = Severity.MEDIUM,
            description = "CASE-based blind injection"
        ),
        SqlPattern(
            id = "hex_payload",
            regex = Regex("""0x[0-9a-f]{8,}""", RegexOption.IGNORE_CASE),
            category = SqlCategory.BLIND_INJECTION,
            severity = Severity.MEDIUM,
            description = "Hex-encoded payload detected"
        ),
        SqlPattern(
            id = "char_encoding",
            regex = Regex("""\bCHAR\s*\(\s*\d+\s*(,\s*\d+\s*)+\)""", RegexOption.IGNORE_CASE),
            category = SqlCategory.BLIND_INJECTION,
            severity = Severity.MEDIUM,
            description = "CHAR encoding detected"
        )
    )

    // =========================================================================
    // PROMPT INJECTION PATTERNS
    // =========================================================================

    data class PromptPattern(
        val id: String,
        val regex: Regex,
        val description: String,
        val severity: Severity,
        val gates: List<String>
    )

    val PROMPT_INJECTION_PATTERNS: List<PromptPattern> = listOf(
        // Direct instruction override
        PromptPattern(
            id = "ignore_instructions",
            regex = Regex("""\b(ignore|disregard|forget|skip|bypass)\s+(all\s+)?(previous|prior|above|your|earlier|initial|everything)?\s*(you\s+were\s+told|instructions?|prompts?|rules?|guidelines?|directions?|constraints?)?\b""", RegexOption.IGNORE_CASE),
            description = "Attempts to override previous instructions",
            severity = Severity.HIGH,
            gates = listOf("scope")
        ),
        PromptPattern(
            id = "new_instructions",
            regex = Regex("""\b(new\s+instructions?|from\s+now\s+on|starting\s+now|begin(ning)?\s+now)\s*[:-]?\s*(you\s+(are|will|must|should)|ignore|forget)""", RegexOption.IGNORE_CASE),
            description = "Attempts to set new instructions",
            severity = Severity.HIGH,
            gates = listOf("scope")
        ),

        // Role/Persona manipulation
        PromptPattern(
            id = "role_switch",
            regex = Regex("""\b(you\s+are\s+now|pretend\s+(to\s+be|you'?re)|act\s+as(\s+if)?|roleplay\s+as|imagine\s+you'?re|behave\s+(like|as))\s+(a|an|the)?\s*(DAN|evil|unrestricted|unfiltered|uncensored|jailbroken|different|new)\b""", RegexOption.IGNORE_CASE),
            description = "Attempts to switch AI persona/role",
            severity = Severity.HIGH,
            gates = listOf("scope", "truth")
        ),
        PromptPattern(
            id = "dan_mode",
            regex = Regex("""\b(DAN\s*mode|do\s*anything\s*now|developer\s*mode|god\s*mode|sudo\s*mode|admin\s*mode|maintenance\s*mode|debug\s*mode)\b""", RegexOption.IGNORE_CASE),
            description = "Known jailbreak mode activation",
            severity = Severity.CRITICAL,
            gates = listOf("scope")
        ),

        // Safety bypass
        PromptPattern(
            id = "bypass_safety",
            regex = Regex("""\b(bypass|disable|turn\s+off|remove|ignore|override|circumvent)\s+(the\s+)?(safety|content\s*filter|guardrails?|restrictions?|limitations?|censorship|moderation)\b""", RegexOption.IGNORE_CASE),
            description = "Attempts to bypass safety mechanisms",
            severity = Severity.CRITICAL,
            gates = listOf("scope", "harm")
        ),
        PromptPattern(
            id = "unlock_capabilities",
            regex = Regex("""\b(unlock|unleash|free|liberate)\s+(your|the|hidden|true|full)?\s*(potential|capabilities?|power|abilities?)\b""", RegexOption.IGNORE_CASE),
            description = "Attempts to unlock restricted capabilities",
            severity = Severity.HIGH,
            gates = listOf("scope")
        ),

        // Instruction confusion
        PromptPattern(
            id = "fake_system_message",
            regex = Regex("""\[(system|admin|developer|instructor|master)\s*(message|says?|note|instruction)\s*[:\]]""", RegexOption.IGNORE_CASE),
            description = "Fake system message injection",
            severity = Severity.HIGH,
            gates = listOf("scope", "truth")
        ),
        PromptPattern(
            id = "fake_context",
            regex = Regex("""\b(the\s+user\s+(wants|asked|said)|user\s+instruction|human\s+says?|end\s+of\s+system\s+prompt)\s*[:-]""", RegexOption.IGNORE_CASE),
            description = "Fake context injection",
            severity = Severity.HIGH,
            gates = listOf("scope", "truth")
        ),

        // Delimiter manipulation
        PromptPattern(
            id = "delimiter_break",
            regex = Regex("""(<\/?(?:system|user|assistant|instruction|context|prompt)>|```(?:system|instruction|prompt)|###\s*(?:system|instruction|end))""", RegexOption.IGNORE_CASE),
            description = "Delimiter-based injection attempt",
            severity = Severity.HIGH,
            gates = listOf("scope")
        ),
        PromptPattern(
            id = "prompt_template",
            regex = Regex("""\{\{\s*(system|instruction|prompt|context)\s*\}\}|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]""", RegexOption.IGNORE_CASE),
            description = "Prompt template format injection",
            severity = Severity.HIGH,
            gates = listOf("scope")
        ),

        // Jailbreak techniques
        PromptPattern(
            id = "hypothetical",
            regex = Regex("""\b(hypothetically|theoretically|in\s+a\s+fictional\s+scenario|let'?s\s+say|imagine|suppose)\s+.{0,30}(you\s+(could|would|can)|there\s+were\s+no\s+rules?|no\s+restrictions?)\b""", RegexOption.IGNORE_CASE),
            description = "Hypothetical scenario framing to bypass filters",
            severity = Severity.MEDIUM,
            gates = listOf("scope")
        ),
        PromptPattern(
            id = "character_play",
            regex = Regex("""\b(write\s+as|respond\s+as|speak\s+like|in\s+the\s+voice\s+of)\s+(a|an)\s*(villian|criminal|hacker|unethical|uncensored|unrestricted)\b""", RegexOption.IGNORE_CASE),
            description = "Character roleplay to bypass filters",
            severity = Severity.HIGH,
            gates = listOf("scope", "harm")
        ),
        PromptPattern(
            id = "educational_framing",
            regex = Regex("""\b(for\s+educational\s+purposes?|for\s+research|for\s+a\s+school\s+project|to\s+understand|to\s+learn\s+about)\s+.{0,30}(how\s+to|ways?\s+to)\s+(hack|exploit|attack|bypass|steal)\b""", RegexOption.IGNORE_CASE),
            description = "Educational framing for harmful content",
            severity = Severity.MEDIUM,
            gates = listOf("scope", "harm")
        ),
        PromptPattern(
            id = "grandma_exploit",
            regex = Regex("""\b(my\s+(grandmother|grandma|nana)|deceased\s+relative|bedtime\s+story)\s+.{0,50}(used\s+to|would|always|tell)\b""", RegexOption.IGNORE_CASE),
            description = "Grandma exploit / emotional manipulation",
            severity = Severity.MEDIUM,
            gates = listOf("scope", "harm")
        ),
        PromptPattern(
            id = "opposite_day",
            regex = Regex("""\b(opposite\s+day|reverse\s+mode|backwards?\s+mode|everything\s+is\s+reversed?)\b""", RegexOption.IGNORE_CASE),
            description = "Opposite/reverse mode jailbreak",
            severity = Severity.MEDIUM,
            gates = listOf("scope", "truth")
        ),

        // System prompt extraction
        PromptPattern(
            id = "extract_prompt",
            regex = Regex("""\b(reveal|show|display|print|output|tell\s+me|what\s+(is|are))\s+(your|the|my)?\s*(system\s*)?(prompt|instructions?|configuration|rules?|guidelines?)\b""", RegexOption.IGNORE_CASE),
            description = "System prompt extraction attempt",
            severity = Severity.HIGH,
            gates = listOf("scope")
        ),
        PromptPattern(
            id = "repeat_prompt",
            regex = Regex("""\b(repeat|recite|echo|copy)\s+(back|verbatim)?\s*(your|the|system)\s*(prompt|instructions?)\b""", RegexOption.IGNORE_CASE),
            description = "Prompt repetition request",
            severity = Severity.HIGH,
            gates = listOf("scope")
        )
    )

    // =========================================================================
    // OUTPUT VALIDATION PATTERNS
    // =========================================================================

    data class OutputPattern(
        val id: String,
        val regex: Regex,
        val description: String,
        val severity: Severity
    )

    val OUTPUT_VALIDATION_PATTERNS: List<OutputPattern> = listOf(
        // Code injection vectors
        OutputPattern(
            id = "xss",
            regex = Regex("""<script[^>]*>|javascript:|on(load|error|click|mouse)\s*=""", RegexOption.IGNORE_CASE),
            description = "Potential XSS pattern in output",
            severity = Severity.HIGH
        ),
        OutputPattern(
            id = "command_injection",
            regex = Regex("""[;&|`$]\s*(rm|del|format|shutdown|reboot|wget|curl|nc|bash|sh|cmd)\b""", RegexOption.IGNORE_CASE),
            description = "Potential command injection in output",
            severity = Severity.CRITICAL
        ),
        OutputPattern(
            id = "eval_functions",
            regex = Regex("""\b(eval|exec|system|popen|subprocess\.call|os\.system|child_process\.exec)\s*\(""", RegexOption.IGNORE_CASE),
            description = "Dangerous code execution function",
            severity = Severity.HIGH
        ),

        // Excessive agency
        OutputPattern(
            id = "auto_execute",
            regex = Regex("""\b(auto(matically)?|without\s+(confirmation|approval|permission|asking))\s*(execute|run|perform|send|delete|modify|transfer)\b""", RegexOption.IGNORE_CASE),
            description = "Autonomous action without confirmation",
            severity = Severity.HIGH
        ),
        OutputPattern(
            id = "destructive_action",
            regex = Regex("""\b(delete|remove|destroy|wipe|format)\s+(all|everything|database|files?|data)\b""", RegexOption.IGNORE_CASE),
            description = "Destructive action capability",
            severity = Severity.CRITICAL
        ),
        OutputPattern(
            id = "financial_action",
            regex = Regex("""\b(transfer|send|move)\s+(money|funds|payment|bitcoin|crypto|eth)\s*(to|from)\b""", RegexOption.IGNORE_CASE),
            description = "Financial transaction capability",
            severity = Severity.HIGH
        ),

        // System prompt leakage
        OutputPattern(
            id = "leaked_prompt",
            regex = Regex("""\b(my\s+(system\s+)?instructions?\s+(are|say)|here\s+(is|are)\s+my\s+(system\s+)?prompt|i\s+was\s+(told|instructed|programmed)\s+to)\b""", RegexOption.IGNORE_CASE),
            description = "System prompt leakage in output",
            severity = Severity.HIGH
        ),

        // Misinformation indicators
        OutputPattern(
            id = "false_certainty",
            regex = Regex("""\b(this\s+is\s+(definitely|absolutely|certainly|100%)\s+(true|fact|correct)|proven\s+fact|scientifically\s+proven|no\s+doubt)\b""", RegexOption.IGNORE_CASE),
            description = "Overconfident factual claim",
            severity = Severity.MEDIUM
        ),
        OutputPattern(
            id = "dangerous_medical",
            regex = Regex("""\b(this\s+(will\s+)?cure|guaranteed\s+to\s+(heal|cure|treat)|miracle\s+(cure|treatment)|stop\s+taking\s+(your\s+)?medication)\b""", RegexOption.IGNORE_CASE),
            description = "Potentially dangerous medical advice",
            severity = Severity.CRITICAL
        )
    )
}
