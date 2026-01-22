#!/usr/bin/env python3
"""
Memory Patterns Synchronization Script

Generates TypeScript pattern files from the Python source of truth.
This ensures cross-platform consistency between Python and TypeScript implementations.

Usage:
    python scripts/sync-memory-patterns.py

Outputs:
    - packages/browser/src/agent-shield/memory-patterns.ts
    - packages/elizaos/src/memory-patterns.ts

The Python patterns in src/sentinelseed/memory/patterns.py are the source of truth.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from sentinelseed.memory.patterns import (
    ALL_INJECTION_PATTERNS,
    InjectionCategory,
    __version__ as PATTERNS_VERSION,
)


def escape_regex_for_ts(pattern: str) -> str:
    """Escape a Python regex pattern for TypeScript string literal."""
    # Double-escape backslashes for TypeScript string
    return pattern.replace("\\", "\\\\")


def generate_ts_enum() -> str:
    """Generate TypeScript enum for InjectionCategory."""
    lines = [
        "/**",
        " * Categories of memory injection attacks.",
        " */",
        "export enum InjectionCategory {",
    ]
    for cat in InjectionCategory:
        lines.append(f"  {cat.name} = '{cat.value}',")
    lines.append("}")
    return "\n".join(lines)


def generate_ts_severity_map() -> str:
    """Generate severity mapping function."""
    severity_map = {
        InjectionCategory.AUTHORITY_CLAIM: "high",
        InjectionCategory.INSTRUCTION_OVERRIDE: "critical",
        InjectionCategory.ADDRESS_REDIRECTION: "critical",
        InjectionCategory.AIRDROP_SCAM: "high",
        InjectionCategory.URGENCY_MANIPULATION: "medium",
        InjectionCategory.TRUST_EXPLOITATION: "medium",
        InjectionCategory.ROLE_MANIPULATION: "high",
        InjectionCategory.CONTEXT_POISONING: "high",
        InjectionCategory.CRYPTO_ATTACK: "critical",
    }

    lines = [
        "export type InjectionSeverity = 'critical' | 'high' | 'medium' | 'low';",
        "",
        "export function getCategorySeverity(category: InjectionCategory): InjectionSeverity {",
        "  const severityMap: Record<InjectionCategory, InjectionSeverity> = {",
    ]
    for cat, severity in severity_map.items():
        lines.append(f"    [InjectionCategory.{cat.name}]: '{severity}',")
    lines.append("  };")
    lines.append("  return severityMap[category] || 'medium';")
    lines.append("}")
    return "\n".join(lines)


def generate_ts_patterns() -> str:
    """Generate TypeScript pattern array."""
    lines = [
        "// Patterns synchronized with Python patterns.py",
        "export const ALL_INJECTION_PATTERNS: InjectionPattern[] = [",
    ]

    for p in ALL_INJECTION_PATTERNS:
        escaped_pattern = escape_regex_for_ts(p.pattern)
        lines.append("  {")
        lines.append(f"    pattern: '{escaped_pattern}',")
        lines.append(f"    category: InjectionCategory.{p.category.name},")
        lines.append(f"    confidence: {p.confidence},")
        lines.append(f"    reason: '{p.reason}',")
        lines.append(f"    name: '{p.name}',")
        lines.append("  },")

    lines.append("];")
    return "\n".join(lines)


def generate_full_ts_file() -> str:
    """Generate complete TypeScript file."""
    timestamp = datetime.now().isoformat()

    header = f'''/**
 * Memory Injection Pattern Definitions - TypeScript
 *
 * AUTO-GENERATED from Python patterns.py
 * DO NOT EDIT MANUALLY - Run scripts/sync-memory-patterns.py to regenerate
 *
 * Generated: {timestamp}
 * Python version: {PATTERNS_VERSION}
 *
 * @see https://arxiv.org/abs/2503.16248 (Princeton CrAIBench)
 * @see src/sentinelseed/memory/patterns.py (Python source of truth)
 * @author Sentinel Team
 * @version {PATTERNS_VERSION}
 */

export const MEMORY_PATTERNS_VERSION = '{PATTERNS_VERSION}';

'''

    interfaces = '''
export interface InjectionPattern {
  pattern: string;
  category: InjectionCategory;
  confidence: number;
  reason: string;
  name: string;
}

export interface CompiledInjectionPattern {
  regex: RegExp;
  category: InjectionCategory;
  confidence: number;
  reason: string;
  name: string;
}

'''

    functions = '''
export function compilePatterns(
  patterns: InjectionPattern[],
  flags: string = 'i'
): CompiledInjectionPattern[] {
  return patterns.map((p) => ({
    regex: new RegExp(p.pattern, flags),
    category: p.category,
    confidence: p.confidence,
    reason: p.reason,
    name: p.name,
  }));
}

export const COMPILED_INJECTION_PATTERNS: CompiledInjectionPattern[] =
  compilePatterns(ALL_INJECTION_PATTERNS);

export function getPatternsByCategory(
  category: InjectionCategory
): InjectionPattern[] {
  return ALL_INJECTION_PATTERNS.filter((p) => p.category === category);
}

export function getHighConfidencePatterns(
  minConfidence: number = 85
): InjectionPattern[] {
  return ALL_INJECTION_PATTERNS.filter((p) => p.confidence >= minConfidence);
}
'''

    parts = [
        header,
        generate_ts_enum(),
        "",
        generate_ts_severity_map(),
        interfaces,
        generate_ts_patterns(),
        functions,
    ]

    return "\n".join(parts)


def write_file(path: Path, content: str) -> None:
    """Write content to file, creating directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Written: {path}")


def main() -> int:
    """Main entry point."""
    print(f"Synchronizing memory patterns (v{PATTERNS_VERSION})...")
    print(f"  Source: src/sentinelseed/memory/patterns.py")
    print(f"  Patterns: {len(ALL_INJECTION_PATTERNS)}")
    print()

    ts_content = generate_full_ts_file()

    # Output paths
    outputs = [
        ROOT_DIR / "packages" / "browser" / "src" / "agent-shield" / "memory-patterns.ts",
        ROOT_DIR / "packages" / "elizaos" / "src" / "memory-patterns.ts",
    ]

    print("Writing TypeScript files:")
    for output_path in outputs:
        write_file(output_path, ts_content)

    print()
    print("Synchronization complete!")
    print(f"  Categories: {len(InjectionCategory)}")
    print(f"  Patterns: {len(ALL_INJECTION_PATTERNS)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
