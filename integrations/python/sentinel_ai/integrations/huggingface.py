"""
Hugging Face Transformers integration for Sentinel AI.

Provides a wrapper that adds Sentinel safety checks to any
Hugging Face pipeline or model.

Example:
    from transformers import pipeline
    from sentinel_ai.integrations.huggingface import SentinelTransformersGuard

    # Create a text generation pipeline
    generator = pipeline("text-generation", model="gpt2")

    # Wrap with Sentinel
    safe_generator = SentinelTransformersGuard(generator)

    # Use normally - safety checks are automatic
    result = safe_generator("Tell me about")
"""

from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass

from ..validator import SentinelGuard, ValidationResult, create_chat_guard
from ..seeds import load_seed, load_embedded_seed


@dataclass
class SafeGenerationResult:
    """Result from safe text generation."""
    text: str
    input_validation: ValidationResult
    output_validation: ValidationResult
    was_modified: bool = False
    original_output: Optional[str] = None


class SentinelTransformersGuard:
    """
    Safety wrapper for Hugging Face Transformers pipelines.

    Wraps any text generation pipeline to add input/output validation
    using Sentinel's security patterns and optionally prepends
    alignment seeds to prompts.

    Attributes:
        pipeline: The underlying Transformers pipeline
        guard: SentinelGuard instance for validation
        seed_level: Which seed level to use for system prompts
        block_unsafe_input: Whether to block unsafe inputs
        block_unsafe_output: Whether to block unsafe outputs
    """

    def __init__(
        self,
        pipeline: Any,
        guard: Optional[SentinelGuard] = None,
        seed_level: Optional[str] = None,
        block_unsafe_input: bool = True,
        block_unsafe_output: bool = True,
        on_unsafe_input: Optional[Callable[[str, ValidationResult], str]] = None,
        on_unsafe_output: Optional[Callable[[str, ValidationResult], str]] = None,
    ):
        """
        Initialize the safety wrapper.

        Args:
            pipeline: Hugging Face pipeline to wrap
            guard: Custom SentinelGuard, or None for default
            seed_level: Seed level to prepend ("minimal", "standard", "full", or None)
            block_unsafe_input: Block generation for unsafe inputs
            block_unsafe_output: Filter/block unsafe outputs
            on_unsafe_input: Custom handler for unsafe inputs
            on_unsafe_output: Custom handler for unsafe outputs
        """
        self.pipeline = pipeline
        self.guard = guard or create_chat_guard()
        self.seed_level = seed_level
        self.block_unsafe_input = block_unsafe_input
        self.block_unsafe_output = block_unsafe_output
        self.on_unsafe_input = on_unsafe_input
        self.on_unsafe_output = on_unsafe_output

        # Load seed if specified
        self._seed_content: Optional[str] = None
        if seed_level:
            try:
                self._seed_content = load_seed(seed_level)
            except FileNotFoundError:
                # Fallback to embedded minimal seed
                try:
                    self._seed_content = load_embedded_seed("minimal")
                except ValueError:
                    self._seed_content = None

    def __call__(
        self,
        text: Union[str, List[str]],
        **kwargs: Any,
    ) -> Union[SafeGenerationResult, List[SafeGenerationResult]]:
        """
        Generate text with safety checks.

        Args:
            text: Input text or list of texts
            **kwargs: Additional arguments passed to pipeline

        Returns:
            SafeGenerationResult or list of results
        """
        if isinstance(text, list):
            return [self._generate_safe(t, **kwargs) for t in text]
        return self._generate_safe(text, **kwargs)

    def _generate_safe(self, text: str, **kwargs: Any) -> SafeGenerationResult:
        """Generate text safely for a single input."""
        # Validate input
        input_validation = self.guard.validate_input(text)

        if not input_validation.passed and self.block_unsafe_input:
            # Handle unsafe input
            if self.on_unsafe_input:
                modified_text = self.on_unsafe_input(text, input_validation)
                return SafeGenerationResult(
                    text=modified_text,
                    input_validation=input_validation,
                    output_validation=self.guard.validate_output(modified_text),
                    was_modified=True,
                )
            else:
                # Return a safe refusal message
                refusal = self._get_refusal_message(input_validation)
                return SafeGenerationResult(
                    text=refusal,
                    input_validation=input_validation,
                    output_validation=self.guard.validate_output(refusal),
                    was_modified=True,
                )

        # Optionally prepend seed to prompt
        generation_prompt = text
        if self._seed_content:
            generation_prompt = f"{self._seed_content}\n\nUser: {text}\nAssistant:"

        # Generate
        result = self.pipeline(generation_prompt, **kwargs)

        # Extract generated text
        if isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict) and "generated_text" in result[0]:
                generated_text = result[0]["generated_text"]
                # Remove the prompt if it was prepended
                if self._seed_content and generated_text.startswith(generation_prompt):
                    generated_text = generated_text[len(generation_prompt):].strip()
            else:
                generated_text = str(result[0])
        else:
            generated_text = str(result)

        # Validate output
        output_validation = self.guard.validate_output(generated_text)

        if not output_validation.passed and self.block_unsafe_output:
            # Handle unsafe output
            if self.on_unsafe_output:
                modified_output = self.on_unsafe_output(generated_text, output_validation)
                return SafeGenerationResult(
                    text=modified_output,
                    input_validation=input_validation,
                    output_validation=output_validation,
                    was_modified=True,
                    original_output=generated_text,
                )
            else:
                # Return a filtered message
                filtered = "[Output filtered due to safety concerns]"
                return SafeGenerationResult(
                    text=filtered,
                    input_validation=input_validation,
                    output_validation=output_validation,
                    was_modified=True,
                    original_output=generated_text,
                )

        return SafeGenerationResult(
            text=generated_text,
            input_validation=input_validation,
            output_validation=output_validation,
        )

    def _get_refusal_message(self, validation: ValidationResult) -> str:
        """Get appropriate refusal message based on validation result."""
        if validation.block_reason:
            reason_messages = {
                "prompt_injection": "I can't process this request as it appears to contain instruction manipulation attempts.",
                "jailbreak_attempt": "I'm not able to engage with requests that attempt to bypass safety guidelines.",
                "system_prompt_extraction": "I don't share information about my internal configuration.",
                "pii_detected": "I noticed sensitive personal information in your message. Please avoid sharing such details.",
                "harmful_content": "I can't help with this request as it may involve harmful content.",
            }
            return reason_messages.get(
                validation.block_reason.value,
                "I'm not able to help with this particular request."
            )
        return "I'm not able to help with this particular request."

    def generate(
        self,
        text: Union[str, List[str]],
        **kwargs: Any,
    ) -> Union[SafeGenerationResult, List[SafeGenerationResult]]:
        """Alias for __call__."""
        return self(text, **kwargs)

    def is_input_safe(self, text: str) -> bool:
        """Quick check if input is safe."""
        return self.guard.validate_input(text).passed

    def is_output_safe(self, text: str) -> bool:
        """Quick check if output is safe."""
        return self.guard.validate_output(text).passed


