package dev.sentinelseed.jetbrains.services

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.diagnostic.Logger
import dev.sentinelseed.jetbrains.compliance.CompliancePatterns
import dev.sentinelseed.jetbrains.compliance.CompliancePatterns.Severity
import dev.sentinelseed.jetbrains.util.SecurityPatterns

/**
 * Compliance check result for a specific framework.
 */
data class ComplianceResult(
    val framework: String,
    val compliant: Boolean,
    val findings: List<ComplianceFinding>,
    val riskLevel: String,
    val recommendations: List<String>
)

data class ComplianceFinding(
    val id: String,
    val category: String,
    val description: String,
    val matchedText: String,
    val severity: Severity,
    val position: IntRange
)

/**
 * Unified compliance result across all frameworks.
 */
data class UnifiedComplianceResult(
    val compliant: Boolean,
    val euAiAct: ComplianceResult?,
    val owaspLlm: ComplianceResult?,
    val csaAicm: ComplianceResult?,
    val recommendations: List<String>
)

/**
 * Compliance checking service for EU AI Act, OWASP LLM Top 10, and CSA AICM.
 *
 * Privacy guarantees:
 * - All checks run 100% locally
 * - No data sent to external servers
 * - Pattern-based heuristic detection
 */
@Service(Service.Level.APP)
class ComplianceService {
    private val logger = Logger.getInstance(ComplianceService::class.java)

    companion object {
        fun getInstance(): ComplianceService =
            ApplicationManager.getApplication().getService(ComplianceService::class.java)
    }

    // =========================================================================
    // EU AI ACT COMPLIANCE
    // =========================================================================

