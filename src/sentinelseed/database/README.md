# Database Guard

> **Query validation for AI agents to prevent data exfiltration**

Database Guard protects databases from AI agent abuse by validating SQL queries before execution. It addresses **OWASP ASI03 (Identity & Privilege Abuse)** and prevents data exfiltration attacks.

## The Problem

AI agents with database access are vulnerable to:

```
User asks: "What's the weather like?"

Agent (compromised via prompt injection):
  → SELECT * FROM users
  → SELECT password, ssn, credit_card FROM customers
  → DROP TABLE audit_log
```

**Impact:**
- 23% of organizations have experienced AI agent data leaks
- Financial data, PII, and credentials can be exfiltrated
- Destructive operations can corrupt or destroy data

## The Solution

Database Guard validates every query before execution:

```
Query                                    Validation
──────────────────────────────────────────────────────────────
SELECT name FROM users WHERE id=1    →   ✅ ALLOWED
SELECT * FROM users                  →   ❌ BLOCKED (SELECT *)
SELECT password FROM users           →   ❌ BLOCKED (sensitive)
DELETE FROM users                    →   ❌ BLOCKED (no WHERE)
1; DROP TABLE users--                →   ❌ BLOCKED (injection)
```

## Installation

```bash
pip install sentinelseed
```

## Quick Start

```python
from sentinelseed.database import DatabaseGuard

# Create guard with policy
guard = DatabaseGuard(
    max_rows_per_query=1000,
    require_where_clause=True,
)

# Validate before executing
result = guard.validate("SELECT name, email FROM users WHERE active = true")

if result.allowed:
    cursor.execute(query)
else:
    log.warning(f"Query blocked: {result.reason}")
    for v in result.violations:
        print(f"  - {v.description}")
```

## Configuration Options

### Basic Configuration

```python
guard = DatabaseGuard(
    # Row limits
    max_rows_per_query=1000,

    # Require WHERE on destructive operations
    require_where_clause=True,

    # Custom patterns to block
    block_patterns=["SELECT * FROM", "UNION SELECT"],

    # Sensitive columns to detect
    sensitive_columns={"password", "ssn", "credit_card"},

    # Table access control
    allowed_tables={"users", "products", "orders"},  # Whitelist
    blocked_tables={"audit_log", "admin_settings"},  # Blacklist

    # Raise exceptions on blocked queries
    strict_mode=True,
)
```

### Using Preset Policies

```python
from sentinelseed.database import (
    DatabaseGuard,
    POLICY_STRICT,
    POLICY_MODERATE,
    POLICY_PERMISSIVE,
)

# Strict: Block everything risky
guard = DatabaseGuard(policy=POLICY_STRICT)

# Moderate: Reasonable defaults (default)
guard = DatabaseGuard(policy=POLICY_MODERATE)

# Permissive: Minimal blocking
guard = DatabaseGuard(policy=POLICY_PERMISSIVE)
```

### Policy Comparison

| Feature | STRICT | MODERATE | PERMISSIVE |
|---------|--------|----------|------------|
| Max rows/query | 100 | 1,000 | 10,000 |
| Block SELECT * | Yes | Yes | No |
| Block UNION | Yes | Yes | Yes |
| Block DROP/TRUNCATE | Yes | Yes | No |
| Block schema changes | Yes | Yes | No |
| Block sensitive data | Yes | No | No |
| Require WHERE | Yes | Yes | Yes |

## Validation Results

```python
result = guard.validate(query)

# Basic checks
if result.blocked:
    print(f"Blocked: {result.reason}")

if result.has_sensitive_data:
    print("Warning: Accessing sensitive columns")

if result.is_destructive:
    print("Warning: Destructive operation")

# Detailed information
print(f"Query type: {result.query_type.value}")
print(f"Risk level: {result.risk_level.value}")
print(f"Tables: {result.tables_accessed}")

# Violations
for v in result.violations:
    print(f"[{v.risk_level.value}] {v.description}")
    if v.remediation:
        print(f"  Fix: {v.remediation}")

# Sensitive data detected
for s in result.sensitive_data:
    print(f"Sensitive: {s.column_name} ({s.data_type.value})")
```

## Detection Patterns

### SQL Injection (12 patterns)

| Pattern | Risk | Description |
|---------|------|-------------|
| UNION SELECT | Critical | Classic injection |
| OR 1=1 | Critical | Tautology attack |
| --/# comments | High | Query termination |
| SLEEP/BENCHMARK | Critical | Time-based injection |
| INTO OUTFILE | Critical | File write |
| LOAD_FILE | Critical | File read |
| Stacked queries | Critical | Multiple statements |
| INFORMATION_SCHEMA | High | DB enumeration |
| Hex encoding | Medium | Bypass attempt |
| CHAR() | High | Encoding bypass |

### Destructive Operations (4 patterns)

| Pattern | Risk | Description |
|---------|------|-------------|
| DROP TABLE/DATABASE | Critical | Data destruction |
| TRUNCATE TABLE | Critical | Data deletion |
| DELETE without WHERE | High | Mass deletion |
| UPDATE without WHERE | High | Mass modification |

### Sensitive Data (14 patterns)

| Category | Columns Detected |
|----------|------------------|
| Authentication | password, token, api_key, private_key |
| Financial | credit_card, cvv, bank_account, iban |
| Legal | ssn, passport, drivers_license |
| PII | dob, address, phone, email |
| Health (HIPAA) | medical_record, diagnosis, patient_id |

