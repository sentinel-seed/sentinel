"""
Detection patterns for Database Guard.

Contains regex patterns for detecting:
- SQL injection attacks
- Sensitive data access
- Dangerous query patterns
- Schema manipulation attempts
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Pattern

from .types import RiskLevel, SensitiveDataType, ViolationType


@dataclass
class DetectionPattern:
    """A pattern for detecting policy violations."""
    id: str
    pattern: Pattern[str]
    violation_type: ViolationType
    risk_level: RiskLevel
    description: str
    remediation: Optional[str] = None


@dataclass
class SensitiveDataPattern:
    """A pattern for detecting sensitive data access."""
    id: str
    pattern: Pattern[str]
    data_type: SensitiveDataType
    description: str
    columns: Optional[List[str]] = None  # Specific column names to match


# SQL Injection patterns
SQL_INJECTION_PATTERNS: List[DetectionPattern] = [
    DetectionPattern(
        id="sqli_union_select",
        pattern=re.compile(r"\bUNION\s+(ALL\s+)?SELECT\b", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.CRITICAL,
        description="UNION SELECT detected: common SQL injection technique",
        remediation="Use parameterized queries. Never concatenate user input into SQL.",
    ),
    DetectionPattern(
        id="sqli_comment_injection",
        pattern=re.compile(r"(--|#|/\*.*\*/)\s*$", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.HIGH,
        description="SQL comment sequence at end of query: potential injection",
        remediation="Validate and sanitize all inputs. Use parameterized queries.",
    ),
    DetectionPattern(
        id="sqli_or_true",
        pattern=re.compile(r"\bOR\s+['\"]?1['\"]?\s*=\s*['\"]?1['\"]?", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.CRITICAL,
        description="OR 1=1 tautology detected: classic SQL injection",
        remediation="Never trust user input. Use prepared statements.",
    ),
    DetectionPattern(
        id="sqli_or_always_true",
        pattern=re.compile(r"\bOR\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?\s*--", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.CRITICAL,
        description="OR condition with comment: SQL injection attempt",
        remediation="Use parameterized queries. Validate all inputs.",
    ),
    DetectionPattern(
        id="sqli_semicolon_multi",
        pattern=re.compile(r";\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.CRITICAL,
        description="Multiple statements detected: stacked query injection",
        remediation="Disable multiple statements. Use single-query prepared statements.",
    ),
    DetectionPattern(
        id="sqli_hex_encoding",
        pattern=re.compile(r"0x[0-9a-fA-F]{4,}", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.MEDIUM,
        description="Hex-encoded value detected: potential encoding bypass",
        remediation="Decode and validate hex values. Use allowlists for expected values.",
    ),
    DetectionPattern(
        id="sqli_char_function",
        pattern=re.compile(r"\bCHAR\s*\(\s*\d+\s*(,\s*\d+\s*)*\)", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.HIGH,
        description="CHAR() function detected: potential encoding bypass",
        remediation="Block dynamic character construction. Use parameterized queries.",
    ),
    DetectionPattern(
        id="sqli_sleep_benchmark",
        pattern=re.compile(r"\b(SLEEP|BENCHMARK|WAITFOR\s+DELAY|pg_sleep)\s*\(", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.CRITICAL,
        description="Time-based SQL injection attempt detected",
        remediation="Block time-delay functions. Monitor for slow queries.",
    ),
    DetectionPattern(
        id="sqli_into_outfile",
        pattern=re.compile(r"\bINTO\s+(OUT|DUMP)FILE\b", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.CRITICAL,
        description="File write attempt detected: potential data exfiltration",
        remediation="Revoke FILE privilege. Block file operations in queries.",
    ),
    DetectionPattern(
        id="sqli_load_file",
        pattern=re.compile(r"\bLOAD_FILE\s*\(", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.CRITICAL,
        description="File read attempt detected: potential data exfiltration",
        remediation="Revoke FILE privilege. Block file operations.",
    ),
    DetectionPattern(
        id="sqli_information_schema",
        pattern=re.compile(r"\bINFORMATION_SCHEMA\b", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.HIGH,
        description="Information schema access: database enumeration attempt",
        remediation="Restrict access to system tables. Use least-privilege accounts.",
    ),
    DetectionPattern(
        id="sqli_sys_tables",
        pattern=re.compile(r"\b(sysobjects|syscolumns|pg_catalog|mysql\.user)\b", re.IGNORECASE),
        violation_type=ViolationType.SQL_INJECTION,
        risk_level=RiskLevel.HIGH,
        description="System table access: privilege escalation attempt",
        remediation="Use restricted database accounts. Block system table access.",
    ),
]

# Destructive operation patterns
DESTRUCTIVE_PATTERNS: List[DetectionPattern] = [
    DetectionPattern(
        id="destructive_drop_table",
        pattern=re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX)\b", re.IGNORECASE),
        violation_type=ViolationType.DESTRUCTIVE_OPERATION,
        risk_level=RiskLevel.CRITICAL,
        description="DROP statement detected: destructive operation",
        remediation="Use soft deletes. Require explicit confirmation for destructive ops.",
    ),
    DetectionPattern(
        id="destructive_truncate",
        pattern=re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE),
        violation_type=ViolationType.DESTRUCTIVE_OPERATION,
        risk_level=RiskLevel.CRITICAL,
        description="TRUNCATE detected: will delete all data",
        remediation="Use DELETE with WHERE. Implement backup before truncate.",
    ),
    DetectionPattern(
        id="destructive_delete_all",
        pattern=re.compile(r"\bDELETE\s+FROM\s+\w+\s*(?:;|$)", re.IGNORECASE),
        violation_type=ViolationType.DESTRUCTIVE_OPERATION,
        risk_level=RiskLevel.HIGH,
        description="DELETE without WHERE: will delete all rows",
        remediation="Always use WHERE clause with DELETE statements.",
    ),
    DetectionPattern(
        id="destructive_update_all",
        pattern=re.compile(r"\bUPDATE\s+\w+\s+SET\s+.+(?:;|$)(?!\s*WHERE)", re.IGNORECASE),
        violation_type=ViolationType.DESTRUCTIVE_OPERATION,
        risk_level=RiskLevel.HIGH,
        description="UPDATE without WHERE: will update all rows",
        remediation="Always use WHERE clause with UPDATE statements.",
    ),
]

# Schema modification patterns
SCHEMA_PATTERNS: List[DetectionPattern] = [
    DetectionPattern(
        id="schema_create",
        pattern=re.compile(r"\bCREATE\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW|PROCEDURE|FUNCTION|TRIGGER)\b", re.IGNORECASE),
        violation_type=ViolationType.SCHEMA_MODIFICATION,
        risk_level=RiskLevel.HIGH,
        description="CREATE statement detected: schema modification",
        remediation="Use migration tools. Require DBA approval for schema changes.",
    ),
    DetectionPattern(
        id="schema_alter",
        pattern=re.compile(r"\bALTER\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW|PROCEDURE|FUNCTION)\b", re.IGNORECASE),
        violation_type=ViolationType.SCHEMA_MODIFICATION,
        risk_level=RiskLevel.HIGH,
        description="ALTER statement detected: schema modification",
        remediation="Use migration tools. Version control all schema changes.",
    ),
    DetectionPattern(
        id="schema_grant",
        pattern=re.compile(r"\b(GRANT|REVOKE)\s+", re.IGNORECASE),
        violation_type=ViolationType.PRIVILEGE_ESCALATION,
        risk_level=RiskLevel.CRITICAL,
        description="GRANT/REVOKE detected: privilege modification attempt",
        remediation="Only DBAs should modify privileges. Use least-privilege accounts.",
    ),
]

# Excessive data patterns
EXCESSIVE_DATA_PATTERNS: List[DetectionPattern] = [
    DetectionPattern(
        id="excessive_select_star",
        pattern=re.compile(r"\bSELECT\s+\*\s+FROM\b", re.IGNORECASE),
        violation_type=ViolationType.EXCESSIVE_DATA,
        risk_level=RiskLevel.MEDIUM,
        description="SELECT * detected: may return excessive or sensitive data",
        remediation="Explicitly list required columns. Use column allowlists.",
    ),
    DetectionPattern(
        id="excessive_no_limit",
        pattern=re.compile(r"\bSELECT\s+(?!.*\bLIMIT\b).*FROM\b", re.IGNORECASE | re.DOTALL),
        violation_type=ViolationType.EXCESSIVE_DATA,
        risk_level=RiskLevel.LOW,
        description="SELECT without LIMIT: may return excessive rows",
        remediation="Add LIMIT clause to prevent unbounded result sets.",
    ),
]

# Sensitive data column patterns
SENSITIVE_DATA_PATTERNS: List[SensitiveDataPattern] = [
    # Authentication data
    SensitiveDataPattern(
        id="sensitive_password",
        pattern=re.compile(r"\b(password|passwd|pwd|pass_hash|password_hash)\b", re.IGNORECASE),
        data_type=SensitiveDataType.AUTHENTICATION,
        description="Password field access detected",
        columns=["password", "passwd", "pwd", "pass_hash", "password_hash"],
    ),
    SensitiveDataPattern(
        id="sensitive_token",
        pattern=re.compile(r"\b(token|api_key|apikey|secret_key|access_token|refresh_token|auth_token)\b", re.IGNORECASE),
        data_type=SensitiveDataType.AUTHENTICATION,
        description="Authentication token field access detected",
        columns=["token", "api_key", "apikey", "secret_key", "access_token", "refresh_token"],
    ),
    SensitiveDataPattern(
        id="sensitive_private_key",
        pattern=re.compile(r"\b(private_key|secret|signing_key|encryption_key)\b", re.IGNORECASE),
        data_type=SensitiveDataType.AUTHENTICATION,
        description="Cryptographic key field access detected",
        columns=["private_key", "secret", "signing_key", "encryption_key"],
    ),

    # Financial data
    SensitiveDataPattern(
        id="sensitive_credit_card",
        pattern=re.compile(r"\b(credit_card|cc_number|card_number|cvv|cvc|card_cvc)\b", re.IGNORECASE),
        data_type=SensitiveDataType.FINANCIAL,
        description="Credit card field access detected",
        columns=["credit_card", "cc_number", "card_number", "cvv", "cvc"],
    ),
    SensitiveDataPattern(
        id="sensitive_bank",
        pattern=re.compile(r"\b(bank_account|account_number|routing_number|iban|swift_code)\b", re.IGNORECASE),
        data_type=SensitiveDataType.FINANCIAL,
        description="Bank account field access detected",
        columns=["bank_account", "account_number", "routing_number", "iban"],
    ),

    # Legal identifiers
    SensitiveDataPattern(
        id="sensitive_ssn",
        pattern=re.compile(r"\b(ssn|social_security|social_security_number|national_id)\b", re.IGNORECASE),
        data_type=SensitiveDataType.LEGAL,
        description="Social Security Number field access detected",
        columns=["ssn", "social_security", "social_security_number"],
    ),
    SensitiveDataPattern(
        id="sensitive_passport",
        pattern=re.compile(r"\b(passport|passport_number|passport_id|visa_number)\b", re.IGNORECASE),
        data_type=SensitiveDataType.LEGAL,
        description="Passport/visa field access detected",
        columns=["passport", "passport_number", "passport_id"],
    ),
    SensitiveDataPattern(
        id="sensitive_drivers",
        pattern=re.compile(r"\b(drivers_license|driver_license|license_number|dl_number)\b", re.IGNORECASE),
        data_type=SensitiveDataType.LEGAL,
        description="Driver's license field access detected",
        columns=["drivers_license", "driver_license", "license_number"],
    ),

    # PII
    SensitiveDataPattern(
        id="sensitive_dob",
        pattern=re.compile(r"\b(date_of_birth|dob|birth_date|birthdate)\b", re.IGNORECASE),
        data_type=SensitiveDataType.PII,
        description="Date of birth field access detected",
        columns=["date_of_birth", "dob", "birth_date"],
    ),
    SensitiveDataPattern(
        id="sensitive_address",
        pattern=re.compile(r"\b(home_address|street_address|full_address|residential_address)\b", re.IGNORECASE),
        data_type=SensitiveDataType.PII,
        description="Home address field access detected",
        columns=["home_address", "street_address", "full_address"],
    ),
    SensitiveDataPattern(
        id="sensitive_phone",
        pattern=re.compile(r"\b(phone_number|mobile_number|cell_phone|telephone)\b", re.IGNORECASE),
        data_type=SensitiveDataType.PII,
        description="Phone number field access detected",
        columns=["phone_number", "mobile_number", "cell_phone"],
    ),
    SensitiveDataPattern(
        id="sensitive_email",
        pattern=re.compile(r"\b(email|email_address|personal_email)\b", re.IGNORECASE),
        data_type=SensitiveDataType.PII,
        description="Email field access detected",
        columns=["email", "email_address", "personal_email"],
    ),

    # Health data (HIPAA)
    SensitiveDataPattern(
        id="sensitive_health",
        pattern=re.compile(r"\b(medical_record|health_data|diagnosis|prescription|patient_id|mrn)\b", re.IGNORECASE),
        data_type=SensitiveDataType.HEALTH,
        description="Health/medical field access detected (HIPAA)",
        columns=["medical_record", "health_data", "diagnosis", "prescription", "patient_id"],
    ),
]

# Combine all detection patterns
ALL_DETECTION_PATTERNS = (
    SQL_INJECTION_PATTERNS +
    DESTRUCTIVE_PATTERNS +
    SCHEMA_PATTERNS +
    EXCESSIVE_DATA_PATTERNS
)


def get_patterns_by_risk(min_risk: RiskLevel) -> List[DetectionPattern]:
    """Get all patterns at or above a risk level."""
    risk_order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    min_index = risk_order.index(min_risk)
    return [
        p for p in ALL_DETECTION_PATTERNS
        if risk_order.index(p.risk_level) >= min_index
    ]


def get_patterns_by_type(violation_type: ViolationType) -> List[DetectionPattern]:
    """Get all patterns for a specific violation type."""
    return [
        p for p in ALL_DETECTION_PATTERNS
        if p.violation_type == violation_type
    ]
