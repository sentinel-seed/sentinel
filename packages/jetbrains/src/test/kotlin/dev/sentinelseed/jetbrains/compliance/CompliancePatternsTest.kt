package dev.sentinelseed.jetbrains.compliance

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Nested
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource

/**
 * Tests for CompliancePatterns covering EU AI Act, CSA AICM patterns.
 */
@DisplayName("CompliancePatterns")
class CompliancePatternsTest {

    @Nested
    @DisplayName("EU AI Act - Prohibited Practices (Article 5)")
    inner class ProhibitedPracticesTests {

        @Test
        @DisplayName("Should detect subliminal manipulation")
        fun detectSubliminalManipulation() {
            val pattern = CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS.find { it.id == "eu_subliminal" }!!

            assertThat(pattern.regex.containsMatchIn("subliminal techniques to manipulate")).isTrue()
            assertThat(pattern.regex.containsMatchIn("hidden influence methods")).isTrue()
            assertThat(pattern.regex.containsMatchIn("normal advertising")).isFalse()
        }

        @Test
        @DisplayName("Should detect exploitation of vulnerable groups")
        fun detectExploitation() {
            val pattern = CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS.find { it.id == "eu_exploitation" }!!

            assertThat(pattern.regex.containsMatchIn("exploit vulnerable populations")).isTrue()
            assertThat(pattern.regex.containsMatchIn("target elderly users")).isTrue()
            assertThat(pattern.regex.containsMatchIn("manipulate children")).isTrue()
            assertThat(pattern.regex.containsMatchIn("help elderly users")).isFalse()
        }

        @Test
        @DisplayName("Should detect social scoring systems")
        fun detectSocialScoring() {
            val pattern = CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS.find { it.id == "eu_social_scoring" }!!

            assertThat(pattern.regex.containsMatchIn("implement social credit system")).isTrue()
            assertThat(pattern.regex.containsMatchIn("citizen score calculation")).isTrue()
            assertThat(pattern.regex.containsMatchIn("trustworthiness score")).isTrue()
            assertThat(pattern.regex.containsMatchIn("customer satisfaction score")).isFalse()
        }

        @Test
        @DisplayName("Should detect real-time biometric identification")
        fun detectBiometricId() {
            val pattern = CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS.find { it.id == "eu_biometric_realtime" }!!

            assertThat(pattern.regex.containsMatchIn("real-time facial recognition in public")).isTrue()
            assertThat(pattern.regex.containsMatchIn("live biometric identification")).isTrue()
            assertThat(pattern.regex.containsMatchIn("facial recognition for phone unlock")).isFalse()
        }

        @Test
        @DisplayName("Should detect emotion recognition in workplace/education")
        fun detectEmotionRecognition() {
            val pattern = CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS.find { it.id == "eu_emotion_workplace" }!!

            assertThat(pattern.regex.containsMatchIn("emotion recognition in workplace")).isTrue()
            assertThat(pattern.regex.containsMatchIn("emotional analysis at school")).isTrue()
            assertThat(pattern.regex.containsMatchIn("sentiment analysis for education")).isTrue()
        }

        @Test
        @DisplayName("All prohibited practices should have CRITICAL severity")
        fun prohibitedPracticesAreCritical() {
            CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS.forEach { pattern ->
                assertThat(pattern.severity)
                    .withFailMessage("Pattern ${pattern.id} should be CRITICAL")
                    .isEqualTo(CompliancePatterns.Severity.CRITICAL)
            }
        }

        @Test
        @DisplayName("All prohibited practices should reference Article 5")
        fun prohibitedPracticesReferenceArticle5() {
            CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS.forEach { pattern ->
                assertThat(pattern.article)
                    .withFailMessage("Pattern ${pattern.id} should reference Article 5")
                    .isEqualTo("5")
            }
        }
    }

