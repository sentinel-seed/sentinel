"""
TextNormalizer - Preprocessing layer for obfuscation detection and removal.

This module implements the normalization phase of the detection pipeline,
which runs BEFORE detectors to remove obfuscation and enable accurate detection.

Architecture:
    The normalizer is the first stage of the detection pipeline:

    Input → [TextNormalizer] → [Detectors] → Result
              │
              └→ Detects obfuscation
              └→ Normalizes text
              └→ Returns metadata for scoring

Without normalization, obfuscated attacks bypass detection:
    - Base64("How to make a bomb") → PatternDetector sees "SG93IHRv..."
    - With normalization → PatternDetector sees "How to make a bomb"

Based on research:
    - "Bypassing Prompt Injection and Jailbreak Detection in LLM Guardrails"
      (arXiv:2504.11168) - Tested 6 guardrail systems, found bypass rates 44-100%
    - "Special-Character Adversarial Attacks" (arXiv:2508.14070)
    - "StructuralSleight" (arXiv:2406.08754) - 94.62% ASR on GPT-4o
    - "Emoji Attack" (arXiv:2411.01077) - 100% ASR with emoji smuggling

Normalization Techniques:
    1. Unicode Control Removal: Zero-width, bidirectional, tags
    2. Unicode Substitution: Fullwidth → ASCII, math symbols → ASCII
    3. Encoding Detection: Base64, hexadecimal, ROT-13
    4. Leetspeak Conversion: h4ck3r → hacker
    5. Text Manipulation: Excessive spaces, character fragmentation

Design Principles:
    1. Non-destructive: Original text preserved in result
    2. Ordered pipeline: Normalizations applied in specific order
    3. Confidence scoring: Each technique has detection confidence
    4. Graceful degradation: Failed normalizations don't break pipeline

Usage:
    from sentinelseed.detection.normalizer import TextNormalizer

    normalizer = TextNormalizer()
    result = normalizer.normalize("SG93IHRvIG1ha2UgYSBib21i")

    if result.is_obfuscated:
        print(f"Obfuscation detected: {result.obfuscation_types}")
        print(f"Normalized: {result.normalized_text}")

References:
    - https://arxiv.org/abs/2504.11168 (Guardrail Bypassing)
    - https://arxiv.org/abs/2508.14070 (Special Characters)
    - https://arxiv.org/abs/2406.08754 (StructuralSleight)
"""

from __future__ import annotations

import base64
import codecs
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sentinelseed.detection.types import (
    NormalizationResult,
    ObfuscationInfo,
    ObfuscationType,
)


logger = logging.getLogger("sentinelseed.detection.normalizer")


# =============================================================================
# UNICODE RANGES AND MAPPINGS
# =============================================================================

# Zero-width and invisible characters
ZERO_WIDTH_CHARS = {
    "\u200b",  # Zero Width Space
    "\u200c",  # Zero Width Non-Joiner
    "\u200d",  # Zero Width Joiner
    "\u200e",  # Left-to-Right Mark
    "\u200f",  # Right-to-Left Mark
    "\u2060",  # Word Joiner
    "\u2061",  # Function Application
    "\u2062",  # Invisible Times
    "\u2063",  # Invisible Separator
    "\u2064",  # Invisible Plus
    "\ufeff",  # Zero Width No-Break Space (BOM)
}

# Bidirectional override characters
BIDI_OVERRIDE_CHARS = {
    "\u202a",  # Left-to-Right Embedding
    "\u202b",  # Right-to-Left Embedding
    "\u202c",  # Pop Directional Formatting
    "\u202d",  # Left-to-Right Override
    "\u202e",  # Right-to-Left Override
    "\u2066",  # Left-to-Right Isolate
    "\u2067",  # Right-to-Left Isolate
    "\u2068",  # First Strong Isolate
    "\u2069",  # Pop Directional Isolate
}

# Unicode Tags (U+E0000-U+E007F) - used for emoji smuggling
TAG_RANGE = range(0xE0000, 0xE0080)

# Fullwidth ASCII range (U+FF00-U+FFEF)
FULLWIDTH_START = 0xFF00
FULLWIDTH_END = 0xFFEF
FULLWIDTH_OFFSET = 0xFEE0  # Subtract to get ASCII

# Mathematical Alphanumeric Symbols (U+1D400-U+1D7FF)
MATH_ALPHA_START = 0x1D400
MATH_ALPHA_END = 0x1D7FF

# Leetspeak mappings (common substitutions)
# Extended with contextual detection - symbols only count in word context
LEETSPEAK_NUMBERS = {
    "4": "a",
    "8": "b",
    "3": "e",
    "6": "g",
    "1": "i",
    "0": "o",
    "5": "s",
    "7": "t",
    "2": "z",
}