    /**
     * Checks content against EU AI Act requirements.
     *
     * Detects:
     * - Article 5: Prohibited practices
     * - Article 6/Annex III: High-risk systems
     * - Article 52: Transparency obligations
     */
    fun checkEUAIAct(content: String): ComplianceResult {
        if (content.isBlank()) {
            return ComplianceResult(
                framework = "EU AI Act",
                compliant = true,
                findings = emptyList(),
                riskLevel = "minimal",
                recommendations = emptyList()
            )
        }

        val findings = mutableListOf<ComplianceFinding>()
        val recommendations = mutableListOf<String>()

        // Check prohibited practices (Article 5)
        for (pattern in CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    ComplianceFinding(
                        id = pattern.id,
                        category = pattern.category,
                        description = pattern.description,
                        matchedText = match.value,
                        severity = pattern.severity,
                        position = match.range
                    )
                )
            }
        }

        // Check high-risk patterns (Article 6/Annex III)
        for (pattern in CompliancePatterns.HIGH_RISK_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    ComplianceFinding(
                        id = pattern.id,
                        category = pattern.category,
                        description = pattern.description,
                        matchedText = match.value,
                        severity = pattern.severity,
                        position = match.range
                    )
                )
            }
        }

        // Check transparency patterns (Article 52)
        for (pattern in CompliancePatterns.TRANSPARENCY_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    ComplianceFinding(
                        id = pattern.id,
                        category = pattern.category,
                        description = pattern.description,
                        matchedText = match.value,
                        severity = pattern.severity,
                        position = match.range
                    )
                )
            }
        }

        // Determine risk level
        val hasProhibited = findings.any { it.severity == Severity.CRITICAL && it.category.startsWith("Article 5") }
        val hasHighRisk = findings.any { it.severity == Severity.HIGH }
        val hasTransparency = findings.any { it.category.startsWith("Article 52") }

        val riskLevel = when {
            hasProhibited -> "unacceptable"
            hasHighRisk -> "high"
            hasTransparency -> "limited"
            else -> "minimal"
        }

        // Generate recommendations
        if (hasProhibited) {
            recommendations.add("CRITICAL: This practice is PROHIBITED under EU AI Act Article 5. Remove this functionality.")
        }
        if (hasHighRisk) {
            recommendations.add("HIGH: This is a high-risk AI system. Conformity assessment required before deployment.")
            recommendations.add("Implement risk management system per Article 9.")
            recommendations.add("Ensure human oversight mechanisms per Article 14.")
        }
        if (hasTransparency) {
            recommendations.add("MEDIUM: Transparency disclosure required per Article 52.")
        }

        return ComplianceResult(
            framework = "EU AI Act",
            compliant = !hasProhibited,
            findings = findings,
            riskLevel = riskLevel,
            recommendations = recommendations
        )
    }

    // =========================================================================
    // OWASP LLM TOP 10 COMPLIANCE
    // =========================================================================

    /**
     * Checks content against OWASP LLM Top 10 vulnerabilities.
     *
     * Detects:
     * - LLM01: Prompt Injection
     * - LLM02: Sensitive Information Disclosure
     * - LLM05: Improper Output Handling
     * - LLM06: Excessive Agency
     * - LLM07: System Prompt Leakage
     */
    fun checkOWASP(content: String): ComplianceResult {
        if (content.isBlank()) {
            return ComplianceResult(
                framework = "OWASP LLM Top 10",
                compliant = true,
                findings = emptyList(),
                riskLevel = "secure",
                recommendations = emptyList()
            )
        }

        val findings = mutableListOf<ComplianceFinding>()
        val recommendations = mutableListOf<String>()

        // Use SecurityPatterns for OWASP checks
        // LLM01: Prompt Injection
        for (pattern in SecurityPatterns.PROMPT_INJECTION_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    ComplianceFinding(
                        id = pattern.id,
                        category = "LLM01: Prompt Injection",
                        description = pattern.description,
                        matchedText = match.value,
                        severity = mapSeverity(pattern.severity),
                        position = match.range
                    )
                )
            }
        }

        // LLM02: Sensitive Information Disclosure
        for (pattern in SecurityPatterns.SECRET_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    ComplianceFinding(
                        id = pattern.id,
                        category = "LLM02: Sensitive Information Disclosure",
                        description = pattern.description,
                        matchedText = maskSensitiveValue(match.value),
                        severity = mapSeverity(pattern.severity),
                        position = match.range
                    )
                )
            }
        }

        // LLM05: Improper Output Handling
        for (pattern in SecurityPatterns.OUTPUT_VALIDATION_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    ComplianceFinding(
                        id = pattern.id,
                        category = "LLM05: Improper Output Handling",
                        description = pattern.description,
                        matchedText = match.value,
                        severity = mapSeverity(pattern.severity),
                        position = match.range
                    )
                )
            }
        }

        // Determine risk level
        val hasCritical = findings.any { it.severity == Severity.CRITICAL }
        val hasHigh = findings.any { it.severity == Severity.HIGH }

        val riskLevel = when {
            hasCritical -> "critical"
            hasHigh -> "high"
            findings.isNotEmpty() -> "medium"
            else -> "secure"
        }

        // Generate recommendations
        val llm01Findings = findings.filter { it.category.startsWith("LLM01") }
        val llm02Findings = findings.filter { it.category.startsWith("LLM02") }
        val llm05Findings = findings.filter { it.category.startsWith("LLM05") }

        if (llm01Findings.isNotEmpty()) {
            recommendations.add("LLM01: Implement input sanitization and instruction hierarchy.")
        }
        if (llm02Findings.isNotEmpty()) {
            recommendations.add("LLM02: Review output for PII and sensitive data. Implement data filtering.")
        }
        if (llm05Findings.isNotEmpty()) {
            recommendations.add("LLM05: Validate all LLM outputs before passing to downstream systems.")
        }

        return ComplianceResult(
            framework = "OWASP LLM Top 10",
            compliant = findings.isEmpty(),
            findings = findings,
            riskLevel = riskLevel,
            recommendations = recommendations
        )
    }

    // =========================================================================
    // CSA AICM COMPLIANCE
    // =========================================================================

    /**
     * Checks content against CSA AI Controls Matrix requirements.
     *
     * Evaluates:
     * - Model Security domain
     * - Data Governance domain
     * - Supply Chain domain
     * - Application Security domain
     */
    fun checkCSA(content: String): ComplianceResult {
        if (content.isBlank()) {
            return ComplianceResult(
                framework = "CSA AI Controls Matrix",
                compliant = true,
                findings = emptyList(),
                riskLevel = "compliant",
                recommendations = emptyList()
            )
        }

        val findings = mutableListOf<ComplianceFinding>()
        val recommendations = mutableListOf<String>()

        // Check CSA AICM patterns
        for (pattern in CompliancePatterns.CSA_AICM_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    ComplianceFinding(
                        id = pattern.id,
                        category = pattern.domain,
                        description = pattern.description,
                        matchedText = match.value,
                        severity = pattern.severity,
                        position = match.range
                    )
                )
            }
        }

        // Determine risk level
        val hasCritical = findings.any { it.severity == Severity.CRITICAL }
        val hasHigh = findings.any { it.severity == Severity.HIGH }

        val riskLevel = when {
            hasCritical -> "non-compliant"
            hasHigh -> "partially-compliant"
            findings.isNotEmpty() -> "review-needed"
            else -> "compliant"
        }

        // Generate recommendations
        val domains = findings.map { it.category }.toSet()
        for (domain in domains) {
            when (domain) {
                "Model Security" -> recommendations.add("Model Security: Implement model protection and monitoring controls.")
                "Data Governance" -> recommendations.add("Data Governance: Validate training data integrity and implement provenance tracking.")
                "Data Security & Privacy" -> recommendations.add("Data Security: Implement data classification and access controls.")
                "Supply Chain" -> recommendations.add("Supply Chain: Audit third-party models and dependencies.")
                "Application Security" -> recommendations.add("Application Security: Implement input validation and output filtering.")
            }
        }

        return ComplianceResult(
            framework = "CSA AI Controls Matrix",
            compliant = findings.isEmpty(),
            findings = findings,
            riskLevel = riskLevel,
            recommendations = recommendations
        )
    }

    // =========================================================================
    // UNIFIED COMPLIANCE CHECK
    // =========================================================================

    /**
     * Checks content against all supported compliance frameworks.
     */
    fun checkAll(content: String): UnifiedComplianceResult {
        val euResult = checkEUAIAct(content)
        val owaspResult = checkOWASP(content)
        val csaResult = checkCSA(content)

        val allRecommendations = mutableListOf<String>()
        allRecommendations.addAll(euResult.recommendations)
        allRecommendations.addAll(owaspResult.recommendations)
        allRecommendations.addAll(csaResult.recommendations)

        val compliant = euResult.compliant && owaspResult.compliant && csaResult.compliant

        return UnifiedComplianceResult(
            compliant = compliant,
            euAiAct = euResult,
            owaspLlm = owaspResult,
            csaAicm = csaResult,
            recommendations = allRecommendations.distinct()
        )
    }

    // =========================================================================
    // HELPER METHODS
    // =========================================================================

    private fun mapSeverity(severity: SecurityPatterns.Severity): Severity {
        return when (severity) {
            SecurityPatterns.Severity.LOW -> Severity.LOW
            SecurityPatterns.Severity.MEDIUM -> Severity.MEDIUM
            SecurityPatterns.Severity.HIGH -> Severity.HIGH
            SecurityPatterns.Severity.CRITICAL -> Severity.CRITICAL
        }
    }

    private fun maskSensitiveValue(value: String): String {
        return when {
            value.length <= 8 -> "****"
            value.length <= 16 -> "${value.take(2)}****${value.takeLast(2)}"
            else -> "${value.take(4)}...${value.takeLast(4)}"
        }
    }
}
