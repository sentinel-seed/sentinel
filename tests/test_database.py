"""Tests for sentinelseed.database module."""

import pytest

from sentinelseed.database import (
    DatabaseGuard,
    QueryBlocked,
    QueryValidationResult,
    QueryType,
    RiskLevel,
    ViolationType,
    validate_query,
    is_safe_query,
    POLICY_STRICT,
    POLICY_MODERATE,
    POLICY_PERMISSIVE,
)


class TestDatabaseGuard:
    """Tests for DatabaseGuard class."""

    def test_init_default(self):
        """Test default initialization."""
        guard = DatabaseGuard()
        assert guard is not None

    def test_init_with_options(self):
        """Test initialization with options."""
        guard = DatabaseGuard(
            max_rows_per_query=500,
            require_where_clause=True,
            strict_mode=False,
        )
        assert guard is not None

    def test_validate_safe_select(self):
        """Test validation of safe SELECT query."""
        guard = DatabaseGuard()
        result = guard.validate(
            "SELECT name, email FROM users WHERE id = 123"
        )

        assert result.allowed is True
        assert result.blocked is False
        assert result.query_type == QueryType.SELECT
        assert len(result.violations) == 0

    def test_validate_select_star_blocked(self):
        """Test that SELECT * is blocked by default."""
        guard = DatabaseGuard()
        result = guard.validate("SELECT * FROM users")

        assert result.allowed is False
        assert result.blocked is True
        assert any(
            v.violation_type == ViolationType.EXCESSIVE_DATA
            for v in result.violations
        )

    def test_validate_union_blocked(self):
        """Test that UNION is blocked."""
        guard = DatabaseGuard()
        result = guard.validate(
            "SELECT name FROM users UNION SELECT password FROM admin"
        )

        assert result.allowed is False
        assert any(
            v.violation_type == ViolationType.SQL_INJECTION
            for v in result.violations
        )

    def test_validate_drop_table_blocked(self):
        """Test that DROP TABLE is blocked."""
        guard = DatabaseGuard()
        result = guard.validate("DROP TABLE users")

        assert result.allowed is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert any(
            v.violation_type == ViolationType.DESTRUCTIVE_OPERATION
            for v in result.violations
        )

    def test_validate_delete_without_where_blocked(self):
        """Test that DELETE without WHERE is blocked."""
        guard = DatabaseGuard()
        result = guard.validate("DELETE FROM users")

        assert result.allowed is False
        assert any(
            v.violation_type == ViolationType.MISSING_WHERE
            for v in result.violations
        )

    def test_validate_delete_with_where_allowed(self):
        """Test that DELETE with WHERE is allowed."""
        guard = DatabaseGuard()
        result = guard.validate("DELETE FROM users WHERE id = 123")

        # Should be allowed (has WHERE clause)
        # Note: may still be blocked by SELECT * check if present
        where_violations = [
            v for v in result.violations
            if v.violation_type == ViolationType.MISSING_WHERE
        ]
        assert len(where_violations) == 0

    def test_validate_update_without_where_blocked(self):
        """Test that UPDATE without WHERE is blocked."""
        guard = DatabaseGuard()
        result = guard.validate("UPDATE users SET status = 'inactive'")

        assert result.allowed is False
        assert any(
            v.violation_type == ViolationType.MISSING_WHERE
            for v in result.violations
        )

    def test_validate_sql_injection_patterns(self):
        """Test detection of SQL injection patterns."""
        guard = DatabaseGuard()

        injection_queries = [
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            "SELECT * FROM users; DROP TABLE users;--",
            "SELECT * FROM users WHERE name = '' UNION SELECT password FROM admin--",
            "SELECT SLEEP(5)",
            "SELECT * FROM users INTO OUTFILE '/tmp/data.txt'",
        ]

        for query in injection_queries:
            result = guard.validate(query)
            assert result.allowed is False, f"Query should be blocked: {query}"
            assert result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_validate_sensitive_data_detection(self):
        """Test detection of sensitive data access."""
        guard = DatabaseGuard()
        result = guard.validate(
            "SELECT name, password, ssn FROM users"
        )

        assert result.has_sensitive_data is True
        assert len(result.sensitive_data) > 0
        # Should detect password and ssn
        sensitive_columns = {s.column_name.lower() for s in result.sensitive_data}
        assert "password" in sensitive_columns
        assert "ssn" in sensitive_columns

    def test_validate_table_whitelist(self):
        """Test table whitelist enforcement."""
        guard = DatabaseGuard(
            allowed_tables={"users", "products"}
        )

        # Allowed table
        result = guard.validate("SELECT name FROM users WHERE id = 1")
        table_violations = [
            v for v in result.violations
            if v.violation_type == ViolationType.UNAUTHORIZED_TABLE
        ]
        assert len(table_violations) == 0

        # Unauthorized table
        result = guard.validate("SELECT * FROM secret_data")
        assert result.allowed is False
        assert any(
            v.violation_type == ViolationType.UNAUTHORIZED_TABLE
            for v in result.violations
        )

    def test_validate_table_blacklist(self):
        """Test table blacklist enforcement."""
        guard = DatabaseGuard(
            blocked_tables={"audit_log", "admin_settings"}
        )

        result = guard.validate("SELECT * FROM audit_log")
        assert result.allowed is False
        assert any(
            v.violation_type == ViolationType.UNAUTHORIZED_TABLE
            for v in result.violations
        )

    def test_strict_mode_raises_exception(self):
        """Test that strict mode raises QueryBlocked."""
        guard = DatabaseGuard(strict_mode=True)

        with pytest.raises(QueryBlocked) as exc_info:
            guard.validate("DROP TABLE users")

        assert exc_info.value.result.blocked is True
        assert len(exc_info.value.violations) > 0

    def test_custom_block_patterns(self):
        """Test custom block patterns."""
        guard = DatabaseGuard(
            block_patterns=["sensitive_table", r"\bINNER\s+JOIN\b"]
        )

        result = guard.validate("SELECT * FROM sensitive_table")
        assert result.allowed is False

        result = guard.validate("SELECT * FROM users INNER JOIN orders")
        assert result.allowed is False

    def test_query_type_detection(self):
        """Test query type detection."""
        guard = DatabaseGuard()

        test_cases = [
            ("SELECT name FROM users", QueryType.SELECT),
            ("INSERT INTO users VALUES (1, 'test')", QueryType.INSERT),
            ("UPDATE users SET name = 'test' WHERE id = 1", QueryType.UPDATE),
            ("DELETE FROM users WHERE id = 1", QueryType.DELETE),
            ("CREATE TABLE new_table (id INT)", QueryType.CREATE),
            ("DROP TABLE old_table", QueryType.DROP),
        ]

        for query, expected_type in test_cases:
            result = guard.validate(query)
            assert result.query_type == expected_type, f"Query: {query}"

    def test_tables_extraction(self):
        """Test table name extraction from queries."""
        guard = DatabaseGuard()

        result = guard.validate(
            "SELECT u.name, o.total FROM users u "
            "JOIN orders o ON u.id = o.user_id"
        )

        assert "users" in result.tables_accessed
        assert "orders" in result.tables_accessed

    def test_validation_stats(self):
        """Test validation statistics tracking."""
        from sentinelseed.database import DatabaseGuardPolicy

        # Use policy that logs all queries
        policy = DatabaseGuardPolicy(log_all_queries=True)
        guard = DatabaseGuard(policy=policy)

        guard.validate("SELECT name FROM users WHERE id = 1")
        guard.validate("DROP TABLE users")
        guard.validate("SELECT email FROM users WHERE active = true")

        stats = guard.get_validation_stats()

        assert stats["total"] == 3
        assert stats["blocked"] >= 1
        assert stats["allowed"] >= 1

    def test_empty_query(self):
        """Test empty query handling."""
        guard = DatabaseGuard()

        result = guard.validate("")
        assert result.allowed is True
        assert result.query_type == QueryType.UNKNOWN

        result = guard.validate("   ")
        assert result.allowed is True