# Symbols that could be leetspeak but need word context
LEETSPEAK_SYMBOLS = {
    "@": "a",
    "!": "i",
    "$": "s",
    "+": "t",
    "(": "c",
    "<": "c",
    "|": "i",
    "€": "e",
    "£": "e",
}

# Combined for full detection
LEETSPEAK_MAP = {**LEETSPEAK_NUMBERS, **LEETSPEAK_SYMBOLS}

# Upside down character mapping (100% ASR for jailbreaks)
# Source: arXiv:2504.11168
# IMPORTANT: Only include special Unicode characters, NOT regular ASCII letters
# Regular letters like d, b, n, o should NOT be mapped as they corrupt normal text
UPSIDE_DOWN_MAP = {
    # Lowercase special characters
    "ɐ": "a",  # Turned a
    "ɒ": "a",  # Turned alpha
    "ɔ": "c",  # Open o (looks like turned c)
    "ǝ": "e",  # Turned e
    "ə": "e",  # Schwa
    "ɟ": "f",  # Dotless j with stroke
    "ƃ": "g",  # Turned g
    "ɥ": "h",  # Turned h
    "ᴉ": "i",  # Turned i
    "ɾ": "j",  # Fishhook r (looks like turned j)
    "ʞ": "k",  # Turned k
    "ɯ": "m",  # Turned m
    "ɹ": "r",  # Turned r
    "ʇ": "t",  # Turned t
    "ʌ": "v",  # Turned v
    "ʍ": "w",  # Turned w
    "ʎ": "y",  # Turned y
    # Uppercase special characters
    "∀": "A",  # For all (inverted A)
    "Ɔ": "C",  # Open O capital
    "Ǝ": "E",  # Reversed E
    "Ⅎ": "F",  # Turned F
    "פ": "G",  # Hebrew pe (looks like turned G)
    "ſ": "J",  # Long s (looks like J)
    "˥": "L",  # Modifier letter small capital L
    "Ԁ": "P",  # Cyrillic Komi De
    "┴": "T",  # Box drawing T
    "∩": "U",  # Intersection (inverted U)
    "Λ": "V",  # Greek capital Lambda
    "⅄": "Y",  # Turned Y
}

# Cross-script homoglyphs (44-76% ASR)
# Characters from different Unicode scripts that look like Latin letters
# Source: arXiv:2508.14070
HOMOGLYPH_MAP = {
    # Cyrillic → Latin
    "а": "a", "А": "A",  # Cyrillic a
    "с": "c", "С": "C",  # Cyrillic es
    "е": "e", "Е": "E",  # Cyrillic ie
    "һ": "h", "Һ": "H",  # Cyrillic shha
    "і": "i", "І": "I",  # Cyrillic i
    "ј": "j", "Ј": "J",  # Cyrillic je
    "к": "k", "К": "K",  # Cyrillic ka (looks similar)
    "о": "o", "О": "O",  # Cyrillic o
    "р": "p", "Р": "P",  # Cyrillic er
    "ѕ": "s", "Ѕ": "S",  # Cyrillic dze
    "у": "y", "У": "Y",  # Cyrillic u (looks like y)
    "х": "x", "Х": "X",  # Cyrillic ha
    # Greek → Latin
    "α": "a", "Α": "A",  # Greek alpha
    "β": "b", "Β": "B",  # Greek beta
    "ε": "e", "Ε": "E",  # Greek epsilon
    "η": "n", "Η": "H",  # Greek eta
    "ι": "i", "Ι": "I",  # Greek iota
    "κ": "k", "Κ": "K",  # Greek kappa
    "ν": "v", "Ν": "N",  # Greek nu
    "ο": "o", "Ο": "O",  # Greek omicron
    "ρ": "p", "Ρ": "P",  # Greek rho
    "τ": "t", "Τ": "T",  # Greek tau
    "υ": "u", "Υ": "Y",  # Greek upsilon
    "χ": "x", "Χ": "X",  # Greek chi
    # Other scripts
    "ℓ": "l",  # Script small l
    "ℒ": "L",  # Script capital L
    "ℐ": "I",  # Script capital I
    "ℛ": "R",  # Script capital R
    "ℬ": "B",  # Script capital B
    "ℰ": "E",  # Script capital E
    "ℱ": "F",  # Script capital F
    "ℳ": "M",  # Script capital M
    "ⅰ": "i",  # Roman numeral one
    "ⅱ": "ii", # Roman numeral two
    "ⅲ": "iii", # Roman numeral three
    "ⅳ": "iv",  # Roman numeral four
    "ⅴ": "v",   # Roman numeral five
    "ⅵ": "vi",  # Roman numeral six
    "ⅶ": "vii", # Roman numeral seven
    "ⅷ": "viii", # Roman numeral eight
    "ⅸ": "ix",  # Roman numeral nine
    "ⅹ": "x",   # Roman numeral ten
}

