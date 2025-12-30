package dev.sentinelseed.jetbrains.compliance

/**
 * Compliance patterns for EU AI Act, OWASP LLM Top 10, and CSA AICM.
 * Ported from VS Code extension compliance module.
 */
object CompliancePatterns {

    // =========================================================================
    // EU AI ACT PATTERNS
    // =========================================================================

    data class EUAIActPattern(
        val id: String,
        val regex: Regex,
        val description: String,
        val category: String,
        val severity: Severity,
        val article: String
    )

    enum class Severity { INFO, LOW, MEDIUM, HIGH, CRITICAL }

    val PROHIBITED_PRACTICE_PATTERNS: List<EUAIActPattern> = listOf(
        // Article 5(1)(a) - Subliminal manipulation
        EUAIActPattern(
            id = "eu_subliminal",
            regex = Regex("""\b(subliminal|unconscious|hidden\s+influence|covert)\s+(techniques?|methods?|manipulation|influence)\b""", RegexOption.IGNORE_CASE),
            description = "Subliminal manipulation technique",
            category = "Article 5(1)(a)",
            severity = Severity.CRITICAL,
            article = "5"
        ),
        // Article 5(1)(b) - Exploitation of vulnerabilities
        EUAIActPattern(
            id = "eu_exploitation",
            regex = Regex("""\b(exploit|target|manipulate)\s+(vulnerable|elderly|disabled|children|minors|mental\s+health)\b""", RegexOption.IGNORE_CASE),
            description = "Exploitation of vulnerable groups",
            category = "Article 5(1)(b)",
            severity = Severity.CRITICAL,
            article = "5"
        ),
        // Article 5(1)(c) - Social scoring
        EUAIActPattern(
            id = "eu_social_scoring",
            regex = Regex("""\b(social\s+(credit|score|scoring)|citizen\s+score|behavior\s+score|trustworthiness\s+score)\b""", RegexOption.IGNORE_CASE),
            description = "Social scoring system",
            category = "Article 5(1)(c)",
            severity = Severity.CRITICAL,
            article = "5"
        ),
        // Article 5(1)(d) - Real-time biometric identification
        EUAIActPattern(
            id = "eu_biometric_realtime",
            regex = Regex("""\b(real-?time|live)\s+(biometric|facial)\s+(identification|recognition|scanning)\b""", RegexOption.IGNORE_CASE),
            description = "Real-time biometric identification in public spaces",
            category = "Article 5(1)(d)",
            severity = Severity.CRITICAL,
            article = "5"
        ),
        // Emotion recognition in workplace/education
        EUAIActPattern(
            id = "eu_emotion_workplace",
            regex = Regex("""\b(emotion|emotional|sentiment)\s+(recognition|detection|analysis)\s+(in|at|for)\s+(work|workplace|school|education)\b""", RegexOption.IGNORE_CASE),
            description = "Emotion recognition in workplace/education",
            category = "Article 5(1)(f)",
            severity = Severity.CRITICAL,
            article = "5"
        )
    )

    val HIGH_RISK_PATTERNS: List<EUAIActPattern> = listOf(
        // Annex III - Critical infrastructure
        EUAIActPattern(
            id = "eu_critical_infra",
            regex = Regex("""\b(power\s+grid|water\s+supply|traffic\s+control|critical\s+infrastructure)\s+(management|control|operation|system|AI)\b""", RegexOption.IGNORE_CASE),
            description = "Critical infrastructure AI",
            category = "Annex III (2)",
            severity = Severity.HIGH,
            article = "6"
        ),
        // Education/Employment
        EUAIActPattern(
            id = "eu_education_employment",
            regex = Regex("""\b(academic|educational|hiring|recruitment|employment)\s+(assessment|evaluation|decision|screening)\b""", RegexOption.IGNORE_CASE),
            description = "Education/Employment decision AI",
            category = "Annex III (3-4)",
            severity = Severity.HIGH,
            article = "6"
        ),
        // Essential services
        EUAIActPattern(
            id = "eu_essential_services",
            regex = Regex("""\b(credit\s+scoring|insurance\s+pricing|benefit\s+eligibility|loan\s+approval)\b""", RegexOption.IGNORE_CASE),
            description = "Essential services AI",
            category = "Annex III (5)",
            severity = Severity.HIGH,
            article = "6"
        ),
        // Law enforcement
        EUAIActPattern(
            id = "eu_law_enforcement",
            regex = Regex("""\b(predictive\s+policing|crime\s+prediction|recidivism|law\s+enforcement\s+AI)\b""", RegexOption.IGNORE_CASE),
            description = "Law enforcement AI",
            category = "Annex III (6)",
            severity = Severity.HIGH,
            article = "6"
        ),
        // Migration/Asylum
        EUAIActPattern(
            id = "eu_migration",
            regex = Regex("""\b(asylum|immigration|border\s+control|visa)\s+(assessment|decision|processing|screening)\b""", RegexOption.IGNORE_CASE),
            description = "Migration/asylum AI",
            category = "Annex III (7)",
            severity = Severity.HIGH,
            article = "6"
        )
    )

