"""
Type definitions for Database Guard module.

Provides dataclasses and enums for query validation results,
policy configuration, and sensitive data classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class QueryType(Enum):
    """Classification of SQL query types."""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    DROP = "drop"
    ALTER = "alter"
    TRUNCATE = "truncate"
    EXECUTE = "execute"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risk classification for queries."""
    CRITICAL = "critical"   # Immediate block, potential attack
    HIGH = "high"           # Block by default, may allow with override
    MEDIUM = "medium"       # Warning, requires review
    LOW = "low"             # Generally safe, minor concerns
    SAFE = "safe"           # No issues detected


class ViolationType(Enum):
    """Types of policy violations."""
    SQL_INJECTION = "sql_injection"
    EXCESSIVE_DATA = "excessive_data"
    SENSITIVE_DATA = "sensitive_data"
    DESTRUCTIVE_OPERATION = "destructive_operation"
    MISSING_WHERE = "missing_where"
    UNAUTHORIZED_TABLE = "unauthorized_table"
    PROHIBITED_PATTERN = "prohibited_pattern"
    SCHEMA_MODIFICATION = "schema_modification"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class SensitiveDataType(Enum):
    """Classification of sensitive data types."""
    PII = "pii"                      # Personally Identifiable Information
    FINANCIAL = "financial"          # Credit cards, bank accounts
    AUTHENTICATION = "authentication"  # Passwords, tokens, keys
    HEALTH = "health"                # Medical/health data (HIPAA)
    LEGAL = "legal"                  # Legal identifiers (SSN, passport)


@dataclass
class PolicyViolation:
    """Represents a single policy violation."""
    violation_type: ViolationType
    risk_level: RiskLevel
    description: str
    pattern_matched: Optional[str] = None
    location: Optional[str] = None  # Where in query the violation was found
    remediation: Optional[str] = None


@dataclass
class SensitiveDataMatch:
    """Represents detection of sensitive data in query."""
    data_type: SensitiveDataType
    pattern_id: str
    column_name: Optional[str] = None
    table_name: Optional[str] = None
    description: str = ""


@dataclass
class QueryValidationResult:
    """
    Result of validating a database query.

    Contains all information about whether the query is allowed,
    any violations found, and recommendations.
    """
    allowed: bool
    risk_level: RiskLevel
    query_type: QueryType
    violations: List[PolicyViolation] = field(default_factory=list)
    sensitive_data: List[SensitiveDataMatch] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    estimated_rows: Optional[int] = None
    tables_accessed: Set[str] = field(default_factory=set)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def blocked(self) -> bool:
        """Alias for not allowed, for clearer API."""
        return not self.allowed

    @property
    def reason(self) -> Optional[str]:
        """Primary reason for blocking, if blocked."""
        if self.allowed:
            return None
        if self.violations:
            return self.violations[0].description
        return "Query blocked by policy"

    @property
    def has_sensitive_data(self) -> bool:
        """Check if query accesses sensitive data."""
        return len(self.sensitive_data) > 0

    @property
    def is_destructive(self) -> bool:
        """Check if query is destructive (DELETE, DROP, TRUNCATE)."""
        return self.query_type in (
            QueryType.DELETE,
            QueryType.DROP,
            QueryType.TRUNCATE,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "allowed": self.allowed,
            "blocked": self.blocked,
            "risk_level": self.risk_level.value,
            "query_type": self.query_type.value,
            "violations": [
                {
                    "type": v.violation_type.value,
                    "risk": v.risk_level.value,
                    "description": v.description,
                    "pattern": v.pattern_matched,
                    "remediation": v.remediation,
                }
                for v in self.violations
            ],
            "sensitive_data": [
                {
                    "type": s.data_type.value,
                    "pattern_id": s.pattern_id,
                    "column": s.column_name,
                    "table": s.table_name,
                }
                for s in self.sensitive_data
            ],
            "warnings": self.warnings,
            "estimated_rows": self.estimated_rows,
            "tables_accessed": list(self.tables_accessed),
            "timestamp": self.timestamp,
        }


@dataclass
class DatabaseGuardPolicy:
    """
    Configuration policy for Database Guard.

    Defines what operations are allowed, limits, and detection rules.
    """
    # Row limits
    max_rows_per_query: int = 1000
    max_rows_per_minute: int = 10000

    # Required clauses
    require_where_on_update: bool = True
    require_where_on_delete: bool = True
    require_limit_on_select: bool = False

    # Blocked operations
    block_destructive: bool = True      # DROP, TRUNCATE
    block_schema_changes: bool = True   # CREATE, ALTER
    block_select_star: bool = True      # SELECT *
    block_union: bool = True            # UNION (common injection)

    # Table access control
    allowed_tables: Optional[Set[str]] = None   # If set, whitelist mode
    blocked_tables: Set[str] = field(default_factory=set)  # Blacklist

    # Sensitive data handling
    detect_sensitive_data: bool = True
    block_sensitive_data: bool = False   # Block queries that access sensitive fields
    sensitive_columns: Set[str] = field(default_factory=lambda: {
        "password", "passwd", "pwd", "secret", "token", "api_key", "apikey",
        "ssn", "social_security", "credit_card", "cc_number", "cvv",
        "bank_account", "routing_number", "private_key", "secret_key",
    })

    # Custom patterns to block (regex)
    custom_block_patterns: List[str] = field(default_factory=list)

    # Logging
    log_all_queries: bool = False
    log_blocked_queries: bool = True

    def with_max_rows(self, limit: int) -> "DatabaseGuardPolicy":
        """Return new policy with updated row limit."""
        return DatabaseGuardPolicy(
            **{**self.__dict__, "max_rows_per_query": limit}
        )

    def with_allowed_tables(self, tables: Set[str]) -> "DatabaseGuardPolicy":
        """Return new policy with allowed tables whitelist."""
        return DatabaseGuardPolicy(
            **{**self.__dict__, "allowed_tables": tables}
        )

    def with_blocked_tables(self, tables: Set[str]) -> "DatabaseGuardPolicy":
        """Return new policy with blocked tables."""
        return DatabaseGuardPolicy(
            **{**self.__dict__, "blocked_tables": tables}
        )


# Preset policies for common use cases
POLICY_STRICT = DatabaseGuardPolicy(
    max_rows_per_query=100,
    require_where_on_update=True,
    require_where_on_delete=True,
    require_limit_on_select=True,
    block_destructive=True,
    block_schema_changes=True,
    block_select_star=True,
    block_union=True,
    block_sensitive_data=True,
)

POLICY_MODERATE = DatabaseGuardPolicy(
    max_rows_per_query=1000,
    require_where_on_update=True,
    require_where_on_delete=True,
    require_limit_on_select=False,
    block_destructive=True,
    block_schema_changes=True,
    block_select_star=True,
    block_union=True,
    block_sensitive_data=False,
)

POLICY_PERMISSIVE = DatabaseGuardPolicy(
    max_rows_per_query=10000,
    require_where_on_update=True,
    require_where_on_delete=True,
    require_limit_on_select=False,
    block_destructive=False,
    block_schema_changes=False,
    block_select_star=False,
    block_union=True,  # Still block UNION for injection protection
    block_sensitive_data=False,
)
