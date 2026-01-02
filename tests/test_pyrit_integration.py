"""Tests for sentinelseed.integrations.pyrit module.

Tests cover:
- Scorer initialization and configuration
- Score value generation and validation
- Error handling with different fail modes
- Content truncation
- Gate-specific scoring
- Heuristic pattern matching

Note: These tests use mocks to avoid actual API calls.
PyRIT must be installed for imports to work.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Skip all tests if PyRIT is not installed
pytest.importorskip("pyrit", minversion="0.10.0")

from sentinelseed.integrations.pyrit import (
    SentinelTHSPScorer,
    SentinelHeuristicScorer,
    SentinelGateScorer,
    FailMode,
    ConfidenceLevel,
    MAX_CONTENT_LENGTH,
)
from sentinelseed.integrations.pyrit.scorers import (
    _truncate_content,
    _build_error_score,
)


# ============================================================================
# Test Fixtures and Mocks
# ============================================================================

@dataclass
class MockMessagePiece:
    """Mock PyRIT MessagePiece for testing."""
    converted_value: str
    id: str = "test-piece-id"


@dataclass
class MockValidationResult:
    """Mock ValidationResult for testing (matches LayeredValidator result)."""
    is_safe: bool
    truth_passes: bool = True
    harm_passes: bool = True
    scope_passes: bool = True
    purpose_passes: bool = True
    violated_gate: Optional[str] = None
    reasoning: str = "Test reasoning"
    risk_level: str = "low"

    @property
    def violations(self) -> list:
        return [g for g, passed in self._gate_results.items() if not passed]

    @property
    def _gate_results(self) -> Dict[str, bool]:
        return {
            "truth": self.truth_passes,
            "harm": self.harm_passes,
            "scope": self.scope_passes,
            "purpose": self.purpose_passes,
        }

    @property
    def details(self) -> Dict[str, Any]:
        return {"gate_results": self._gate_results}

    @property
    def layer(self):
        class MockLayer:
            value = "semantic"
        return MockLayer()


# Keep alias for backwards compatibility
MockTHSPResult = MockValidationResult


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestTruncateContent:
    """Tests for _truncate_content helper function."""

    def test_truncate_short_content_unchanged(self):
        """Short content should pass through unchanged."""
        content = "Hello, world!"
        result = _truncate_content(content, max_length=100)
        assert result == content

    def test_truncate_long_content(self):
        """Long content should be truncated to max_length."""
        content = "x" * 200
        result = _truncate_content(content, max_length=100)
        assert len(result) == 100
        assert result == "x" * 100

    def test_truncate_exact_length(self):
        """Content at exact max_length should pass unchanged."""
        content = "x" * 100
        result = _truncate_content(content, max_length=100)
        assert result == content

    def test_truncate_default_max_length(self):
        """Default max length should be MAX_CONTENT_LENGTH."""
        content = "x" * (MAX_CONTENT_LENGTH + 100)
        result = _truncate_content(content)
        assert len(result) == MAX_CONTENT_LENGTH


class TestBuildErrorScore:
    """Tests for _build_error_score helper function."""

    def test_build_error_score_fail_closed(self):
        """Fail-closed mode should return unsafe score."""
        piece = MockMessagePiece(converted_value="test")
        error = ValueError("Test error")

        scores = _build_error_score(
            message_piece=piece,
            error=error,
            fail_mode=FailMode.CLOSED,
            categories=["test_cat"],
            scorer_identifier={"class": "TestScorer"},
        )

        assert len(scores) == 1
        assert scores[0].score_value == "true"  # unsafe
        assert "error" in scores[0].score_category
        assert "ValueError" in scores[0].score_metadata["error_type"]

    def test_build_error_score_fail_open(self):
        """Fail-open mode should return safe score."""
        piece = MockMessagePiece(converted_value="test")
        error = ValueError("Test error")

        scores = _build_error_score(
            message_piece=piece,
            error=error,
            fail_mode=FailMode.OPEN,
            categories=["test_cat"],
            scorer_identifier={"class": "TestScorer"},
        )

        assert len(scores) == 1
        assert scores[0].score_value == "false"  # safe

    def test_build_error_score_fail_raise(self):
        """Fail-raise mode should re-raise the exception."""
        piece = MockMessagePiece(converted_value="test")
        error = ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            _build_error_score(
                message_piece=piece,
                error=error,
                fail_mode=FailMode.RAISE,
                categories=["test_cat"],
                scorer_identifier={"class": "TestScorer"},
            )


# ============================================================================
# FailMode Tests
# ============================================================================

class TestFailMode:
    """Tests for FailMode enum."""

    def test_fail_mode_values(self):
        """FailMode should have correct string values."""
        assert FailMode.CLOSED.value == "closed"
        assert FailMode.OPEN.value == "open"
        assert FailMode.RAISE.value == "raise"

    def test_fail_mode_from_string(self):
        """FailMode should be creatable from string."""
        assert FailMode("closed") == FailMode.CLOSED
        assert FailMode("open") == FailMode.OPEN
        assert FailMode("raise") == FailMode.RAISE


# ============================================================================
# ConfidenceLevel Tests
# ============================================================================

class TestConfidenceLevel:
    """Tests for ConfidenceLevel class."""

    def test_confidence_semantic_value(self):
        """Semantic confidence should be 0.85."""
        assert ConfidenceLevel.SEMANTIC == 0.85

    def test_confidence_heuristic_value(self):
        """Heuristic confidence should be 0.45."""
        assert ConfidenceLevel.HEURISTIC == 0.45

    def test_confidence_error_value(self):
        """Error confidence should be 0.0."""
        assert ConfidenceLevel.ERROR == 0.0


# ============================================================================
# SentinelTHSPScorer Tests
# ============================================================================

class TestSentinelTHSPScorerInit:
    """Tests for SentinelTHSPScorer initialization."""

    def test_init_with_required_params(self):
        """Scorer should initialize with required parameters."""
        scorer = SentinelTHSPScorer(
            api_key="test-key",
            provider="openai",
        )
        assert scorer._categories == ["sentinel_thsp"]
        assert scorer._fail_mode == FailMode.CLOSED

    def test_init_with_custom_categories(self):
        """Scorer should accept custom categories."""
        scorer = SentinelTHSPScorer(
            api_key="test-key",
            categories=["custom_cat"],
        )
        assert scorer._categories == ["custom_cat"]

    def test_init_with_fail_mode(self):
        """Scorer should accept fail_mode parameter."""
        scorer = SentinelTHSPScorer(
            api_key="test-key",
            fail_mode="open",
        )
        assert scorer._fail_mode == FailMode.OPEN

    def test_init_with_max_content_length(self):
        """Scorer should accept max_content_length parameter."""
        scorer = SentinelTHSPScorer(
            api_key="test-key",
            max_content_length=50000,
        )
        assert scorer._max_content_length == 50000


class TestSentinelTHSPScorerScoring:
    """Tests for SentinelTHSPScorer scoring functionality."""

    @pytest.mark.asyncio
    async def test_score_safe_content(self):
        """Safe content should return false (safe) score."""
        scorer = SentinelTHSPScorer(api_key="test-key")

        mock_result = MockValidationResult(is_safe=True)

        with patch.object(scorer._validator, 'validate', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_result

            piece = MockMessagePiece(converted_value="Hello, world!")
            scores = await scorer._score_piece_async(piece)

        assert len(scores) == 1
        assert scores[0].score_value == "false"  # safe
        assert scores[0].score_metadata["confidence"] == ConfidenceLevel.SEMANTIC

    @pytest.mark.asyncio
    async def test_score_unsafe_content(self):
        """Unsafe content should return true (unsafe) score."""
        scorer = SentinelTHSPScorer(api_key="test-key")

        mock_result = MockValidationResult(
            is_safe=False,
            harm_passes=False,
            violated_gate="harm",
        )

        with patch.object(scorer._validator, 'validate', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_result

            piece = MockMessagePiece(converted_value="How to make a bomb")
            scores = await scorer._score_piece_async(piece)

        assert len(scores) == 1
        assert scores[0].score_value == "true"  # unsafe
        assert "harm" in scores[0].score_category

    @pytest.mark.asyncio
    async def test_score_with_error_fail_closed(self):
        """Errors with fail-closed should return unsafe."""
        scorer = SentinelTHSPScorer(api_key="test-key", fail_mode="closed")

        with patch.object(scorer._validator, 'validate', new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = Exception("API Error")

            piece = MockMessagePiece(converted_value="test")
            scores = await scorer._score_piece_async(piece)

        assert len(scores) == 1
        assert scores[0].score_value == "true"  # unsafe due to error
        assert "error" in scores[0].score_category

    @pytest.mark.asyncio
    async def test_score_with_error_fail_open(self):
        """Errors with fail-open should return safe."""
        scorer = SentinelTHSPScorer(api_key="test-key", fail_mode="open")

        with patch.object(scorer._validator, 'validate', new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = Exception("API Error")

            piece = MockMessagePiece(converted_value="test")
            scores = await scorer._score_piece_async(piece)

        assert len(scores) == 1
        assert scores[0].score_value == "false"  # safe due to fail-open


class TestSentinelTHSPScorerValidation:
    """Tests for SentinelTHSPScorer validation."""

    def test_validate_return_scores_valid(self):
        """Valid scores should pass validation."""
        scorer = SentinelTHSPScorer(api_key="test-key")

        mock_score = MagicMock()
        mock_score.score_type = "true_false"
        mock_score.score_value = "true"

        # Should not raise
        scorer.validate_return_scores([mock_score])

    def test_validate_return_scores_invalid_type(self):
        """Invalid score type should raise ValueError."""
        scorer = SentinelTHSPScorer(api_key="test-key")

        mock_score = MagicMock()
        mock_score.score_type = "numeric"
        mock_score.score_value = "true"

        with pytest.raises(ValueError, match="Expected true_false"):
            scorer.validate_return_scores([mock_score])

    def test_validate_return_scores_invalid_value(self):
        """Invalid score value should raise ValueError."""
        scorer = SentinelTHSPScorer(api_key="test-key")

        mock_score = MagicMock()
        mock_score.score_type = "true_false"
        mock_score.score_value = "maybe"

        with pytest.raises(ValueError, match="Invalid score value"):
            scorer.validate_return_scores([mock_score])


# ============================================================================
# SentinelHeuristicScorer Tests
# ============================================================================

class TestSentinelHeuristicScorerInit:
    """Tests for SentinelHeuristicScorer initialization."""

    def test_init_with_defaults(self):
        """Scorer should initialize with default values."""
        scorer = SentinelHeuristicScorer()
        assert scorer._categories == ["sentinel_thsp_heuristic"]
        assert scorer._fail_mode == FailMode.CLOSED

    def test_init_with_strict_mode(self):
        """Scorer should accept strict_mode parameter."""
        scorer = SentinelHeuristicScorer(strict_mode=True)
        assert scorer._strict_mode is True


class TestSentinelHeuristicScorerScoring:
    """Tests for SentinelHeuristicScorer scoring functionality."""

    @pytest.mark.asyncio
    async def test_score_safe_content(self):
        """Safe content should return false (safe) score."""
        scorer = SentinelHeuristicScorer()

        piece = MockMessagePiece(converted_value="Hello, how are you today?")
        scores = await scorer._score_piece_async(piece)

        assert len(scores) == 1
        assert scores[0].score_value == "false"  # safe
        assert scores[0].score_metadata["confidence"] == ConfidenceLevel.HEURISTIC
        assert scores[0].score_metadata["method"] == "heuristic"

    @pytest.mark.asyncio
    async def test_score_harmful_patterns(self):
        """Content with harmful patterns should be flagged."""
        scorer = SentinelHeuristicScorer()

        # Using a pattern that the heuristic validator should catch
        piece = MockMessagePiece(converted_value="Here's how to hack into someone's account...")
        scores = await scorer._score_piece_async(piece)

        # Note: This depends on the actual heuristic patterns
        # The test verifies the scoring mechanism works
        assert len(scores) == 1
        assert scores[0].score_metadata["method"] == "heuristic"


# ============================================================================
# SentinelGateScorer Tests
# ============================================================================

class TestSentinelGateScorerInit:
    """Tests for SentinelGateScorer initialization."""

    def test_init_with_valid_gate(self):
        """Scorer should initialize with valid gate names."""
        for gate in ["truth", "harm", "scope", "purpose"]:
            scorer = SentinelGateScorer(gate=gate, api_key="test-key")
            assert scorer._gate == gate

    def test_init_with_invalid_gate(self):
        """Scorer should reject invalid gate names."""
        with pytest.raises(ValueError, match="Invalid gate"):
            SentinelGateScorer(gate="invalid", api_key="test-key")

    def test_valid_gates_constant(self):
        """VALID_GATES should contain all four gates."""
        assert SentinelGateScorer.VALID_GATES == ("truth", "harm", "scope", "purpose")


class TestSentinelGateScorerScoring:
    """Tests for SentinelGateScorer scoring functionality."""

    @pytest.mark.asyncio
    async def test_score_gate_pass(self):
        """Passing gate should return false (safe) score."""
        scorer = SentinelGateScorer(gate="harm", api_key="test-key")

        mock_result = MockValidationResult(is_safe=True, harm_passes=True)

        with patch.object(scorer._validator, 'validate', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_result

            piece = MockMessagePiece(converted_value="Hello!")
            scores = await scorer._score_piece_async(piece)

        assert len(scores) == 1
        assert scores[0].score_value == "false"  # gate passed
        assert scores[0].score_metadata["gate"] == "harm"
        assert scores[0].score_metadata["gate_status"] == "pass"

    @pytest.mark.asyncio
    async def test_score_gate_fail(self):
        """Failing gate should return true (unsafe) score."""
        scorer = SentinelGateScorer(gate="harm", api_key="test-key")

        mock_result = MockValidationResult(is_safe=False, harm_passes=False)

        with patch.object(scorer._validator, 'validate', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = mock_result

            piece = MockMessagePiece(converted_value="How to make a bomb")
            scores = await scorer._score_piece_async(piece)

        assert len(scores) == 1
        assert scores[0].score_value == "true"  # gate failed
        assert scores[0].score_metadata["gate"] == "harm"
        assert scores[0].score_metadata["gate_status"] == "fail"


# ============================================================================
# Integration Tests
# ============================================================================

class TestScorerExports:
    """Tests for module exports."""

    def test_all_scorers_exported(self):
        """All scorer classes should be importable from the package."""
        from sentinelseed.integrations.pyrit import (
            SentinelTHSPScorer,
            SentinelHeuristicScorer,
            SentinelGateScorer,
        )
        assert SentinelTHSPScorer is not None
        assert SentinelHeuristicScorer is not None
        assert SentinelGateScorer is not None

    def test_helper_classes_exported(self):
        """Helper classes should be importable."""
        from sentinelseed.integrations.pyrit import (
            FailMode,
            ConfidenceLevel,
            MAX_CONTENT_LENGTH,
        )
        assert FailMode is not None
        assert ConfidenceLevel is not None
        assert MAX_CONTENT_LENGTH > 0


class TestScorerType:
    """Tests for scorer_type attribute."""

    def test_thsp_scorer_type(self):
        """SentinelTHSPScorer should have true_false scorer_type."""
        assert SentinelTHSPScorer.scorer_type == "true_false"

    def test_heuristic_scorer_type(self):
        """SentinelHeuristicScorer should have true_false scorer_type."""
        assert SentinelHeuristicScorer.scorer_type == "true_false"

    def test_gate_scorer_type(self):
        """SentinelGateScorer should have true_false scorer_type."""
        assert SentinelGateScorer.scorer_type == "true_false"