class TestPresetPolicies:
    """Tests for preset policies."""

    def test_policy_strict(self):
        """Test POLICY_STRICT blocks aggressively."""
        guard = DatabaseGuard(policy=POLICY_STRICT)

        # Should block sensitive data access
        result = guard.validate("SELECT password FROM users WHERE id = 1")
        assert result.allowed is False

    def test_policy_moderate(self):
        """Test POLICY_MODERATE has balanced blocking."""
        guard = DatabaseGuard(policy=POLICY_MODERATE)

        # Safe query should be allowed
        result = guard.validate("SELECT name FROM users WHERE id = 1")
        assert result.allowed is True

        # SELECT * should be blocked
        result = guard.validate("SELECT * FROM users")
        assert result.allowed is False

    def test_policy_permissive(self):
        """Test POLICY_PERMISSIVE allows more."""
        guard = DatabaseGuard(policy=POLICY_PERMISSIVE)

        # SELECT * should be allowed
        result = guard.validate("SELECT * FROM users WHERE id = 1")
        # In permissive mode, SELECT * is allowed
        select_star_violations = [
            v for v in result.violations
            if "SELECT *" in (v.pattern_matched or "")
        ]
        assert len(select_star_violations) == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_validate_query(self):
        """Test validate_query function."""
        result = validate_query("SELECT name FROM users WHERE id = 1")
        assert isinstance(result, QueryValidationResult)
        assert result.allowed is True

    def test_is_safe_query(self):
        """Test is_safe_query function."""
        assert is_safe_query("SELECT name FROM users WHERE id = 1") is True
        assert is_safe_query("DROP TABLE users") is False


class TestQueryValidationResult:
    """Tests for QueryValidationResult."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        guard = DatabaseGuard()
        result = guard.validate("SELECT * FROM users")

        d = result.to_dict()

        assert "allowed" in d
        assert "blocked" in d
        assert "risk_level" in d
        assert "violations" in d
        assert "sensitive_data" in d
        assert "tables_accessed" in d

    def test_is_destructive(self):
        """Test is_destructive property."""
        guard = DatabaseGuard()

        result = guard.validate("DELETE FROM users WHERE id = 1")
        assert result.is_destructive is True

        result = guard.validate("SELECT name FROM users")
        assert result.is_destructive is False

    def test_reason_property(self):
        """Test reason property."""
        guard = DatabaseGuard()

        result = guard.validate("SELECT name FROM users WHERE id = 1")
        assert result.reason is None

        result = guard.validate("DROP TABLE users")
        assert result.reason is not None
        assert len(result.reason) > 0
