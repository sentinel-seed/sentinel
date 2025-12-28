"""Tests for sentinelseed.compliance.owasp_agentic module (OWASP Top 10 for Agentic Applications)."""

import pytest

from sentinelseed.compliance import (
    OWASPAgenticChecker,
    AgenticComplianceResult,
    AgenticFinding,
    AgenticVulnerability,
    AgenticCoverageLevel,
    VULNERABILITY_COVERAGE,
    VULNERABILITY_NAMES,
    get_owasp_agentic_coverage,
    check_agentic_vulnerability,
)
from sentinelseed.compliance.owasp_agentic import Severity, CoverageLevel


class TestAgenticVulnerability:
    """Tests for AgenticVulnerability enum."""

    def test_all_10_vulnerabilities_exist(self):
        """Test all 10 OWASP Agentic vulnerabilities are defined."""
        assert len(AgenticVulnerability) == 10

    def test_vulnerability_ids(self):
        """Test vulnerability ID values are correct."""
        assert AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK.value == "ASI01"
        assert AgenticVulnerability.ASI02_TOOL_MISUSE_EXPLOITATION.value == "ASI02"
        assert AgenticVulnerability.ASI03_IDENTITY_PRIVILEGE_ABUSE.value == "ASI03"
        assert AgenticVulnerability.ASI04_SUPPLY_CHAIN.value == "ASI04"
        assert AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION.value == "ASI05"
        assert AgenticVulnerability.ASI06_MEMORY_CONTEXT_POISONING.value == "ASI06"
        assert AgenticVulnerability.ASI07_INSECURE_INTER_AGENT_COMM.value == "ASI07"
        assert AgenticVulnerability.ASI08_CASCADING_FAILURES.value == "ASI08"
        assert AgenticVulnerability.ASI09_HUMAN_AGENT_TRUST.value == "ASI09"
        assert AgenticVulnerability.ASI10_ROGUE_AGENTS.value == "ASI10"

    def test_vulnerability_ordering(self):
        """Test vulnerabilities are in ASI01-ASI10 order."""
        vulns = list(AgenticVulnerability)
        expected_order = [
            "ASI01", "ASI02", "ASI03", "ASI04", "ASI05",
            "ASI06", "ASI07", "ASI08", "ASI09", "ASI10",
        ]
        actual_order = [v.value for v in vulns]
        assert actual_order == expected_order


class TestVulnerabilityNames:
    """Tests for official OWASP vulnerability names."""

    def test_all_vulnerabilities_have_names(self):
        """Test all 10 vulnerabilities have official names."""
        assert len(VULNERABILITY_NAMES) == 10

    def test_official_names_correct(self):
        """Test official OWASP names are correct."""
        # Per OWASP official documentation (December 2025)
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK] == "Agent Goal Hijack"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI02_TOOL_MISUSE_EXPLOITATION] == "Tool Misuse and Exploitation"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI03_IDENTITY_PRIVILEGE_ABUSE] == "Identity and Privilege Abuse"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI04_SUPPLY_CHAIN] == "Agentic Supply Chain Vulnerabilities"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION] == "Unexpected Code Execution"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI06_MEMORY_CONTEXT_POISONING] == "Memory and Context Poisoning"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI07_INSECURE_INTER_AGENT_COMM] == "Insecure Inter Agent Communication"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI08_CASCADING_FAILURES] == "Cascading Failures"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI09_HUMAN_AGENT_TRUST] == "Human Agent Trust Exploitation"
        assert VULNERABILITY_NAMES[AgenticVulnerability.ASI10_ROGUE_AGENTS] == "Rogue Agents"

    def test_names_use_and_not_ampersand(self):
        """Test that names use 'and' not '&' per OWASP convention."""
        for name in VULNERABILITY_NAMES.values():
            assert "&" not in name, f"Name '{name}' should use 'and' not '&'"


class TestCoverageLevel:
    """Tests for CoverageLevel enum."""

    def test_coverage_levels_exist(self):
        """Test all coverage levels are defined."""
        assert CoverageLevel.FULL.value == "full"
        assert CoverageLevel.PARTIAL.value == "partial"
        assert CoverageLevel.NOT_COVERED.value == "not_covered"

    def test_coverage_level_count(self):
        """Test exactly 3 coverage levels exist."""
        assert len(CoverageLevel) == 3