    val TRANSPARENCY_PATTERNS: List<EUAIActPattern> = listOf(
        // AI chatbots
        EUAIActPattern(
            id = "eu_chatbot",
            regex = Regex("""\b(chatbot|virtual\s+assistant|conversational\s+AI|AI\s+assistant)\b""", RegexOption.IGNORE_CASE),
            description = "AI chatbot requires disclosure",
            category = "Article 52(1)",
            severity = Severity.MEDIUM,
            article = "52"
        ),
        // Deepfakes
        EUAIActPattern(
            id = "eu_deepfake",
            regex = Regex("""\b(deepfake|synthetic\s+media|AI-?generated\s+(image|video|audio))\b""", RegexOption.IGNORE_CASE),
            description = "Synthetic media requires labeling",
            category = "Article 52(3)",
            severity = Severity.MEDIUM,
            article = "52"
        )
    )

    // =========================================================================
    // CSA AICM PATTERNS
    // =========================================================================

    data class CSAPattern(
        val id: String,
        val regex: Regex,
        val description: String,
        val domain: String,
        val severity: Severity
    )

    val CSA_AICM_PATTERNS: List<CSAPattern> = listOf(
        // Model Security
        CSAPattern(
            id = "csa_model_theft",
            regex = Regex("""\b(model\s+extraction|weight\s+stealing|model\s+theft|parameter\s+extraction)\b""", RegexOption.IGNORE_CASE),
            description = "Model security threat",
            domain = "Model Security",
            severity = Severity.HIGH
        ),
        CSAPattern(
            id = "csa_adversarial",
            regex = Regex("""\b(adversarial\s+attack|evasion\s+attack|perturbation\s+attack)\b""", RegexOption.IGNORE_CASE),
            description = "Adversarial attack pattern",
            domain = "Model Security",
            severity = Severity.HIGH
        ),
        // Data Governance
        CSAPattern(
            id = "csa_data_poisoning",
            regex = Regex("""\b(data\s+poisoning|training\s+data\s+manipulation|backdoor\s+injection|corrupted\s+training\s+(data|dataset))\b""", RegexOption.IGNORE_CASE),
            description = "Data poisoning threat",
            domain = "Data Governance",
            severity = Severity.HIGH
        ),
        CSAPattern(
            id = "csa_pii_exposure",
            regex = Regex("""\b(PII\s+exposure|personal\s+data\s+leak|data\s+breach|privacy\s+violation)\b""", RegexOption.IGNORE_CASE),
            description = "PII exposure risk",
            domain = "Data Security & Privacy",
            severity = Severity.HIGH
        ),
        // Supply Chain
        CSAPattern(
            id = "csa_supply_chain",
            regex = Regex("""\b(malicious\s+model|compromised\s+weights|supply\s+chain\s+attack)\b""", RegexOption.IGNORE_CASE),
            description = "Supply chain risk",
            domain = "Supply Chain",
            severity = Severity.HIGH
        ),
        // Application Security
        CSAPattern(
            id = "csa_prompt_injection",
            regex = Regex("""\b(prompt\s+injection|instruction\s+injection|jailbreak\s+attempt|input\s+sanitization\s+bypass|input\s+validation\s+bypass)\b""", RegexOption.IGNORE_CASE),
            description = "Prompt injection vulnerability",
            domain = "Application Security",
            severity = Severity.HIGH
        )
    )

    // =========================================================================
    // COMBINED ALL PATTERNS
    // =========================================================================

    val ALL_EU_PATTERNS: List<EUAIActPattern> =
        PROHIBITED_PRACTICE_PATTERNS + HIGH_RISK_PATTERNS + TRANSPARENCY_PATTERNS
}