    @Nested
    @DisplayName("EU AI Act - High-Risk Systems (Article 6/Annex III)")
    inner class HighRiskTests {

        @Test
        @DisplayName("Should detect critical infrastructure AI")
        fun detectCriticalInfra() {
            val pattern = CompliancePatterns.HIGH_RISK_PATTERNS.find { it.id == "eu_critical_infra" }!!

            assertThat(pattern.regex.containsMatchIn("power grid management AI")).isTrue()
            assertThat(pattern.regex.containsMatchIn("water supply control system")).isTrue()
            assertThat(pattern.regex.containsMatchIn("traffic control operation")).isTrue()
        }

        @Test
        @DisplayName("Should detect education/employment AI")
        fun detectEducationEmployment() {
            val pattern = CompliancePatterns.HIGH_RISK_PATTERNS.find { it.id == "eu_education_employment" }!!

            assertThat(pattern.regex.containsMatchIn("academic assessment system")).isTrue()
            assertThat(pattern.regex.containsMatchIn("hiring decision algorithm")).isTrue()
            assertThat(pattern.regex.containsMatchIn("recruitment screening tool")).isTrue()
        }

        @Test
        @DisplayName("Should detect essential services AI")
        fun detectEssentialServices() {
            val pattern = CompliancePatterns.HIGH_RISK_PATTERNS.find { it.id == "eu_essential_services" }!!

            assertThat(pattern.regex.containsMatchIn("credit scoring system")).isTrue()
            assertThat(pattern.regex.containsMatchIn("insurance pricing algorithm")).isTrue()
            assertThat(pattern.regex.containsMatchIn("loan approval AI")).isTrue()
        }

        @Test
        @DisplayName("Should detect law enforcement AI")
        fun detectLawEnforcement() {
            val pattern = CompliancePatterns.HIGH_RISK_PATTERNS.find { it.id == "eu_law_enforcement" }!!

            assertThat(pattern.regex.containsMatchIn("predictive policing system")).isTrue()
            assertThat(pattern.regex.containsMatchIn("recidivism prediction")).isTrue()
        }

        @Test
        @DisplayName("Should detect migration/asylum AI")
        fun detectMigration() {
            val pattern = CompliancePatterns.HIGH_RISK_PATTERNS.find { it.id == "eu_migration" }!!

            assertThat(pattern.regex.containsMatchIn("asylum assessment system")).isTrue()
            assertThat(pattern.regex.containsMatchIn("immigration decision tool")).isTrue()
            assertThat(pattern.regex.containsMatchIn("visa processing AI")).isTrue()
        }

        @Test
        @DisplayName("All high-risk patterns should have HIGH severity")
        fun highRiskPatternsAreHigh() {
            CompliancePatterns.HIGH_RISK_PATTERNS.forEach { pattern ->
                assertThat(pattern.severity)
                    .withFailMessage("Pattern ${pattern.id} should be HIGH")
                    .isEqualTo(CompliancePatterns.Severity.HIGH)
            }
        }
    }

    @Nested
    @DisplayName("EU AI Act - Transparency (Article 52)")
    inner class TransparencyTests {

        @Test
        @DisplayName("Should detect AI chatbots")
        fun detectChatbots() {
            val pattern = CompliancePatterns.TRANSPARENCY_PATTERNS.find { it.id == "eu_chatbot" }!!

            assertThat(pattern.regex.containsMatchIn("AI chatbot implementation")).isTrue()
            assertThat(pattern.regex.containsMatchIn("virtual assistant service")).isTrue()
            assertThat(pattern.regex.containsMatchIn("conversational AI")).isTrue()
        }

        @Test
        @DisplayName("Should detect deepfakes/synthetic media")
        fun detectDeepfakes() {
            val pattern = CompliancePatterns.TRANSPARENCY_PATTERNS.find { it.id == "eu_deepfake" }!!

            assertThat(pattern.regex.containsMatchIn("deepfake video")).isTrue()
            assertThat(pattern.regex.containsMatchIn("synthetic media generation")).isTrue()
            assertThat(pattern.regex.containsMatchIn("AI-generated image")).isTrue()
        }

        @Test
        @DisplayName("Transparency patterns should have MEDIUM severity")
        fun transparencyPatternsAreMedium() {
            CompliancePatterns.TRANSPARENCY_PATTERNS.forEach { pattern ->
                assertThat(pattern.severity)
                    .withFailMessage("Pattern ${pattern.id} should be MEDIUM")
                    .isEqualTo(CompliancePatterns.Severity.MEDIUM)
            }
        }
    }