## Strict Mode

In strict mode, blocked queries raise exceptions:

```python
from sentinelseed.database import DatabaseGuard, QueryBlocked

guard = DatabaseGuard(strict_mode=True)

try:
    result = guard.validate("SELECT * FROM users")
except QueryBlocked as e:
    print(f"Blocked: {e}")
    print(f"Violations: {len(e.violations)}")
    for v in e.violations:
        print(f"  - {v.description}")
```

## Validate and Execute

Combine validation and execution:

```python
# Automatically validates before executing
result = guard.validate_and_execute(
    "SELECT name FROM users WHERE id = %s",
    cursor.execute,
    params=(user_id,)
)
```

## Quick Functions

For simple use cases:

```python
from sentinelseed.database import is_safe_query, validate_query

# Quick safety check
if is_safe_query("SELECT name FROM users"):
    cursor.execute(query)

# Quick validation with options
result = validate_query(
    "SELECT * FROM sensitive_table",
    max_rows_per_query=100,
    block_patterns=["sensitive_table"],
)
```

## Statistics

Monitor blocked queries:

```python
stats = guard.get_validation_stats()
print(f"Total: {stats['total']}")
print(f"Blocked: {stats['blocked']}")
print(f"Block rate: {stats['block_rate']:.1%}")

# Get recent blocked queries
for blocked in guard.get_recent_blocked(limit=5):
    print(f"{blocked['timestamp']}: {blocked['query_preview']}")
```

## Integration Examples

### With SQLAlchemy

```python
from sqlalchemy import event
from sentinelseed.database import DatabaseGuard, QueryBlocked

guard = DatabaseGuard(strict_mode=True)

@event.listens_for(engine, "before_cursor_execute")
def validate_query(conn, cursor, statement, parameters, context, executemany):
    try:
        guard.validate(statement)
    except QueryBlocked as e:
        raise SecurityError(f"Query blocked: {e}")
```

### With Django

```python
from django.db import connection
from sentinelseed.database import DatabaseGuard

guard = DatabaseGuard()

class SafeQueryMiddleware:
    def process_request(self, request):
        # Wrap cursor
        original_execute = connection.cursor().execute

        def safe_execute(sql, params=None):
            result = guard.validate(sql)
            if result.blocked:
                raise SecurityError(f"Blocked: {result.reason}")
            return original_execute(sql, params)

        connection.cursor().execute = safe_execute
```

### With LangChain SQL Agent

```python
from langchain.agents import create_sql_agent
from sentinelseed.database import DatabaseGuard

guard = DatabaseGuard(
    allowed_tables={"products", "categories"},
    max_rows_per_query=100,
)

class SafeSQLDatabase(SQLDatabase):
    def run(self, command: str, fetch: str = "all"):
        result = guard.validate(command)
        if result.blocked:
            return f"Query blocked: {result.reason}"
        return super().run(command, fetch)
```

## OWASP Coverage

Database Guard addresses:

| OWASP ID | Vulnerability | Coverage |
|----------|--------------|----------|
| ASI03 | Identity & Privilege Abuse | Full |
| ASI01 | Prompt Injection (via SQL) | Partial |

## Best Practices

1. **Use table whitelists in production**
   ```python
   guard = DatabaseGuard(
       allowed_tables={"users", "products", "orders"}
   )
   ```

2. **Set appropriate row limits**
   ```python
   guard = DatabaseGuard(max_rows_per_query=100)
   ```

3. **Monitor blocked queries**
   ```python
   if stats["block_rate"] > 0.1:
       alert_security_team()
   ```

4. **Combine with database permissions**
   - Database Guard validates queries
   - Database permissions enforce access
   - Defense in depth

5. **Log all blocked queries**
   ```python
   policy = DatabaseGuardPolicy(
       log_blocked_queries=True,
       log_all_queries=False,
   )
   ```

## API Reference

### DatabaseGuard

```python
guard = DatabaseGuard(
    policy: DatabaseGuardPolicy = POLICY_MODERATE,
    strict_mode: bool = False,
    max_rows_per_query: int = None,
    block_patterns: List[str] = None,
    require_where_clause: bool = True,
    sensitive_columns: Set[str] = None,
    allowed_tables: Set[str] = None,
    blocked_tables: Set[str] = None,
)
```

### Methods

| Method | Description |
|--------|-------------|
| `validate(query)` | Validate a SQL query |
| `validate_and_execute(query, fn)` | Validate and execute |
| `get_validation_stats()` | Get validation statistics |
| `get_recent_blocked(limit)` | Get recent blocked queries |

### QueryValidationResult

| Property | Type | Description |
|----------|------|-------------|
| `allowed` | bool | Query is allowed |
| `blocked` | bool | Query is blocked (inverse of allowed) |
| `reason` | str | Primary reason if blocked |
| `risk_level` | RiskLevel | CRITICAL, HIGH, MEDIUM, LOW, SAFE |
| `query_type` | QueryType | SELECT, INSERT, UPDATE, DELETE, etc. |
| `violations` | List[PolicyViolation] | All violations found |
| `sensitive_data` | List[SensitiveDataMatch] | Sensitive columns accessed |
| `tables_accessed` | Set[str] | Tables in query |
| `has_sensitive_data` | bool | Accesses sensitive columns |
| `is_destructive` | bool | DELETE, DROP, TRUNCATE |

## License

MIT License - See [LICENSE](../../../LICENSE) for details.

---

**Sentinel Team** - Practical AI Safety for Developers