class SentinelTextClassificationGuard:
    """
    Safety wrapper for text classification pipelines.

    Adds input validation to ensure classifier inputs are safe.
    """

    def __init__(
        self,
        pipeline: Any,
        guard: Optional[SentinelGuard] = None,
        block_unsafe: bool = True,
    ):
        self.pipeline = pipeline
        self.guard = guard or create_chat_guard()
        self.block_unsafe = block_unsafe

    def __call__(self, text: Union[str, List[str]], **kwargs: Any) -> Any:
        """Classify text with safety checks on input."""
        if isinstance(text, str):
            texts = [text]
        else:
            texts = text

        # Validate all inputs
        for t in texts:
            validation = self.guard.validate_input(t)
            if not validation.passed and self.block_unsafe:
                return {"error": "Input blocked due to safety concerns", "validation": validation}

        return self.pipeline(text, **kwargs)


def wrap_pipeline(
    pipeline: Any,
    seed_level: str = "standard",
    **guard_kwargs: Any,
) -> SentinelTransformersGuard:
    """
    Convenience function to wrap a pipeline with Sentinel.

    Args:
        pipeline: Hugging Face pipeline to wrap
        seed_level: Seed level for alignment
        **guard_kwargs: Arguments passed to SentinelGuard

    Returns:
        Wrapped pipeline with safety checks
    """
    guard = SentinelGuard(**guard_kwargs)
    return SentinelTransformersGuard(
        pipeline=pipeline,
        guard=guard,
        seed_level=seed_level,
    )
