"""
Sentinel Database Guard Module

Protects databases from AI agent data exfiltration and SQL injection
by validating queries before execution.

Usage:
    from sentinelseed.database import DatabaseGuard

    guard = DatabaseGuard(
        max_rows_per_query=1000,
        block_patterns=["SELECT * FROM", "UNION SELECT"],
        require_where_clause=True,
    )

    result = guard.validate("SELECT name FROM users WHERE id = 123")
    if result.blocked:
        log.warning(f"Query blocked: {result.reason}")
    else:
        cursor.execute(query)

For strict mode:
    guard = DatabaseGuard(strict_mode=True)
    try:
        guard.validate(query)  # Raises QueryBlocked if invalid
    except QueryBlocked as e:
        handle_blocked(e)

Quick validation:
    from sentinelseed.database import is_safe_query, validate_query

    if is_safe_query("SELECT * FROM users"):
        execute(query)

    result = validate_query(query, max_rows_per_query=100)
    if result.has_sensitive_data:
        log.warning("Query accesses sensitive columns")

Reference: OWASP ASI03 (Identity and Privilege Abuse)
"""

from .guard import (
    DatabaseGuard,
    QueryBlocked,
    validate_query,
    is_safe_query,
)
from .types import (
    QueryType,
    RiskLevel,
    ViolationType,
    SensitiveDataType,
    PolicyViolation,
    SensitiveDataMatch,
    QueryValidationResult,
    DatabaseGuardPolicy,
    POLICY_STRICT,
    POLICY_MODERATE,
    POLICY_PERMISSIVE,
)
from .patterns import (
    DetectionPattern,
    SensitiveDataPattern,
    SQL_INJECTION_PATTERNS,
    DESTRUCTIVE_PATTERNS,
    SCHEMA_PATTERNS,
    SENSITIVE_DATA_PATTERNS,
    ALL_DETECTION_PATTERNS,
    get_patterns_by_risk,
    get_patterns_by_type,
)

__all__ = [
    # Main class
    "DatabaseGuard",
    "QueryBlocked",
    # Convenience functions
    "validate_query",
    "is_safe_query",
    # Types
    "QueryType",
    "RiskLevel",
    "ViolationType",
    "SensitiveDataType",
    "PolicyViolation",
    "SensitiveDataMatch",
    "QueryValidationResult",
    "DatabaseGuardPolicy",
    # Preset policies
    "POLICY_STRICT",
    "POLICY_MODERATE",
    "POLICY_PERMISSIVE",
    # Patterns
    "DetectionPattern",
    "SensitiveDataPattern",
    "SQL_INJECTION_PATTERNS",
    "DESTRUCTIVE_PATTERNS",
    "SCHEMA_PATTERNS",
    "SENSITIVE_DATA_PATTERNS",
    "ALL_DETECTION_PATTERNS",
    "get_patterns_by_risk",
    "get_patterns_by_type",
]