# Emoji variation selectors (used in emoji smuggling)
# Source: arXiv:2411.01077 - 100% ASR
VARIATION_SELECTORS = set(chr(c) for c in range(0xFE00, 0xFE10))  # VS1-VS16
VARIATION_SELECTORS.update(chr(c) for c in range(0xE0100, 0xE01F0))  # VS17-VS256

# Regional indicator symbols (can hide text)
REGIONAL_INDICATORS = set(chr(c) for c in range(0x1F1E6, 0x1F200))

# Patterns for detection
# Minimum 12 chars for base64 (encodes ~9 bytes)
BASE64_PATTERN = re.compile(
    r"^[A-Za-z0-9+/]{12,}={0,2}$"  # At least 12 chars, optional padding
)
BASE64_INLINE_PATTERN = re.compile(
    r"(?:^|\s)([A-Za-z0-9+/]{12,}={0,2})(?:\s|$)"
)
HEX_PATTERN = re.compile(
    r"^(?:0x)?([0-9a-fA-F]{2}\s*){4,}$"  # At least 4 hex bytes
)
HEX_INLINE_PATTERN = re.compile(
    r"(?:^|\s)(?:0x)?([0-9a-fA-F]{2}(?:\s*[0-9a-fA-F]{2}){3,})(?:\s|$)"
)
EXCESSIVE_SPACES_PATTERN = re.compile(
    r"(?:^|\s)([a-zA-Z](?:\s[a-zA-Z]){3,})(?:\s|$)"  # a b c d (single chars with spaces)
)


@dataclass
class NormalizerConfig:
    """
    Configuration for TextNormalizer.

    Attributes:
        enable_unicode_control: Remove zero-width and control chars
        enable_unicode_substitution: Normalize fullwidth/math chars
        enable_encoding_detection: Detect and decode base64/hex/rot13
        enable_leetspeak: Convert leetspeak to normal text
        enable_text_manipulation: Fix excessive spaces, etc.
        enable_upside_down: Normalize upside-down text (100% ASR)
        enable_homoglyphs: Normalize cross-script homoglyphs
        enable_emoji_smuggling: Remove emoji smuggling chars (100% ASR)
        min_base64_length: Minimum length for base64 detection
        min_confidence_to_report: Minimum confidence to include in results
        max_decode_attempts: Maximum decoding attempts per technique
        leetspeak_contextual: Use contextual detection for symbol leetspeak
    """
    enable_unicode_control: bool = True
    enable_unicode_substitution: bool = True
    enable_encoding_detection: bool = True
    enable_leetspeak: bool = True
    enable_text_manipulation: bool = True
    enable_upside_down: bool = True
    enable_homoglyphs: bool = True
    enable_emoji_smuggling: bool = True
    min_base64_length: int = 12
    min_confidence_to_report: float = 0.3
    max_decode_attempts: int = 3
    leetspeak_contextual: bool = True  # Only apply symbol leetspeak in word context


