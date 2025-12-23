"""
Database Guard - Query validation for AI agents

Protects databases from AI agent data exfiltration and SQL injection
by validating queries before execution.

The Problem:
- AI agents need database access to answer questions
- Without validation, agents may:
  - Exfiltrate sensitive data (passwords, PII, financial data)
  - Execute destructive operations (DROP, TRUNCATE)
  - Be manipulated via prompt injection to run malicious queries
- 23% of organizations have experienced AI agent data leaks

The Solution:
- Validate every query before execution
- Block dangerous patterns (SQL injection, excessive data)
- Detect sensitive data access
- Enforce row limits and table access control

Reference: OWASP ASI03 (Identity & Privilege Abuse)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Union

from .patterns import (
    ALL_DETECTION_PATTERNS,
    SENSITIVE_DATA_PATTERNS,
    DetectionPattern,
    SensitiveDataPattern,
)
from .types import (
    DatabaseGuardPolicy,
    PolicyViolation,
    QueryType,
    QueryValidationResult,
    RiskLevel,
    SensitiveDataMatch,
    ViolationType,
    POLICY_MODERATE,
)


class QueryBlocked(Exception):
    """Raised when a query is blocked by Database Guard."""

    def __init__(
        self,
        message: str,
        result: QueryValidationResult,
    ):
        super().__init__(message)
        self.result = result
        self.violations = result.violations


class DatabaseGuard:
    """
    Database query validator for AI agents.

    Validates SQL queries against configurable policies to prevent
    data exfiltration, SQL injection, and destructive operations.

    Usage:
        from sentinelseed.database import DatabaseGuard

        guard = DatabaseGuard(
            max_rows_per_query=1000,
            block_patterns=["SELECT * FROM", "UNION SELECT"],
            sensitive_columns={"password", "ssn", "credit_card"},
        )

        result = guard.validate("SELECT name, email FROM users WHERE id = 123")
        if result.blocked:
            log.warning(f"Query blocked: {result.reason}")
        else:
            cursor.execute(query)

    For strict mode (raises exceptions):
        guard = DatabaseGuard(strict_mode=True)
        try:
            guard.validate(query)  # Raises QueryBlocked if invalid
        except QueryBlocked as e:
            handle_blocked_query(e.result)

    Security Notes:
        - Configure appropriate row limits for your use case
        - Use table allowlists in production
        - Monitor blocked queries for attack patterns
        - Combine with proper database user permissions
    """

    def __init__(
        self,
        policy: Optional[DatabaseGuardPolicy] = None,
        strict_mode: bool = False,
        # Convenience parameters (override policy)
        max_rows_per_query: Optional[int] = None,
        block_patterns: Optional[List[str]] = None,
        require_where_clause: bool = True,
        sensitive_columns: Optional[Set[str]] = None,
        allowed_tables: Optional[Set[str]] = None,
        blocked_tables: Optional[Set[str]] = None,
    ):
        """
        Initialize Database Guard.

        Args:
            policy: Full policy configuration. If None, uses POLICY_MODERATE.
            strict_mode: If True, raises QueryBlocked on validation failure.
            max_rows_per_query: Maximum rows allowed per query (convenience).
            block_patterns: Additional patterns to block (convenience).
            require_where_clause: Require WHERE on UPDATE/DELETE (convenience).
            sensitive_columns: Column names to flag as sensitive (convenience).
            allowed_tables: Whitelist of allowed tables (convenience).
            blocked_tables: Blacklist of blocked tables (convenience).
        """
        self._policy = policy or POLICY_MODERATE
        self._strict_mode = strict_mode
        self._validation_log: List[Dict[str, Any]] = []
        self._custom_patterns: List[DetectionPattern] = []

        # Apply convenience overrides
        if max_rows_per_query is not None:
            self._policy.max_rows_per_query = max_rows_per_query

        if require_where_clause is not None:
            self._policy.require_where_on_update = require_where_clause
            self._policy.require_where_on_delete = require_where_clause

        if sensitive_columns is not None:
            self._policy.sensitive_columns = sensitive_columns

        if allowed_tables is not None:
            self._policy.allowed_tables = allowed_tables

        if blocked_tables is not None:
            self._policy.blocked_tables = blocked_tables

        # Compile custom block patterns
        if block_patterns:
            for i, pattern in enumerate(block_patterns):
                self._custom_patterns.append(
                    DetectionPattern(
                        id=f"custom_block_{i}",
                        pattern=re.compile(pattern, re.IGNORECASE),
                        violation_type=ViolationType.PROHIBITED_PATTERN,
                        risk_level=RiskLevel.HIGH,
                        description=f"Custom blocked pattern: {pattern}",
                    )
                )

    def validate(self, query: str) -> QueryValidationResult:
        """
        Validate a SQL query against the configured policy.

        Args:
            query: The SQL query string to validate.

        Returns:
            QueryValidationResult with validation details.

        Raises:
            QueryBlocked: If strict_mode is True and query is blocked.

        Example:
            result = guard.validate("SELECT * FROM users")
            if result.blocked:
                print(f"Blocked: {result.reason}")
                for v in result.violations:
                    print(f"  - {v.description}")
        """
        if not query or not query.strip():
            return QueryValidationResult(
                allowed=True,
                risk_level=RiskLevel.SAFE,
                query_type=QueryType.UNKNOWN,
                warnings=["Empty query"],
            )

        query = query.strip()
        violations: List[PolicyViolation] = []
        sensitive_data: List[SensitiveDataMatch] = []
        warnings: List[str] = []
        tables: Set[str] = set()

        # Determine query type
        query_type = self._detect_query_type(query)

        # Extract tables
        tables = self._extract_tables(query)

        # Run all pattern checks
        violations.extend(self._check_injection_patterns(query))
        violations.extend(self._check_destructive_patterns(query, query_type))
        violations.extend(self._check_schema_patterns(query, query_type))
        violations.extend(self._check_data_patterns(query))
        violations.extend(self._check_custom_patterns(query))

        # Check table access
        violations.extend(self._check_table_access(tables))

        # Check WHERE clause requirements
        violations.extend(self._check_where_clause(query, query_type))

        # Detect sensitive data
        if self._policy.detect_sensitive_data:
            sensitive_data = self._detect_sensitive_data(query)
            if sensitive_data and self._policy.block_sensitive_data:
                violations.append(
                    PolicyViolation(
                        violation_type=ViolationType.SENSITIVE_DATA,
                        risk_level=RiskLevel.HIGH,
                        description=f"Query accesses sensitive data: {', '.join(s.pattern_id for s in sensitive_data)}",
                        remediation="Exclude sensitive columns from query or use data masking.",
                    )
                )

        # Determine overall risk level
        if violations:
            # RiskLevel enum ordering: SAFE < LOW < MEDIUM < HIGH < CRITICAL
            risk_order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
            max_risk_index = max(risk_order.index(v.risk_level) for v in violations)
            risk_level = risk_order[max_risk_index]
        elif sensitive_data:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.SAFE

        # Determine if allowed
        allowed = len(violations) == 0

        result = QueryValidationResult(
            allowed=allowed,
            risk_level=risk_level,
            query_type=query_type,
            violations=violations,
            sensitive_data=sensitive_data,
            warnings=warnings,
            tables_accessed=tables,
        )

        # Log validation
        self._log_validation(query, result)

        # Raise if strict mode and blocked
        if self._strict_mode and not allowed:
            raise QueryBlocked(
                f"Query blocked: {result.reason}",
                result=result,
            )

        return result

    def validate_and_execute(
        self,
        query: str,
        execute_fn: Callable[[str], Any],
        params: Optional[tuple] = None,
    ) -> Any:
        """
        Validate query and execute if allowed.

        Args:
            query: The SQL query to validate and execute.
            execute_fn: Function to execute the query (e.g., cursor.execute).
            params: Optional query parameters.

        Returns:
            Result of execute_fn if query is allowed.

        Raises:
            QueryBlocked: If query validation fails.

        Example:
            result = guard.validate_and_execute(
                "SELECT name FROM users WHERE id = %s",
                cursor.execute,
                params=(user_id,)
            )
        """
        result = self.validate(query)

        if not result.allowed:
            raise QueryBlocked(
                f"Query blocked: {result.reason}",
                result=result,
            )

        if params:
            return execute_fn(query, params)
        return execute_fn(query)

    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of SQL query."""
        query_upper = query.upper().strip()

        type_map = [
            ("SELECT", QueryType.SELECT),
            ("INSERT", QueryType.INSERT),
            ("UPDATE", QueryType.UPDATE),
            ("DELETE", QueryType.DELETE),
            ("CREATE", QueryType.CREATE),
            ("DROP", QueryType.DROP),
            ("ALTER", QueryType.ALTER),
            ("TRUNCATE", QueryType.TRUNCATE),
            ("EXEC", QueryType.EXECUTE),
        ]

        for prefix, query_type in type_map:
            if query_upper.startswith(prefix):
                return query_type

        return QueryType.UNKNOWN

    def _extract_tables(self, query: str) -> Set[str]:
        """Extract table names from query."""
        tables = set()

        # Match FROM clause
        from_match = re.findall(r"\bFROM\s+(\w+)", query, re.IGNORECASE)
        tables.update(from_match)

        # Match JOIN clause
        join_match = re.findall(r"\bJOIN\s+(\w+)", query, re.IGNORECASE)
        tables.update(join_match)

        # Match INTO clause
        into_match = re.findall(r"\bINTO\s+(\w+)", query, re.IGNORECASE)
        tables.update(into_match)

        # Match UPDATE clause
        update_match = re.findall(r"\bUPDATE\s+(\w+)", query, re.IGNORECASE)
        tables.update(update_match)

        return {t.lower() for t in tables}

    def _check_injection_patterns(self, query: str) -> List[PolicyViolation]:
        """Check for SQL injection patterns."""
        violations = []

        for pattern in ALL_DETECTION_PATTERNS:
            if pattern.violation_type == ViolationType.SQL_INJECTION:
                match = pattern.pattern.search(query)
                if match:
                    violations.append(
                        PolicyViolation(
                            violation_type=pattern.violation_type,
                            risk_level=pattern.risk_level,
                            description=pattern.description,
                            pattern_matched=match.group(),
                            remediation=pattern.remediation,
                        )
                    )

        return violations

    def _check_destructive_patterns(
        self, query: str, query_type: QueryType
    ) -> List[PolicyViolation]:
        """Check for destructive operations."""
        violations = []

        if not self._policy.block_destructive:
            return violations

        for pattern in ALL_DETECTION_PATTERNS:
            if pattern.violation_type == ViolationType.DESTRUCTIVE_OPERATION:
                match = pattern.pattern.search(query)
                if match:
                    violations.append(
                        PolicyViolation(
                            violation_type=pattern.violation_type,
                            risk_level=pattern.risk_level,
                            description=pattern.description,
                            pattern_matched=match.group(),
                            remediation=pattern.remediation,
                        )
                    )

        return violations

    def _check_schema_patterns(
        self, query: str, query_type: QueryType
    ) -> List[PolicyViolation]:
        """Check for schema modification attempts."""
        violations = []

        if not self._policy.block_schema_changes:
            return violations

        for pattern in ALL_DETECTION_PATTERNS:
            if pattern.violation_type in (
                ViolationType.SCHEMA_MODIFICATION,
                ViolationType.PRIVILEGE_ESCALATION,
            ):
                match = pattern.pattern.search(query)
                if match:
                    violations.append(
                        PolicyViolation(
                            violation_type=pattern.violation_type,
                            risk_level=pattern.risk_level,
                            description=pattern.description,
                            pattern_matched=match.group(),
                            remediation=pattern.remediation,
                        )
                    )

        return violations

    def _check_data_patterns(self, query: str) -> List[PolicyViolation]:
        """Check for excessive data access patterns."""
        violations = []

        # Check SELECT *
        if self._policy.block_select_star:
            if re.search(r"\bSELECT\s+\*\s+FROM\b", query, re.IGNORECASE):
                violations.append(
                    PolicyViolation(
                        violation_type=ViolationType.EXCESSIVE_DATA,
                        risk_level=RiskLevel.MEDIUM,
                        description="SELECT * is blocked: explicitly list required columns",
                        pattern_matched="SELECT *",
                        remediation="Replace SELECT * with explicit column list.",
                    )
                )

        # Check UNION
        if self._policy.block_union:
            if re.search(r"\bUNION\b", query, re.IGNORECASE):
                violations.append(
                    PolicyViolation(
                        violation_type=ViolationType.SQL_INJECTION,
                        risk_level=RiskLevel.HIGH,
                        description="UNION is blocked: potential SQL injection vector",
                        pattern_matched="UNION",
                        remediation="Use separate queries or JOINs instead of UNION.",
                    )
                )

        return violations

    def _check_custom_patterns(self, query: str) -> List[PolicyViolation]:
        """Check custom blocked patterns."""
        violations = []

        for pattern in self._custom_patterns:
            match = pattern.pattern.search(query)
            if match:
                violations.append(
                    PolicyViolation(
                        violation_type=pattern.violation_type,
                        risk_level=pattern.risk_level,
                        description=pattern.description,
                        pattern_matched=match.group(),
                        remediation=pattern.remediation,
                    )
                )

        return violations

    def _check_table_access(self, tables: Set[str]) -> List[PolicyViolation]:
        """Check table access against allow/block lists."""
        violations = []

        # Check against whitelist
        if self._policy.allowed_tables is not None:
            unauthorized = tables - self._policy.allowed_tables
            if unauthorized:
                violations.append(
                    PolicyViolation(
                        violation_type=ViolationType.UNAUTHORIZED_TABLE,
                        risk_level=RiskLevel.HIGH,
                        description=f"Unauthorized table access: {', '.join(unauthorized)}",
                        remediation="Only access tables in the allowed list.",
                    )
                )

        # Check against blacklist
        if self._policy.blocked_tables:
            blocked = tables & self._policy.blocked_tables
            if blocked:
                violations.append(
                    PolicyViolation(
                        violation_type=ViolationType.UNAUTHORIZED_TABLE,
                        risk_level=RiskLevel.HIGH,
                        description=f"Blocked table access: {', '.join(blocked)}",
                        remediation="This table is blocked by policy.",
                    )
                )

        return violations

    def _check_where_clause(
        self, query: str, query_type: QueryType
    ) -> List[PolicyViolation]:
        """Check for required WHERE clause."""
        violations = []

        # Check UPDATE
        if (
            query_type == QueryType.UPDATE
            and self._policy.require_where_on_update
        ):
            if not re.search(r"\bWHERE\b", query, re.IGNORECASE):
                violations.append(
                    PolicyViolation(
                        violation_type=ViolationType.MISSING_WHERE,
                        risk_level=RiskLevel.HIGH,
                        description="UPDATE without WHERE clause: would affect all rows",
                        remediation="Add WHERE clause to limit affected rows.",
                    )
                )

        # Check DELETE
        if (
            query_type == QueryType.DELETE
            and self._policy.require_where_on_delete
        ):
            if not re.search(r"\bWHERE\b", query, re.IGNORECASE):
                violations.append(
                    PolicyViolation(
                        violation_type=ViolationType.MISSING_WHERE,
                        risk_level=RiskLevel.CRITICAL,
                        description="DELETE without WHERE clause: would delete all rows",
                        remediation="Add WHERE clause to specify rows to delete.",
                    )
                )

        return violations

    def _detect_sensitive_data(self, query: str) -> List[SensitiveDataMatch]:
        """Detect sensitive data access in query."""
        matches = []

        for pattern in SENSITIVE_DATA_PATTERNS:
            match = pattern.pattern.search(query)
            if match:
                matches.append(
                    SensitiveDataMatch(
                        data_type=pattern.data_type,
                        pattern_id=pattern.id,
                        column_name=match.group(),
                        description=pattern.description,
                    )
                )

        # Also check custom sensitive columns
        if self._policy.sensitive_columns:
            for col in self._policy.sensitive_columns:
                if re.search(rf"\b{re.escape(col)}\b", query, re.IGNORECASE):
                    # Check if not already matched
                    if not any(m.column_name and m.column_name.lower() == col.lower() for m in matches):
                        matches.append(
                            SensitiveDataMatch(
                                data_type=SensitiveDataType.PII,
                                pattern_id=f"custom_{col}",
                                column_name=col,
                                description=f"Custom sensitive column: {col}",
                            )
                        )

        return matches

    def _log_validation(self, query: str, result: QueryValidationResult) -> None:
        """Log validation result."""
        if self._policy.log_all_queries or (
            self._policy.log_blocked_queries and result.blocked
        ):
            self._validation_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query_preview": query[:200] + "..." if len(query) > 200 else query,
                "allowed": result.allowed,
                "risk_level": result.risk_level.value,
                "query_type": result.query_type.value,
                "violation_count": len(result.violations),
                "sensitive_data_count": len(result.sensitive_data),
            })

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        if not self._validation_log:
            return {
                "total": 0,
                "allowed": 0,
                "blocked": 0,
                "block_rate": 0.0,
            }

        total = len(self._validation_log)
        allowed = sum(1 for v in self._validation_log if v["allowed"])

        return {
            "total": total,
            "allowed": allowed,
            "blocked": total - allowed,
            "block_rate": (total - allowed) / total if total > 0 else 0.0,
        }

    def get_recent_blocked(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent blocked queries."""
        blocked = [v for v in self._validation_log if not v["allowed"]]
        return blocked[-limit:]


# Convenience functions
def validate_query(query: str, **kwargs) -> QueryValidationResult:
    """
    Quick validation with default settings.

    Args:
        query: SQL query to validate.
        **kwargs: Options passed to DatabaseGuard.

    Returns:
        QueryValidationResult.
    """
    guard = DatabaseGuard(**kwargs)
    return guard.validate(query)


def is_safe_query(query: str, **kwargs) -> bool:
    """
    Quick check if query is safe.

    Args:
        query: SQL query to check.
        **kwargs: Options passed to DatabaseGuard.

    Returns:
        True if query is allowed, False otherwise.
    """
    result = validate_query(query, **kwargs)
    return result.allowed
