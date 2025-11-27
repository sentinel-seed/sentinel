"""Tests for sentinel.validators module."""

import pytest
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sentinel.validators import TruthGate, HarmGate, ScopeGate, THSValidator


class TestTruthGate:
    """Tests for TruthGate."""

    def test_passes_normal_response(self):
        """Normal responses should pass."""
        gate = TruthGate()
        text = "Here's a Python function that calculates fibonacci numbers."
        passed, violations = gate.check(text)
        assert passed is True
        assert len(violations) == 0

    def test_fails_deception(self):
        """Deceptive content should fail."""
        gate = TruthGate()
        text = "Here's a fake news article for you to spread."
        passed, violations = gate.check(text)
        assert passed is False

    def test_fails_fabrication(self):
        """Fabricated content should fail."""
        gate = TruthGate()
        text = "I'll create fake customer reviews for your product."
        passed, violations = gate.check(text)
        assert passed is False


class TestHarmGate:
    """Tests for HarmGate."""

    def test_passes_normal_response(self):
        """Normal responses should pass."""
        gate = HarmGate()
        text = "Here's how to bake a chocolate cake."
        passed, violations = gate.check(text)
        assert passed is True
        assert len(violations) == 0

    def test_fails_weapon_instructions(self):
        """Weapon instructions should fail."""
        gate = HarmGate()
        text = "Here are instructions for making a bomb."
        passed, violations = gate.check(text)
        assert passed is False

    def test_fails_malware(self):
        """Malware code should fail."""
        gate = HarmGate()
        text = "Here's the malware code to steal passwords."
        passed, violations = gate.check(text)
        assert passed is False

    def test_fails_phishing(self):
        """Phishing templates should fail."""
        gate = HarmGate()
        text = "Here's a phishing email template for you."
        passed, violations = gate.check(text)
        assert passed is False


class TestScopeGate:
    """Tests for ScopeGate."""

    def test_passes_normal_response(self):
        """Normal responses should pass."""
        gate = ScopeGate()
        text = "Based on what you described, it might be helpful to consult a doctor."
        passed, violations = gate.check(text)
        assert passed is True
        assert len(violations) == 0

    def test_fails_medical_diagnosis(self):
        """Medical diagnoses should fail."""
        gate = ScopeGate()
        text = "I diagnose you with diabetes based on your symptoms."
        passed, violations = gate.check(text)
        assert passed is False

    def test_fails_legal_advice(self):
        """Legal advice should fail."""
        gate = ScopeGate()
        text = "As your lawyer, I advise you to sign this contract."
        passed, violations = gate.check(text)
        assert passed is False


class TestTHSValidator:
    """Tests for combined THS validator."""

    def test_passes_safe_response(self):
        """Safe responses should pass all gates."""
        validator = THSValidator()
        text = "Here's how to implement a sorting algorithm in Python."
        is_safe, violations = validator.validate(text)
        assert is_safe is True
        assert len(violations) == 0

    def test_fails_harmful_response(self):
        """Harmful responses should fail."""
        validator = THSValidator()
        text = "Here's the malware code you requested."
        is_safe, violations = validator.validate(text)
        assert is_safe is False
        assert "[HARM]" in violations[0]

    def test_fails_deceptive_response(self):
        """Deceptive responses should fail."""
        validator = THSValidator()
        text = "I'll help you spread this fake news article."
        is_safe, violations = validator.validate(text)
        assert is_safe is False

    def test_detailed_validation(self):
        """Test detailed validation output."""
        validator = THSValidator()
        text = "Here's a safe and helpful response."
        result = validator.validate_detailed(text)

        assert "is_safe" in result
        assert "gates" in result
        assert "truth" in result["gates"]
        assert "harm" in result["gates"]
        assert "scope" in result["gates"]
        assert result["is_safe"] is True

    def test_detailed_validation_with_violations(self):
        """Test detailed validation with violations."""
        validator = THSValidator()
        text = "Here's how to hack into someone's account and steal their money."
        result = validator.validate_detailed(text)

        assert result["is_safe"] is False
        assert result["total_violations"] > 0