class TextNormalizer:
    """
    Preprocessor that normalizes text to remove obfuscation.

    The normalizer runs before detectors to ensure they analyze
    the actual content, not obfuscated versions that bypass detection.

    Pipeline order:
        1. Remove Unicode control characters (zero-width, bidi)
        2. Normalize Unicode substitutions (fullwidth → ASCII)
        3. Detect and decode encodings (base64, hex)
        4. Convert leetspeak (optional, can have false positives)
        5. Fix text manipulation (excessive spaces)

    Attributes:
        config: NormalizerConfig controlling behavior
        version: Semantic version of the normalizer

    Example:
        normalizer = TextNormalizer()
        result = normalizer.normalize("SGVsbG8gd29ybGQ=")

        if result.is_obfuscated:
            print(f"Decoded: {result.normalized_text}")
            # Use normalized_text for detection
    """

    VERSION = "1.0.0"

    def __init__(self, config: Optional[NormalizerConfig] = None) -> None:
        """
        Initialize TextNormalizer.

        Args:
            config: Optional configuration. Uses defaults if None.
        """
        self.config = config or NormalizerConfig()
        self._stats = {
            "total_normalizations": 0,
            "obfuscations_detected": 0,
            "normalizations_applied": 0,
            "errors": 0,
        }

    @property
    def version(self) -> str:
        """Semantic version of this normalizer."""
        return self.VERSION

    def normalize(self, text: str) -> NormalizationResult:
        """
        Normalize text by detecting and removing obfuscation.

        This is the main entry point. It runs all enabled normalization
        techniques in order and returns the result.

        Args:
            text: Input text to normalize

        Returns:
            NormalizationResult with normalized text and obfuscation info
        """
        self._stats["total_normalizations"] += 1

        # Handle empty input
        if not text or not text.strip():
            return NormalizationResult.no_obfuscation(text or "")

        obfuscations: List[ObfuscationInfo] = []
        current_text = text

        try:
            # Stage 1: Unicode control characters (remove invisible chars first)
            if self.config.enable_unicode_control:
                current_text, stage_obs = self._normalize_unicode_control(
                    current_text, text
                )
                obfuscations.extend(stage_obs)

            # Stage 2: Emoji smuggling (remove variation selectors, tags)
            # Must run early to expose hidden content
            if self.config.enable_emoji_smuggling:
                current_text, stage_obs = self._normalize_emoji_smuggling(
                    current_text, text
                )
                obfuscations.extend(stage_obs)

            # Stage 3: Encoding detection (base64, hex, rot13) - BEFORE character transforms
            # This is critical: we must try to decode BEFORE leetspeak converts digits
            if self.config.enable_encoding_detection:
                current_text, stage_obs = self._normalize_encodings(
                    current_text, text
                )
                obfuscations.extend(stage_obs)

            # Stage 4: Unicode substitution (fullwidth, math)
            if self.config.enable_unicode_substitution:
                current_text, stage_obs = self._normalize_unicode_substitution(
                    current_text, text
                )
                obfuscations.extend(stage_obs)

            # Stage 5: Homoglyphs (cross-script character substitution)
            if self.config.enable_homoglyphs:
                current_text, stage_obs = self._normalize_homoglyphs(
                    current_text, text
                )
                obfuscations.extend(stage_obs)

            # Stage 6: Upside down text (100% ASR for jailbreaks)
            if self.config.enable_upside_down:
                current_text, stage_obs = self._normalize_upside_down(
                    current_text, text
                )
                obfuscations.extend(stage_obs)

            # Stage 7: Leetspeak conversion (after encoding, to avoid corrupting base64)
            if self.config.enable_leetspeak:
                current_text, stage_obs = self._normalize_leetspeak(
                    current_text, text
                )
                obfuscations.extend(stage_obs)

            # Stage 8: Text manipulation (excessive spaces)
            if self.config.enable_text_manipulation:
                current_text, stage_obs = self._normalize_text_manipulation(
                    current_text, text
                )
                obfuscations.extend(stage_obs)

        except Exception as e:
            logger.error(f"Normalization error: {e}")
            self._stats["errors"] += 1
            # Return original text on error
            return NormalizationResult.no_obfuscation(text)

        # Filter by confidence threshold
        obfuscations = [
            o for o in obfuscations
            if o.confidence >= self.config.min_confidence_to_report
        ]

        # Build result
        if obfuscations:
            self._stats["obfuscations_detected"] += 1
            if current_text != text:
                self._stats["normalizations_applied"] += 1

            return NormalizationResult.obfuscation_found(
                original_text=text,
                normalized_text=current_text,
                obfuscations=obfuscations,
            )

        return NormalizationResult.no_obfuscation(text)

    def _normalize_unicode_control(
        self,
        text: str,
        original: str,
    ) -> Tuple[str, List[ObfuscationInfo]]:
        """
        Remove Unicode control characters.

        Removes:
            - Zero-width characters (U+200B-U+200F, U+2060-U+2064, U+FEFF)
            - Bidirectional overrides (U+202A-U+202E, U+2066-U+2069)
            - Unicode tags (U+E0000-U+E007F)

        Returns:
            Tuple of (normalized_text, list of ObfuscationInfo)
        """
        obfuscations = []
        result = []
        found_zero_width = []
        found_bidi = []
        found_tags = []

        for char in text:
            code = ord(char)

            if char in ZERO_WIDTH_CHARS:
                found_zero_width.append(char)
                continue  # Remove

            if char in BIDI_OVERRIDE_CHARS:
                found_bidi.append(char)
                continue  # Remove

            if code in TAG_RANGE:
                found_tags.append(char)
                continue  # Remove

            result.append(char)

        normalized = "".join(result)

        # Report zero-width characters
        if found_zero_width:
            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.UNICODE_CONTROL,
                technique="zero_width",
                original=f"[{len(found_zero_width)} zero-width chars]",
                normalized="[removed]",
                confidence=0.9,
                metadata={"count": len(found_zero_width)},
            ))

        # Report bidirectional overrides
        if found_bidi:
            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.UNICODE_CONTROL,
                technique="bidirectional_override",
                original=f"[{len(found_bidi)} bidi override chars]",
                normalized="[removed]",
                confidence=0.95,
                metadata={"count": len(found_bidi)},
            ))

        # Report Unicode tags
        if found_tags:
            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.UNICODE_CONTROL,
                technique="unicode_tags",
                original=f"[{len(found_tags)} tag chars]",
                normalized="[removed]",
                confidence=0.95,
                metadata={"count": len(found_tags)},
            ))

        return normalized, obfuscations

    def _normalize_unicode_substitution(
        self,
        text: str,
        original: str,
    ) -> Tuple[str, List[ObfuscationInfo]]:
        """
        Normalize Unicode character substitutions.

        Converts:
            - Fullwidth characters (U+FF00-U+FFEF) → ASCII
            - Mathematical alphanumeric (U+1D400-U+1D7FF) → ASCII
            - Common homoglyphs → ASCII

        Returns:
            Tuple of (normalized_text, list of ObfuscationInfo)
        """
        obfuscations = []
        result = []
        found_fullwidth = 0
        found_math = 0

        for char in text:
            code = ord(char)

            # Fullwidth to ASCII
            if FULLWIDTH_START <= code <= FULLWIDTH_END:
                ascii_code = code - FULLWIDTH_OFFSET
                if 0x21 <= ascii_code <= 0x7E:  # Printable ASCII
                    result.append(chr(ascii_code))
                    found_fullwidth += 1
                    continue

            # Mathematical alphanumeric to ASCII
            if MATH_ALPHA_START <= code <= MATH_ALPHA_END:
                # Attempt to get base character via normalization
                normalized_char = unicodedata.normalize("NFKC", char)
                if normalized_char != char and len(normalized_char) == 1:
                    result.append(normalized_char)
                    found_math += 1
                    continue

            result.append(char)

        normalized = "".join(result)

        if found_fullwidth:
            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.UNICODE_SUBSTITUTION,
                technique="fullwidth",
                original=f"[{found_fullwidth} fullwidth chars]",
                normalized="[converted to ASCII]",
                confidence=0.85,
                metadata={"count": found_fullwidth},
            ))

        if found_math:
            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.UNICODE_SUBSTITUTION,
                technique="math_alphanumeric",
                original=f"[{found_math} math alphanumeric chars]",
                normalized="[converted to ASCII]",
                confidence=0.85,
                metadata={"count": found_math},
            ))

        return normalized, obfuscations

    def _normalize_encodings(
        self,
        text: str,
        original: str,
    ) -> Tuple[str, List[ObfuscationInfo]]:
        """
        Detect and decode encoded content.

        Handles:
            - Base64 encoding
            - Hexadecimal encoding
            - ROT-13 (detected but not auto-decoded due to false positives)

        Returns:
            Tuple of (normalized_text, list of ObfuscationInfo)
        """
        obfuscations = []
        current_text = text

        # Try Base64 decoding on entire text
        if self._looks_like_base64(text):
            decoded = self._try_decode_base64(text)
            if decoded:
                obfuscations.append(ObfuscationInfo(
                    type=ObfuscationType.ENCODING,
                    technique="base64",
                    original=text[:50] + ("..." if len(text) > 50 else ""),
                    normalized=decoded[:50] + ("..." if len(decoded) > 50 else ""),
                    confidence=0.95,
                    metadata={"full_match": True},
                ))
                current_text = decoded

        # Try inline Base64 (within text)
        elif self.config.enable_encoding_detection:
            for match in BASE64_INLINE_PATTERN.finditer(text):
                encoded_part = match.group(1)
                decoded = self._try_decode_base64(encoded_part)
                if decoded:
                    obfuscations.append(ObfuscationInfo(
                        type=ObfuscationType.ENCODING,
                        technique="base64_inline",
                        original=encoded_part[:30] + "...",
                        normalized=decoded[:30] + "...",
                        confidence=0.85,
                        position=match.start(),
                    ))
                    current_text = current_text.replace(encoded_part, decoded, 1)

        # Try Hex decoding
        if self._looks_like_hex(current_text):
            decoded = self._try_decode_hex(current_text)
            if decoded:
                obfuscations.append(ObfuscationInfo(
                    type=ObfuscationType.ENCODING,
                    technique="hexadecimal",
                    original=current_text[:50] + "...",
                    normalized=decoded[:50] + ("..." if len(decoded) > 50 else ""),
                    confidence=0.90,
                ))
                current_text = decoded

        # Try ROT-13 decoding (only if text looks alphabetic)
        # ROT-13 detection uses heuristics to avoid false positives
        rot13_decoded = self._try_decode_rot13(current_text)
        if rot13_decoded:
            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.ENCODING,
                technique="rot13",
                original=current_text[:50] + ("..." if len(current_text) > 50 else ""),
                normalized=rot13_decoded[:50] + ("..." if len(rot13_decoded) > 50 else ""),
                confidence=0.80,  # Lower confidence due to heuristic detection
                metadata={"cipher": "rot13"},
            ))
            current_text = rot13_decoded

        return current_text, obfuscations

    def _normalize_leetspeak(
        self,
        text: str,
        original: str,
    ) -> Tuple[str, List[ObfuscationInfo]]:
        """
        Convert leetspeak to normal text.

        Uses contextual detection for symbols to avoid false positives:
        - Numbers (4, 3, 0, etc.) are always converted
        - Symbols (@, !, $, etc.) are only converted when surrounded
          by alphanumeric characters (word context)

        Example:
            "p@ssw0rd" → "password" (@ is in word context)
            "Hello!" → "Hello!" (! is not in word context)

        Returns:
            Tuple of (normalized_text, list of ObfuscationInfo)
        """
        obfuscations = []
        result = []
        number_substitutions = 0
        symbol_substitutions = 0
        total_alpha = 0

        text_len = len(text)

        for i, char in enumerate(text):
            # Check if this is a number-based leetspeak (always convert)
            if char in LEETSPEAK_NUMBERS:
                result.append(LEETSPEAK_NUMBERS[char])
                number_substitutions += 1
                total_alpha += 1
                continue

            # Check if this is a symbol-based leetspeak (contextual)
            if char in LEETSPEAK_SYMBOLS:
                # Only convert if contextual mode is disabled OR in word context
                if not self.config.leetspeak_contextual:
                    result.append(LEETSPEAK_SYMBOLS[char])
                    symbol_substitutions += 1
                    total_alpha += 1
                    continue

                # Check word context: alphanumeric before AND after
                has_before = (i > 0 and (
                    text[i-1].isalnum() or text[i-1] in LEETSPEAK_MAP
                ))
                has_after = (i < text_len - 1 and (
                    text[i+1].isalnum() or text[i+1] in LEETSPEAK_MAP
                ))

                if has_before and has_after:
                    # In word context - convert
                    result.append(LEETSPEAK_SYMBOLS[char])
                    symbol_substitutions += 1
                    total_alpha += 1
                else:
                    # Not in word context - keep original
                    result.append(char)
                continue

            # Regular character
            result.append(char)
            if char.isalpha():
                total_alpha += 1

        normalized = "".join(result)

        # Only report if significant leetspeak detected
        total_substitutions = number_substitutions + symbol_substitutions
        if total_alpha > 0 and total_substitutions > 0:
            density = total_substitutions / total_alpha
            if density >= 0.15:  # At least 15% leetspeak
                confidence = min(0.9, 0.5 + density)
                obfuscations.append(ObfuscationInfo(
                    type=ObfuscationType.LEETSPEAK,
                    technique="leetspeak",
                    original=text[:50] + ("..." if len(text) > 50 else ""),
                    normalized=normalized[:50] + ("..." if len(normalized) > 50 else ""),
                    confidence=confidence,
                    metadata={
                        "substitutions": total_substitutions,
                        "number_subs": number_substitutions,
                        "symbol_subs": symbol_substitutions,
                        "density": round(density, 2),
                        "contextual": self.config.leetspeak_contextual,
                    },
                ))

        return normalized, obfuscations

    def _normalize_text_manipulation(
        self,
        text: str,
        original: str,
    ) -> Tuple[str, List[ObfuscationInfo]]:
        """
        Fix text manipulation techniques.

        Handles:
            - Excessive spaces (h e l l o → hello)
            - Multiple spaces → single space

        Returns:
            Tuple of (normalized_text, list of ObfuscationInfo)
        """
        obfuscations = []
        current_text = text

        # Fix excessive spaces pattern (h e l l o)
        matches = list(EXCESSIVE_SPACES_PATTERN.finditer(text))
        if matches:
            for match in matches:
                spaced_text = match.group(1)
                collapsed = spaced_text.replace(" ", "")
                current_text = current_text.replace(spaced_text, collapsed, 1)

            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.TEXT_MANIPULATION,
                technique="excessive_spaces",
                original=f"[{len(matches)} spaced word(s)]",
                normalized="[spaces collapsed]",
                confidence=0.8,
                metadata={"pattern_count": len(matches)},
            ))

        # Normalize multiple spaces to single
        normalized = re.sub(r" {2,}", " ", current_text)
        if normalized != current_text:
            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.TEXT_MANIPULATION,
                technique="multiple_spaces",
                original="[multiple consecutive spaces]",
                normalized="[normalized to single space]",
                confidence=0.5,  # Low confidence - often legitimate
            ))
            current_text = normalized

        return current_text, obfuscations

    def _looks_like_base64(self, text: str) -> bool:
        """Check if text looks like base64."""
        text = text.strip()
        if len(text) < self.config.min_base64_length:
            return False
        return bool(BASE64_PATTERN.match(text))

    def _try_decode_base64(self, text: str) -> Optional[str]:
        """Attempt to decode base64, return None on failure."""
        try:
            # Add padding if needed
            text = text.strip()
            padding = 4 - (len(text) % 4)
            if padding != 4:
                text += "=" * padding

            decoded_bytes = base64.b64decode(text, validate=True)
            decoded = decoded_bytes.decode("utf-8", errors="strict")

            # Validate: should be mostly printable
            printable_ratio = sum(
                1 for c in decoded if c.isprintable() or c.isspace()
            ) / max(1, len(decoded))

            if printable_ratio >= 0.8:
                return decoded

        except Exception:
            pass

        return None

    def _looks_like_hex(self, text: str) -> bool:
        """Check if text looks like hex encoding."""
        text = text.strip()
        return bool(HEX_PATTERN.match(text))

    def _try_decode_hex(self, text: str) -> Optional[str]:
        """Attempt to decode hex, return None on failure."""
        try:
            # Remove 0x prefix and spaces
            clean = text.strip().lower()
            if clean.startswith("0x"):
                clean = clean[2:]
            clean = clean.replace(" ", "")

            if len(clean) % 2 != 0:
                return None

            decoded_bytes = bytes.fromhex(clean)
            decoded = decoded_bytes.decode("utf-8", errors="strict")

            # Validate: should be mostly printable
            printable_ratio = sum(
                1 for c in decoded if c.isprintable() or c.isspace()
            ) / max(1, len(decoded))

            if printable_ratio >= 0.8:
                return decoded

        except Exception:
            pass

        return None

    def _normalize_emoji_smuggling(
        self,
        text: str,
        original: str,
    ) -> Tuple[str, List[ObfuscationInfo]]:
        """
        Remove emoji smuggling characters.

        Emoji smuggling uses variation selectors and Unicode tags to hide
        text within emoji sequences. This technique has 100% ASR.

        Source: arXiv:2411.01077 "Emoji Attack"

        Removes:
            - Variation selectors (U+FE00-U+FE0F, U+E0100-U+E01EF)
            - Text hidden in tag sequences

        Returns:
            Tuple of (normalized_text, list of ObfuscationInfo)
        """
        obfuscations = []
        result = []
        found_variation_selectors = 0
        found_regional = 0

        for char in text:
            if char in VARIATION_SELECTORS:
                found_variation_selectors += 1
                continue  # Remove

            if char in REGIONAL_INDICATORS:
                found_regional += 1
                # Keep regional indicators but count them

            result.append(char)

        normalized = "".join(result)

        if found_variation_selectors > 0:
            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.UNICODE_CONTROL,
                technique="emoji_smuggling",
                original=f"[{found_variation_selectors} variation selectors]",
                normalized="[removed]",
                confidence=0.98,  # Very high - this is deliberate
                metadata={
                    "count": found_variation_selectors,
                    "asr": "100%",
                },
            ))

        return normalized, obfuscations

    def _normalize_homoglyphs(
        self,
        text: str,
        original: str,
    ) -> Tuple[str, List[ObfuscationInfo]]:
        """
        Normalize cross-script homoglyph characters.

        Homoglyphs are characters from different Unicode scripts that
        look visually similar to Latin letters. Attackers use them to
        evade detection while maintaining readability.

        Source: arXiv:2508.14070 "Special-Character Adversarial Attacks"
        ASR: 44-76%

        Converts:
            - Cyrillic lookalikes → Latin (а → a, о → o)
            - Greek lookalikes → Latin (α → a, ο → o)
            - Script characters → Latin

        Returns:
            Tuple of (normalized_text, list of ObfuscationInfo)
        """
        obfuscations = []
        result = []
        found_cyrillic = 0
        found_greek = 0
        found_other = 0

        for char in text:
            if char in HOMOGLYPH_MAP:
                replacement = HOMOGLYPH_MAP[char]
                result.append(replacement)

                # Track type of homoglyph
                code = ord(char)
                if 0x0400 <= code <= 0x04FF:  # Cyrillic
                    found_cyrillic += 1
                elif 0x0370 <= code <= 0x03FF:  # Greek
                    found_greek += 1
                else:
                    found_other += 1
            else:
                result.append(char)

        normalized = "".join(result)

        total_found = found_cyrillic + found_greek + found_other
        if total_found > 0:
            # Higher confidence with more homoglyphs
            confidence = min(0.95, 0.6 + (total_found * 0.05))

            details = []
            if found_cyrillic:
                details.append(f"{found_cyrillic} Cyrillic")
            if found_greek:
                details.append(f"{found_greek} Greek")
            if found_other:
                details.append(f"{found_other} other")

            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.UNICODE_SUBSTITUTION,
                technique="homoglyph",
                original=f"[{total_found} homoglyph chars: {', '.join(details)}]",
                normalized="[converted to Latin]",
                confidence=confidence,
                metadata={
                    "total": total_found,
                    "cyrillic": found_cyrillic,
                    "greek": found_greek,
                    "other": found_other,
                },
            ))

        return normalized, obfuscations

    def _normalize_upside_down(
        self,
        text: str,
        original: str,
    ) -> Tuple[str, List[ObfuscationInfo]]:
        """
        Normalize upside-down text.

        Upside-down text uses special Unicode characters that look like
        inverted letters. This technique has 100% ASR for jailbreaks.

        Source: arXiv:2504.11168 "Bypassing LLM Guardrails"

        Converts:
            - ɐ → a, ǝ → e, ᴉ → i, etc.
            - ∀ → A, Ǝ → E, ∩ → U, etc.

        Returns:
            Tuple of (normalized_text, list of ObfuscationInfo)
        """
        obfuscations = []
        result = []
        found_upside_down = 0

        for char in text:
            if char in UPSIDE_DOWN_MAP:
                result.append(UPSIDE_DOWN_MAP[char])
                found_upside_down += 1
            else:
                result.append(char)

        normalized = "".join(result)

        if found_upside_down > 0:
            # This is a deliberate obfuscation technique
            confidence = min(0.98, 0.7 + (found_upside_down * 0.05))

            obfuscations.append(ObfuscationInfo(
                type=ObfuscationType.UNICODE_SUBSTITUTION,
                technique="upside_down",
                original=f"[{found_upside_down} upside-down chars]",
                normalized="[converted to normal]",
                confidence=confidence,
                metadata={
                    "count": found_upside_down,
                    "asr": "100%",
                },
            ))

        return normalized, obfuscations

    def _try_decode_rot13(self, text: str) -> Optional[str]:
        """
        Attempt to decode ROT-13.

        ROT-13 is a simple letter substitution cipher that replaces
        each letter with the letter 13 positions after it.

        We detect ROT-13 by checking if the decoded text contains
        more recognizable words than the original.

        Returns:
            Decoded text if ROT-13 detected, None otherwise.
        """
        try:
            # Only try on alphabetic text
            alpha_ratio = sum(1 for c in text if c.isalpha()) / max(1, len(text))
            if alpha_ratio < 0.5:
                return None

            # Decode ROT-13
            decoded = codecs.decode(text, "rot_13")

            # Simple heuristic: check for common English words
            common_words = {
                "the", "and", "for", "are", "but", "not", "you", "all",
                "can", "had", "her", "was", "one", "our", "out", "how",
                "ignore", "instructions", "previous", "system", "admin",
                "hack", "password", "secret", "bypass", "override",
            }

            # Count words in original vs decoded
            orig_words = set(text.lower().split())
            decoded_words = set(decoded.lower().split())

            orig_common = len(orig_words & common_words)
            decoded_common = len(decoded_words & common_words)

            # If decoded has more common words, it's likely ROT-13
            if decoded_common > orig_common and decoded_common >= 2:
                return decoded

        except Exception:
            pass

        return None

    @property
    def stats(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        total = self._stats["total_normalizations"]
        return {
            **self._stats,
            "obfuscation_rate": (
                self._stats["obfuscations_detected"] / total if total > 0 else 0.0
            ),
            "normalization_rate": (
                self._stats["normalizations_applied"] / total if total > 0 else 0.0
            ),
        }

    def reset_stats(self) -> None:
        """Reset normalization statistics."""
        self._stats = {
            "total_normalizations": 0,
            "obfuscations_detected": 0,
            "normalizations_applied": 0,
            "errors": 0,
        }


__all__ = ["TextNormalizer", "NormalizerConfig"]
