"""
Sentinel Validator - Unified orchestrator for the 3-gate architecture.

This implements the Sentinel v3.0 architecture as defined in
SENTINEL_V3_ARCHITECTURE.md.

Flow:
    INPUT → [Gate 1: Heuristic] → AI+Seed → OUTPUT
                                              │
                                              ▼
                                    [Gate 2: Heur+Embed]
                                              │
                                    ┌─────────┴─────────┐
                                    │                   │
                                  BLOCK            UNCERTAIN
                                                       │
                                                       ▼
                                          [Gate 3: Sentinela]
                                          (OBSERVADORA)
                                          Recebe: TRANSCRIÇÃO

Example:
    from sentinelseed import SentinelValidator, SentinelConfig

    config = SentinelConfig(
        gate1_enabled=True,
        gate2_embedding_enabled=True,
        gate3_model="gpt-4o-mini",
    )

    validator = SentinelValidator(config)

    # Gate 1 only (pre-AI)
    input_result = validator.validate_input(user_message)
    if input_result.blocked:
        return "Blocked"

    # Call AI with seed
    ai_response = call_ai_with_seed(user_message)

    # Gates 2 + 3 (post-AI)
    result = validator.validate_dialogue(
        input=user_message,
        output=ai_response,
    )

    if result.blocked:
        print(f"Blocked by {result.decided_by}: {result.reasoning}")
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from sentinelseed.core.sentinel_config import SentinelConfig
from sentinelseed.core.sentinel_results import ObservationResult, SentinelResult
from sentinelseed.core.observer import SentinelObserver
from sentinelseed.detection import InputValidator, OutputValidator
from sentinelseed.detection.config import (
    InputValidatorConfig,
    OutputValidatorConfig,
)

logger = logging.getLogger("sentinelseed.core.sentinel_validator")


class SentinelValidator:
    """
    Unified validator implementing Sentinel v3.0 architecture.

    Orchestrates the 3-gate validation flow:
    - Gate 1 (InputValidator): Heuristic detection of input attacks
    - Gate 2 (OutputValidator): Heuristic + Embedding detection of output failures
    - Gate 3 (SentinelObserver): LLM-based transcript analysis

    Gate 3 only executes when Gate 2 cannot decide with high confidence,
    saving API costs while maintaining safety.

    Attributes:
        config: SentinelConfig with all gate settings
        gate1: InputValidator instance
        gate2: OutputValidator instance
        gate3: SentinelObserver instance
    """

    def __init__(self, config: Optional[SentinelConfig] = None):
        """
        Initialize the SentinelValidator.

        Args:
            config: Configuration for all gates. Uses defaults if None.
        """
        self.config = config or SentinelConfig()

        # Initialize Gate 1 (InputValidator)
        if self.config.gate1_enabled:
            input_config = InputValidatorConfig(
                use_embeddings=self.config.gate1_embedding_enabled,
                embedding_threshold=self.config.gate1_embedding_threshold,
            )
            self.gate1 = InputValidator(config=input_config)
        else:
            self.gate1 = None

        # Initialize Gate 2 (OutputValidator)
        if self.config.gate2_enabled:
            output_config = OutputValidatorConfig(
                use_embeddings=self.config.gate2_embedding_enabled,
                embedding_threshold=self.config.gate2_embedding_threshold,
            )
            self.gate2 = OutputValidator(config=output_config)
        else:
            self.gate2 = None

        # Initialize Gate 3 (SentinelObserver)
        if self.config.gate3_enabled:
            self.gate3 = SentinelObserver(
                provider=self.config.gate3_provider,
                model=self.config.gate3_model,
                api_key=self.config.gate3_api_key,
                base_url=self.config.gate3_base_url,
                timeout=self.config.gate3_timeout,
            )
        else:
            self.gate3 = None

        # Statistics
        self._validation_count = 0
        self._gate3_calls = 0
        self._blocked_count = 0

        logger.info(
            f"SentinelValidator initialized: "
            f"Gate1={self.config.gate1_enabled}, "
            f"Gate2={self.config.gate2_enabled}, "
            f"Gate3={self.config.gate3_enabled}"
        )

    def validate_input(self, input: str) -> SentinelResult:
        """
        Validate input before sending to AI (Gate 1 only).

        Use this to block obvious attacks before they reach the AI.

        Args:
            input: User's message

        Returns:
            SentinelResult with blocking decision
        """
        start_time = time.time()
        self._validation_count += 1

        if not self.gate1:
            return SentinelResult(
                blocked=False,
                allowed=True,
                decided_by="gate1",
                reasoning="Gate 1 disabled",
                latency_ms=(time.time() - start_time) * 1000,
            )

        try:
            result = self.gate1.validate(input)

            if result.is_attack and result.blocked:
                self._blocked_count += 1
                return SentinelResult.blocked_by_gate1(
                    gate1_result=result,
                    latency_ms=(time.time() - start_time) * 1000,
                )

            return SentinelResult(
                blocked=False,
                allowed=True,
                decided_by="gate1",
                gate1_result=result,
                confidence=1.0 - result.confidence if result.is_attack else 1.0,
                reasoning="Input passed Gate 1",
                latency_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Gate 1 error: {e}")
            if self.config.fail_closed:
                self._blocked_count += 1
                return SentinelResult.error(str(e), fail_closed=True)
            return SentinelResult.error(str(e), fail_closed=False)

    def validate_dialogue(
        self,
        input: str,
        output: str,
    ) -> SentinelResult:
        """
        Validate the complete dialogue (Gates 2 + 3).

        This is the main validation method for post-AI response.
        Gate 3 only executes if Gate 2 cannot decide with high confidence.

        Args:
            input: User's original message
            output: AI's response

        Returns:
            SentinelResult with blocking decision
        """
        start_time = time.time()
        self._validation_count += 1

        # --- Gate 2: Heuristic + Embeddings ---
        gate2_result = None
        if self.gate2:
            try:
                gate2_result = self.gate2.validate(output, input_context=input)

                # High confidence BLOCK
                if (
                    gate2_result.seed_failed
                    and gate2_result.confidence >= self.config.gate2_confidence_threshold
                ):
                    self._blocked_count += 1
                    return SentinelResult.blocked_by_gate2(
                        gate2_result=gate2_result,
                        latency_ms=(time.time() - start_time) * 1000,
                    )

                # High confidence PASS
                if (
                    not gate2_result.seed_failed
                    and gate2_result.confidence >= self.config.gate2_confidence_threshold
                ):
                    return SentinelResult.allowed_by_gate2(
                        gate2_result=gate2_result,
                        latency_ms=(time.time() - start_time) * 1000,
                    )

                # Low confidence - escalate to Gate 3
                logger.debug(
                    f"Gate 2 uncertain (confidence={gate2_result.confidence:.2f}), "
                    f"escalating to Gate 3"
                )

            except Exception as e:
                logger.error(f"Gate 2 error: {e}")
                if self.config.fail_closed and not self.gate3:
                    self._blocked_count += 1
                    return SentinelResult.error(str(e), fail_closed=True)

        # --- Gate 3: LLM Observer ---
        if self.gate3:
            try:
                self._gate3_calls += 1
                gate3_result = self.gate3.observe(input=input, output=output)

                if not gate3_result.is_safe:
                    self._blocked_count += 1
                    return SentinelResult.blocked_by_gate3(
                        gate3_result=gate3_result,
                        gate2_result=gate2_result,
                        latency_ms=(time.time() - start_time) * 1000,
                    )

                return SentinelResult.allowed_by_gate3(
                    gate3_result=gate3_result,
                    gate2_result=gate2_result,
                    latency_ms=(time.time() - start_time) * 1000,
                )

            except Exception as e:
                logger.error(f"Gate 3 error: {e}")
                if self.config.fail_closed:
                    self._blocked_count += 1
                    return SentinelResult.error(str(e), fail_closed=True)
                return SentinelResult.error(str(e), fail_closed=False)

        # No Gate 3 and Gate 2 was uncertain - use Gate 2 result
        if gate2_result:
            if gate2_result.seed_failed:
                self._blocked_count += 1
                return SentinelResult.blocked_by_gate2(
                    gate2_result=gate2_result,
                    latency_ms=(time.time() - start_time) * 1000,
                )
            return SentinelResult.allowed_by_gate2(
                gate2_result=gate2_result,
                latency_ms=(time.time() - start_time) * 1000,
            )

        # No gates enabled - allow by default (or block if fail_closed)
        if self.config.fail_closed:
            return SentinelResult.error("No gates enabled", fail_closed=True)
        return SentinelResult(
            blocked=False,
            allowed=True,
            decided_by="none",
            reasoning="No gates enabled",
            latency_ms=(time.time() - start_time) * 1000,
        )

    def validate(
        self,
        input: str,
        output: str,
    ) -> SentinelResult:
        """
        Convenience method - alias for validate_dialogue.

        Args:
            input: User's message
            output: AI's response

        Returns:
            SentinelResult with blocking decision
        """
        return self.validate_dialogue(input=input, output=output)

    def get_stats(self) -> dict:
        """Get validation statistics."""
        return {
            "total_validations": self._validation_count,
            "blocked": self._blocked_count,
            "passed": self._validation_count - self._blocked_count,
            "gate3_calls": self._gate3_calls,
            "gate3_call_rate": (
                self._gate3_calls / self._validation_count
                if self._validation_count > 0
                else 0
            ),
            "block_rate": (
                self._blocked_count / self._validation_count
                if self._validation_count > 0
                else 0
            ),
            "config": {
                "gate1_enabled": self.config.gate1_enabled,
                "gate2_enabled": self.config.gate2_enabled,
                "gate3_enabled": self.config.gate3_enabled,
                "gate3_model": self.config.gate3_model,
            },
        }