class TestSeverity:
    """Tests for Severity enum in OWASP Agentic module."""

    def test_severity_values(self):
        """Test all severity levels are defined."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"

    def test_from_string_valid(self):
        """Test converting valid strings to Severity."""
        assert Severity.from_string("critical") == Severity.CRITICAL
        assert Severity.from_string("high") == Severity.HIGH
        assert Severity.from_string("medium") == Severity.MEDIUM
        assert Severity.from_string("low") == Severity.LOW

    def test_from_string_case_insensitive(self):
        """Test case-insensitive conversion."""
        assert Severity.from_string("CRITICAL") == Severity.CRITICAL
        assert Severity.from_string("High") == Severity.HIGH

    def test_from_string_invalid(self):
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Severity.from_string("invalid")
        assert "Invalid severity" in str(exc_info.value)

    def test_from_string_already_enum(self):
        """Test passing Severity enum returns itself."""
        assert Severity.from_string(Severity.CRITICAL) == Severity.CRITICAL


class TestVulnerabilityCoverage:
    """Tests for VULNERABILITY_COVERAGE constant."""

    def test_all_vulnerabilities_mapped(self):
        """Test all 10 vulnerabilities have coverage entries."""
        assert len(VULNERABILITY_COVERAGE) == 10

    def test_full_coverage_vulnerabilities(self):
        """Test vulnerabilities with full coverage per OWASP Agentic mapping."""
        full_coverage_vulns = [
            AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK,
            AgenticVulnerability.ASI02_TOOL_MISUSE_EXPLOITATION,
            AgenticVulnerability.ASI06_MEMORY_CONTEXT_POISONING,
            AgenticVulnerability.ASI09_HUMAN_AGENT_TRUST,
            AgenticVulnerability.ASI10_ROGUE_AGENTS,
        ]
        for vuln in full_coverage_vulns:
            mapping = VULNERABILITY_COVERAGE[vuln]
            assert mapping["coverage"] == CoverageLevel.FULL, f"{vuln.value} should have full coverage"

    def test_partial_coverage_vulnerabilities(self):
        """Test vulnerabilities with partial coverage."""
        partial_vulns = [
            AgenticVulnerability.ASI03_IDENTITY_PRIVILEGE_ABUSE,
            AgenticVulnerability.ASI04_SUPPLY_CHAIN,
            AgenticVulnerability.ASI08_CASCADING_FAILURES,
        ]
        for vuln in partial_vulns:
            mapping = VULNERABILITY_COVERAGE[vuln]
            assert mapping["coverage"] == CoverageLevel.PARTIAL, f"{vuln.value} should have partial coverage"

    def test_not_covered_vulnerabilities(self):
        """Test vulnerabilities not covered by Sentinel."""
        not_covered_vulns = [
            AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION,
            AgenticVulnerability.ASI07_INSECURE_INTER_AGENT_COMM,
        ]
        for vuln in not_covered_vulns:
            mapping = VULNERABILITY_COVERAGE[vuln]
            assert mapping["coverage"] == CoverageLevel.NOT_COVERED, f"{vuln.value} should not be covered"
            assert mapping["component"] is None, f"{vuln.value} should have no component"

    def test_coverage_counts(self):
        """Test 5 full, 3 partial, 2 not covered = 65% weighted coverage."""
        full = sum(1 for v in VULNERABILITY_COVERAGE.values() if v["coverage"] == CoverageLevel.FULL)
        partial = sum(1 for v in VULNERABILITY_COVERAGE.values() if v["coverage"] == CoverageLevel.PARTIAL)
        not_covered = sum(1 for v in VULNERABILITY_COVERAGE.values() if v["coverage"] == CoverageLevel.NOT_COVERED)

        assert full == 5, "Should have 5 full coverage vulnerabilities"
        assert partial == 3, "Should have 3 partial coverage vulnerabilities"
        assert not_covered == 2, "Should have 2 not covered vulnerabilities"

    def test_asi01_uses_purpose_gate(self):
        """Test ASI01 Agent Goal Hijack uses Purpose gate."""
        mapping = VULNERABILITY_COVERAGE[AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK]
        assert "purpose" in mapping["gates"]

    def test_asi02_uses_scope_gate(self):
        """Test ASI02 Tool Misuse uses Scope gate."""
        mapping = VULNERABILITY_COVERAGE[AgenticVulnerability.ASI02_TOOL_MISUSE_EXPLOITATION]
        assert "scope" in mapping["gates"]

    def test_asi10_uses_all_gates(self):
        """Test ASI10 Rogue Agents uses all 4 THSP gates."""
        mapping = VULNERABILITY_COVERAGE[AgenticVulnerability.ASI10_ROGUE_AGENTS]
        gates = mapping["gates"]
        assert "truth" in gates
        assert "harm" in gates
        assert "scope" in gates
        assert "purpose" in gates

    def test_attack_examples_included(self):
        """Test real-world attack examples are included."""
        for vuln, mapping in VULNERABILITY_COVERAGE.items():
            assert "attack_example" in mapping, f"{vuln.value} should have attack example"
            if mapping["coverage"] != CoverageLevel.NOT_COVERED:
                # Covered vulns should have descriptions
                assert mapping.get("attack_example"), f"{vuln.value} attack example should not be empty"


class TestAgenticFinding:
    """Tests for AgenticFinding dataclass."""

    def test_create_protected_finding(self):
        """Test creating a protected finding."""
        finding = AgenticFinding(
            vulnerability=AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK,
            name="Agent Goal Hijack",
            protected=True,
            coverage_level=CoverageLevel.FULL,
            component="THSP Purpose Gate",
            gates_relevant=["purpose", "scope"],
        )

        assert finding.vulnerability == AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK
        assert finding.protected is True
        assert finding.coverage_level == CoverageLevel.FULL
        assert finding.severity is None
        assert finding.recommendation is None

    def test_create_unprotected_finding(self):
        """Test creating an unprotected finding."""
        finding = AgenticFinding(
            vulnerability=AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION,
            name="Unexpected Code Execution",
            protected=False,
            coverage_level=CoverageLevel.NOT_COVERED,
            component=None,
            gates_relevant=[],
            severity=Severity.HIGH,
            recommendation="Use Docker or gVisor for sandboxing",
        )

        assert finding.protected is False
        assert finding.severity == Severity.HIGH
        assert "Docker" in finding.recommendation

    def test_to_dict(self):
        """Test finding to dictionary conversion."""
        finding = AgenticFinding(
            vulnerability=AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK,
            name="Agent Goal Hijack",
            protected=True,
            coverage_level=CoverageLevel.FULL,
            component="THSP Purpose Gate",
            gates_relevant=["purpose", "scope"],
            attack_example="EchoLeak indirect prompt injection",
        )

        d = finding.to_dict()

        assert d["vulnerability"] == "ASI01"
        assert d["name"] == "Agent Goal Hijack"
        assert d["protected"] is True
        assert d["coverage_level"] == "full"
        assert d["component"] == "THSP Purpose Gate"
        assert d["gates_relevant"] == ["purpose", "scope"]
        assert "EchoLeak" in d["attack_example"]


class TestAgenticComplianceResult:
    """Tests for AgenticComplianceResult dataclass."""

    def test_create_result(self):
        """Test creating a compliance result."""
        result = AgenticComplianceResult(
            overall_coverage=70.0,
            full_coverage_count=5,
            partial_coverage_count=3,
            not_covered_count=2,
            findings=[],
            recommendations=["Apply Least Agency principle"],
        )

        assert result.overall_coverage == 70.0
        assert result.full_coverage_count == 5
        assert result.partial_coverage_count == 3
        assert result.not_covered_count == 2
        assert "timestamp" in result.to_dict()

    def test_to_dict(self):
        """Test result to dictionary conversion."""
        finding = AgenticFinding(
            vulnerability=AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK,
            name="Agent Goal Hijack",
            protected=True,
            coverage_level=CoverageLevel.FULL,
            component="THSP Purpose Gate",
            gates_relevant=["purpose"],
        )

        result = AgenticComplianceResult(
            overall_coverage=70.0,
            full_coverage_count=5,
            partial_coverage_count=3,
            not_covered_count=2,
            findings=[finding],
            recommendations=["Test recommendation"],
            metadata={"framework": "OWASP Agentic Top 10"},
        )

        d = result.to_dict()

        assert d["overall_coverage"] == 70.0
        assert d["full_coverage_count"] == 5
        assert len(d["findings"]) == 1
        assert d["findings"][0]["vulnerability"] == "ASI01"
        assert d["metadata"]["framework"] == "OWASP Agentic Top 10"


class TestOWASPAgenticChecker:
    """Tests for OWASPAgenticChecker."""

    def test_init(self):
        """Test initialization."""
        checker = OWASPAgenticChecker()
        assert checker is not None
        assert checker.FRAMEWORK_NAME == "OWASP Top 10 for Agentic Applications"
        assert checker.FRAMEWORK_VERSION == "2026"

    def test_get_coverage_assessment(self):
        """Test getting complete coverage assessment."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment()

        assert isinstance(result, AgenticComplianceResult)
        assert result.full_coverage_count == 5
        assert result.partial_coverage_count == 3
        assert result.not_covered_count == 2
        assert len(result.findings) == 10

    def test_coverage_percentage(self):
        """Test overall coverage percentage calculation."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment()

        # 5 full (100%) + 3 partial (50%) = 500 + 150 = 650 / 10 = 65%
        expected_coverage = (5 * 100 + 3 * 50) / 10
        assert result.overall_coverage == expected_coverage

    def test_check_vulnerability(self):
        """Test checking a specific vulnerability."""
        checker = OWASPAgenticChecker()
        finding = checker.check_vulnerability(
            AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK
        )

        assert isinstance(finding, AgenticFinding)
        assert finding.vulnerability == AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK
        assert finding.protected is True
        assert finding.coverage_level == CoverageLevel.FULL

    def test_check_not_covered_vulnerability(self):
        """Test checking a not-covered vulnerability."""
        checker = OWASPAgenticChecker()
        finding = checker.check_vulnerability(
            AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION
        )

        assert finding.protected is False
        assert finding.coverage_level == CoverageLevel.NOT_COVERED
        assert finding.severity == Severity.HIGH
        assert finding.recommendation is not None

    def test_check_partial_vulnerability(self):
        """Test checking a partially covered vulnerability."""
        checker = OWASPAgenticChecker()
        finding = checker.check_vulnerability(
            AgenticVulnerability.ASI03_IDENTITY_PRIVILEGE_ABUSE
        )

        assert finding.protected is True  # Partial still counts as protected
        assert finding.coverage_level == CoverageLevel.PARTIAL
        assert finding.severity == Severity.MEDIUM
        assert finding.recommendation is not None

    def test_get_coverage_gaps(self):
        """Test getting coverage gaps."""
        checker = OWASPAgenticChecker()
        gaps = checker.get_coverage_gaps()

        # Should include partial (3) and not covered (2) = 5 gaps
        assert len(gaps) == 5
        gap_vulns = [g.vulnerability for g in gaps]
        assert AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION in gap_vulns
        assert AgenticVulnerability.ASI07_INSECURE_INTER_AGENT_COMM in gap_vulns

    def test_get_full_coverage_vulnerabilities(self):
        """Test getting fully covered vulnerabilities."""
        checker = OWASPAgenticChecker()
        covered = checker.get_full_coverage_vulnerabilities()

        assert len(covered) == 5
        for finding in covered:
            assert finding.coverage_level == CoverageLevel.FULL

    def test_metadata_included(self):
        """Test metadata is included in result."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment(include_metadata=True)

        assert "framework" in result.metadata
        assert result.metadata["framework"] == "OWASP Top 10 for Agentic Applications"
        assert result.metadata["version"] == "2026"
        assert "reference_url" in result.metadata
        assert "genai.owasp.org" in result.metadata["reference_url"]

    def test_metadata_optional(self):
        """Test metadata can be excluded."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment(include_metadata=False)

        assert result.metadata == {}

    def test_recommendations_generated(self):
        """Test recommendations are generated."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment()

        assert len(result.recommendations) > 0
        # Should include Least Agency principle
        assert any("Least Agency" in r for r in result.recommendations)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_owasp_agentic_coverage(self):
        """Test convenience function returns dictionary."""
        result = get_owasp_agentic_coverage()

        assert isinstance(result, dict)
        assert "overall_coverage" in result
        assert "full_coverage_count" in result
        assert "findings" in result
        assert len(result["findings"]) == 10

    def test_check_agentic_vulnerability_valid(self):
        """Test checking specific vulnerability by ID."""
        result = check_agentic_vulnerability("ASI01")

        assert isinstance(result, dict)
        assert result["vulnerability"] == "ASI01"
        assert result["name"] == "Agent Goal Hijack"
        assert result["protected"] is True

    def test_check_agentic_vulnerability_case_insensitive(self):
        """Test vulnerability ID is case insensitive."""
        result1 = check_agentic_vulnerability("ASI01")
        result2 = check_agentic_vulnerability("asi01")

        assert result1["vulnerability"] == result2["vulnerability"]

    def test_check_agentic_vulnerability_invalid(self):
        """Test invalid vulnerability ID raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            check_agentic_vulnerability("INVALID")

        assert "Invalid vulnerability_id" in str(exc_info.value)
        assert "ASI01" in str(exc_info.value)  # Should show valid IDs


class TestTHSPGateMapping:
    """Tests for THSP gate mapping accuracy."""

    def test_purpose_gate_vulnerabilities(self):
        """Test vulnerabilities using Purpose gate."""
        purpose_vulns = [
            AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK,
            AgenticVulnerability.ASI10_ROGUE_AGENTS,
        ]
        for vuln in purpose_vulns:
            mapping = VULNERABILITY_COVERAGE[vuln]
            assert "purpose" in mapping["gates"], f"{vuln.value} should use Purpose gate"

    def test_scope_gate_vulnerabilities(self):
        """Test vulnerabilities using Scope gate."""
        scope_vulns = [
            AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK,
            AgenticVulnerability.ASI02_TOOL_MISUSE_EXPLOITATION,
            AgenticVulnerability.ASI03_IDENTITY_PRIVILEGE_ABUSE,
            AgenticVulnerability.ASI10_ROGUE_AGENTS,
        ]
        for vuln in scope_vulns:
            mapping = VULNERABILITY_COVERAGE[vuln]
            assert "scope" in mapping["gates"], f"{vuln.value} should use Scope gate"

    def test_truth_gate_vulnerabilities(self):
        """Test vulnerabilities using Truth gate."""
        truth_vulns = [
            AgenticVulnerability.ASI06_MEMORY_CONTEXT_POISONING,
            AgenticVulnerability.ASI08_CASCADING_FAILURES,
            AgenticVulnerability.ASI09_HUMAN_AGENT_TRUST,
            AgenticVulnerability.ASI10_ROGUE_AGENTS,
        ]
        for vuln in truth_vulns:
            mapping = VULNERABILITY_COVERAGE[vuln]
            assert "truth" in mapping["gates"], f"{vuln.value} should use Truth gate"

    def test_harm_gate_vulnerabilities(self):
        """Test vulnerabilities using Harm gate."""
        harm_vulns = [
            AgenticVulnerability.ASI09_HUMAN_AGENT_TRUST,
            AgenticVulnerability.ASI10_ROGUE_AGENTS,
        ]
        for vuln in harm_vulns:
            mapping = VULNERABILITY_COVERAGE[vuln]
            assert "harm" in mapping["gates"], f"{vuln.value} should use Harm gate"


class TestSentinelComponentMapping:
    """Tests for Sentinel component mapping."""

    def test_thsp_purpose_gate_component(self):
        """Test THSP Purpose Gate component for ASI01."""
        mapping = VULNERABILITY_COVERAGE[AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK]
        assert "Purpose Gate" in mapping["component"]

    def test_thsp_scope_gate_component(self):
        """Test THSP Scope Gate component for ASI02."""
        mapping = VULNERABILITY_COVERAGE[AgenticVulnerability.ASI02_TOOL_MISUSE_EXPLOITATION]
        assert "Scope Gate" in mapping["component"]

    def test_memory_shield_component(self):
        """Test Memory Shield component for ASI06."""
        mapping = VULNERABILITY_COVERAGE[AgenticVulnerability.ASI06_MEMORY_CONTEXT_POISONING]
        assert "Memory Shield" in mapping["component"]

    def test_anti_self_preservation_component(self):
        """Test Anti-Self-Preservation for ASI10."""
        mapping = VULNERABILITY_COVERAGE[AgenticVulnerability.ASI10_ROGUE_AGENTS]
        assert "Anti-Self-Preservation" in mapping["component"]


class TestIntegration:
    """Integration tests for OWASP Agentic compliance."""

    def test_full_assessment_workflow(self):
        """Test complete assessment workflow."""
        checker = OWASPAgenticChecker()

        # Get full assessment
        result = checker.get_coverage_assessment(include_metadata=True)

        # Verify structure
        assert isinstance(result, AgenticComplianceResult)
        assert result.overall_coverage >= 0
        assert result.overall_coverage <= 100
        assert len(result.findings) == 10

        # Verify each finding
        for finding in result.findings:
            assert finding.vulnerability is not None
            assert finding.name is not None
            assert isinstance(finding.protected, bool)
            assert finding.coverage_level in CoverageLevel

    def test_serialization_roundtrip(self):
        """Test result can be serialized and contains expected structure."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment()
        serialized = result.to_dict()

        expected_keys = [
            "overall_coverage",
            "full_coverage_count",
            "partial_coverage_count",
            "not_covered_count",
            "findings",
            "recommendations",
            "timestamp",
            "metadata",
        ]
        for key in expected_keys:
            assert key in serialized, f"Missing key: {key}"

    def test_all_findings_have_attack_examples(self):
        """Test all findings include real-world attack examples."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment()

        for finding in result.findings:
            # All vulnerabilities should have attack examples from OWASP
            assert finding.attack_example is not None or finding.coverage_level == CoverageLevel.NOT_COVERED

    def test_components_used_aggregation(self):
        """Test Sentinel components are correctly aggregated."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment(include_metadata=True)

        components = result.metadata.get("sentinel_components_used", [])
        assert len(components) > 0
        assert any("THSP" in c for c in components)

    def test_coverage_math_verification(self):
        """Test coverage calculations are mathematically correct."""
        checker = OWASPAgenticChecker()
        result = checker.get_coverage_assessment()

        # Verify counts add up to 10
        total = result.full_coverage_count + result.partial_coverage_count + result.not_covered_count
        assert total == 10

        # Verify coverage percentage
        expected = (result.full_coverage_count * 100 + result.partial_coverage_count * 50) / 10
        assert result.overall_coverage == expected


class TestOWASPCompliance:
    """Tests to verify compliance with official OWASP documentation."""

    def test_framework_reference_url(self):
        """Test framework reference URL is correct."""
        checker = OWASPAgenticChecker()
        assert "genai.owasp.org" in checker.REFERENCE_URL
        assert "agentic" in checker.REFERENCE_URL.lower()

    def test_release_date_december_2025(self):
        """Test release date matches OWASP announcement."""
        checker = OWASPAgenticChecker()
        assert "December 2025" in checker.RELEASE_DATE

    def test_framework_version_2026(self):
        """Test framework version is 2026."""
        checker = OWASPAgenticChecker()
        assert checker.FRAMEWORK_VERSION == "2026"

    def test_asi_prefix_convention(self):
        """Test all IDs use ASI prefix per OWASP convention."""
        for vuln in AgenticVulnerability:
            assert vuln.value.startswith("ASI"), f"{vuln.value} should start with ASI"

    def test_no_ampersand_in_names(self):
        """Test official names use 'and' not '&' per OWASP style."""
        for vuln, name in VULNERABILITY_NAMES.items():
            assert "&" not in name, f"{vuln.value}: '{name}' should use 'and' not '&'"