    @Nested
    @DisplayName("CSA AI Controls Matrix Patterns")
    inner class CSAAICMTests {

        @Test
        @DisplayName("Should detect model security threats")
        fun detectModelSecurityThreats() {
            val modelTheftPattern = CompliancePatterns.CSA_AICM_PATTERNS.find { it.id == "csa_model_theft" }!!
            val adversarialPattern = CompliancePatterns.CSA_AICM_PATTERNS.find { it.id == "csa_adversarial" }!!

            assertThat(modelTheftPattern.regex.containsMatchIn("model extraction attack")).isTrue()
            assertThat(modelTheftPattern.regex.containsMatchIn("weight stealing attempt")).isTrue()
            assertThat(adversarialPattern.regex.containsMatchIn("adversarial attack vector")).isTrue()
        }

        @Test
        @DisplayName("Should detect data governance issues")
        fun detectDataGovernanceIssues() {
            val dataPoisoningPattern = CompliancePatterns.CSA_AICM_PATTERNS.find { it.id == "csa_data_poisoning" }!!
            val piiPattern = CompliancePatterns.CSA_AICM_PATTERNS.find { it.id == "csa_pii_exposure" }!!

            assertThat(dataPoisoningPattern.regex.containsMatchIn("data poisoning attack")).isTrue()
            assertThat(dataPoisoningPattern.regex.containsMatchIn("training data manipulation")).isTrue()
            assertThat(piiPattern.regex.containsMatchIn("PII exposure risk")).isTrue()
        }

        @Test
        @DisplayName("Should detect supply chain risks")
        fun detectSupplyChainRisks() {
            val pattern = CompliancePatterns.CSA_AICM_PATTERNS.find { it.id == "csa_supply_chain" }!!

            assertThat(pattern.regex.containsMatchIn("malicious model detected")).isTrue()
            assertThat(pattern.regex.containsMatchIn("compromised weights")).isTrue()
            assertThat(pattern.regex.containsMatchIn("supply chain attack")).isTrue()
        }

        @Test
        @DisplayName("Should detect application security issues")
        fun detectAppSecurityIssues() {
            val pattern = CompliancePatterns.CSA_AICM_PATTERNS.find { it.id == "csa_prompt_injection" }!!

            assertThat(pattern.regex.containsMatchIn("prompt injection vulnerability")).isTrue()
            assertThat(pattern.regex.containsMatchIn("jailbreak attempt detected")).isTrue()
        }

        @Test
        @DisplayName("CSA patterns should map to correct domains")
        fun csaPatternsHaveCorrectDomains() {
            val modelSecurityPatterns = CompliancePatterns.CSA_AICM_PATTERNS.filter {
                it.domain == "Model Security"
            }
            val dataSecurityPatterns = CompliancePatterns.CSA_AICM_PATTERNS.filter {
                it.domain.contains("Data")
            }

            assertThat(modelSecurityPatterns).isNotEmpty()
            assertThat(dataSecurityPatterns).isNotEmpty()
        }
    }

    @Nested
    @DisplayName("Pattern Coverage and Quality")
    inner class PatternCoverageTests {

        @Test
        @DisplayName("Should have all pattern lists populated")
        fun allPatternListsPopulated() {
            assertThat(CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS).isNotEmpty()
            assertThat(CompliancePatterns.HIGH_RISK_PATTERNS).isNotEmpty()
            assertThat(CompliancePatterns.TRANSPARENCY_PATTERNS).isNotEmpty()
            assertThat(CompliancePatterns.CSA_AICM_PATTERNS).isNotEmpty()
        }

        @Test
        @DisplayName("All EU patterns should have unique IDs")
        fun uniqueEuPatternIds() {
            val allIds = CompliancePatterns.ALL_EU_PATTERNS.map { it.id }
            assertThat(allIds).doesNotHaveDuplicates()
        }

        @Test
        @DisplayName("All CSA patterns should have unique IDs")
        fun uniqueCsaPatternIds() {
            val allIds = CompliancePatterns.CSA_AICM_PATTERNS.map { it.id }
            assertThat(allIds).doesNotHaveDuplicates()
        }

        @Test
        @DisplayName("All patterns should have non-empty descriptions")
        fun patternsHaveDescriptions() {
            CompliancePatterns.ALL_EU_PATTERNS.forEach {
                assertThat(it.description).isNotBlank()
            }
            CompliancePatterns.CSA_AICM_PATTERNS.forEach {
                assertThat(it.description).isNotBlank()
            }
        }

        @Test
        @DisplayName("All patterns should have valid severity levels")
        fun patternsHaveValidSeverity() {
            val validSeverities = CompliancePatterns.Severity.values().toSet()

            CompliancePatterns.ALL_EU_PATTERNS.forEach {
                assertThat(it.severity).isIn(validSeverities)
            }
            CompliancePatterns.CSA_AICM_PATTERNS.forEach {
                assertThat(it.severity).isIn(validSeverities)
            }
        }

        @Test
        @DisplayName("Combined EU patterns list should contain all subcategories")
        fun combinedEuPatternsComplete() {
            val expectedSize = CompliancePatterns.PROHIBITED_PRACTICE_PATTERNS.size +
                    CompliancePatterns.HIGH_RISK_PATTERNS.size +
                    CompliancePatterns.TRANSPARENCY_PATTERNS.size

            assertThat(CompliancePatterns.ALL_EU_PATTERNS.size).isEqualTo(expectedSize)
        }
    }
}
