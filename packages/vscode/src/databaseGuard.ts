/**
 * Database Guard: SQL Injection Detection for LLM Prompts
 *
 * Detects SQL injection patterns in prompts that might be:
 * 1. User trying to inject SQL through LLM
 * 2. LLM generating unsafe SQL
 * 3. Prompts containing SQL that could be executed
 */

export interface SqlInjectionResult {
    hasSqlInjection: boolean;
    findings: SqlFinding[];
    severity: 'none' | 'low' | 'medium' | 'high' | 'critical';
    sanitizedText?: string;
}

export interface SqlFinding {
    pattern: string;
    matchedText: string;
    category: SqlCategory;
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    position: { start: number; end: number };
}

export type SqlCategory =
    | 'destructive'
    | 'data_extraction'
    | 'authentication_bypass'
    | 'union_attack'
    | 'comment_injection'
    | 'stacked_queries'
    | 'blind_injection'
    | 'error_based';

interface SqlPattern {
    regex: RegExp;
    category: SqlCategory;
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
}

const SQL_PATTERNS: SqlPattern[] = [
    // Destructive operations (CRITICAL)
    {
        regex: /\b(DROP|TRUNCATE|DELETE\s+FROM|ALTER)\s+(TABLE|DATABASE|SCHEMA|INDEX)\b/gi,
        category: 'destructive',
        severity: 'critical',
        description: 'Destructive SQL command detected'
    },
    {
        regex: /\bDROP\s+ALL\b/gi,
        category: 'destructive',
        severity: 'critical',
        description: 'DROP ALL command detected'
    },
    {
        regex: /\bDELETE\s+FROM\s+\w+\s*(WHERE\s+1\s*=\s*1|WHERE\s+TRUE|;)\s*/gi,
        category: 'destructive',
        severity: 'critical',
        description: 'DELETE with always-true condition'
    },
    {
        regex: /\bUPDATE\s+\w+\s+SET\s+.+\s+WHERE\s+(1\s*=\s*1|TRUE|''='')/gi,
        category: 'destructive',
        severity: 'critical',
        description: 'UPDATE with always-true condition'
    },

    // UNION attacks (HIGH)
    {
        regex: /\bUNION\s+(ALL\s+)?SELECT\b/gi,
        category: 'union_attack',
        severity: 'high',
        description: 'UNION SELECT injection attempt'
    },
    {
        regex: /\bUNION\s+(ALL\s+)?SELECT\s+.*(password|passwd|pwd|secret|token|key|hash)/gi,
        category: 'union_attack',
        severity: 'critical',
        description: 'UNION SELECT targeting credentials'
    },

    // Authentication bypass (HIGH)
    {
        regex: /'\s*(OR|AND)\s*'[^']*'\s*=\s*'[^']*'/gi,
        category: 'authentication_bypass',
        severity: 'high',
        description: 'String comparison bypass pattern'
    },
    {
        regex: /'\s*(OR|AND)\s+\d+\s*=\s*\d+/gi,
        category: 'authentication_bypass',
        severity: 'high',
        description: 'Numeric comparison bypass pattern'
    },
    {
        regex: /'\s*OR\s+'[a-z]+'='[a-z]+/gi,
        category: 'authentication_bypass',
        severity: 'high',
        description: 'OR-based authentication bypass'
    },
    {
        regex: /admin'\s*--/gi,
        category: 'authentication_bypass',
        severity: 'high',
        description: 'Admin login bypass attempt'
    },
    {
        regex: /'\s*OR\s+1\s*=\s*1\s*(--|#|\/\*)/gi,
        category: 'authentication_bypass',
        severity: 'high',
        description: 'Classic OR 1=1 bypass'
    },

    // Comment injection (MEDIUM)
    {
        regex: /--\s*$/gm,
        category: 'comment_injection',
        severity: 'medium',
        description: 'SQL line comment at end'
    },
    {
        regex: /#\s*$/gm,
        category: 'comment_injection',
        severity: 'medium',
        description: 'MySQL comment at end'
    },
    {
        regex: /\/\*.*?\*\//gs,
        category: 'comment_injection',
        severity: 'medium',
        description: 'Block comment detected'
    },
    {
        regex: /\/\*![0-9]*.*?\*\//gs,
        category: 'comment_injection',
        severity: 'high',
        description: 'MySQL version-specific comment'
    },

    // Stacked queries (HIGH)
    {
        regex: /;\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)/gi,
        category: 'stacked_queries',
        severity: 'high',
        description: 'Stacked query detected'
    },
    {
        regex: /;\s*WAITFOR\s+DELAY/gi,
        category: 'stacked_queries',
        severity: 'high',
        description: 'Time-based injection (WAITFOR)'
    },
    {
        regex: /;\s*SLEEP\s*\(/gi,
        category: 'stacked_queries',
        severity: 'high',
        description: 'Time-based injection (SLEEP)'
    },

    // Data extraction (HIGH)
    {
        regex: /\bSELECT\s+.*(FROM\s+information_schema|FROM\s+mysql\.|FROM\s+pg_)/gi,
        category: 'data_extraction',
        severity: 'high',
        description: 'Schema enumeration attempt'
    },
    {
        regex: /\bSELECT\s+.*@@(version|user|database)/gi,
        category: 'data_extraction',
        severity: 'medium',
        description: 'Database info extraction'
    },
    {
        regex: /\bSELECT\s+.*\bLOAD_FILE\s*\(/gi,
        category: 'data_extraction',
        severity: 'critical',
        description: 'File read attempt (LOAD_FILE)'
    },
    {
        regex: /\bINTO\s+(OUT|DUMP)FILE\b/gi,
        category: 'data_extraction',
        severity: 'critical',
        description: 'File write attempt (INTO OUTFILE)'
    },
    {
        regex: /\bSELECT\s+.*\bpg_read_file\s*\(/gi,
        category: 'data_extraction',
        severity: 'critical',
        description: 'PostgreSQL file read attempt'
    },

    // Blind injection (MEDIUM)
    {
        regex: /\b(AND|OR)\s+\d+\s*(=|<|>|!=|<>)\s*\d+/gi,
        category: 'blind_injection',
        severity: 'medium',
        description: 'Boolean-based blind injection'
    },
    {
        regex: /\bCASE\s+WHEN\s+.+\s+THEN\s+.+\s+ELSE\b/gi,
        category: 'blind_injection',
        severity: 'medium',
        description: 'CASE-based blind injection'
    },
    {
        regex: /\bIF\s*\(\s*.+\s*,\s*.+\s*,\s*.+\s*\)/gi,
        category: 'blind_injection',
        severity: 'medium',
        description: 'IF-based blind injection'
    },
    {
        regex: /\bSUBSTRING\s*\(\s*\(\s*SELECT\b/gi,
        category: 'blind_injection',
        severity: 'high',
        description: 'Substring extraction from subquery'
    },

    // Error-based injection (MEDIUM)
    {
        regex: /\bEXTRACTVALUE\s*\(/gi,
        category: 'error_based',
        severity: 'medium',
        description: 'XML error-based injection'
    },
    {
        regex: /\bUPDATEXML\s*\(/gi,
        category: 'error_based',
        severity: 'medium',
        description: 'XML error-based injection'
    },
    {
        regex: /\bEXP\s*\(\s*~\s*\(/gi,
        category: 'error_based',
        severity: 'medium',
        description: 'Double query error injection'
    },

    // Additional dangerous patterns
    {
        regex: /\bEXEC(UTE)?\s+(sp_|xp_)/gi,
        category: 'destructive',
        severity: 'critical',
        description: 'SQL Server stored procedure execution'
    },
    {
        regex: /\bxp_cmdshell\b/gi,
        category: 'destructive',
        severity: 'critical',
        description: 'Command shell execution attempt'
    },
    {
        regex: /\bDBMS_PIPE\b/gi,
        category: 'data_extraction',
        severity: 'high',
        description: 'Oracle DBMS_PIPE access'
    },
    {
        regex: /\bUTL_HTTP\b/gi,
        category: 'data_extraction',
        severity: 'high',
        description: 'Oracle UTL_HTTP access'
    },

    // Hex/char encoding (often used to bypass filters)
    {
        regex: /0x[0-9a-f]{8,}/gi,
        category: 'blind_injection',
        severity: 'medium',
        description: 'Hex-encoded payload detected'
    },
    {
        regex: /\bCHAR\s*\(\s*\d+\s*(,\s*\d+\s*)+\)/gi,
        category: 'blind_injection',
        severity: 'medium',
        description: 'CHAR encoding detected'
    },
    {
        regex: /\bCONCAT\s*\(\s*CHAR\s*\(/gi,
        category: 'blind_injection',
        severity: 'medium',
        description: 'CONCAT with CHAR encoding'
    }
];

export class DatabaseGuard {
    /**
     * Scan text for SQL injection patterns
     */
    public scan(text: string): SqlInjectionResult {
        const findings: SqlFinding[] = [];

        for (const pattern of SQL_PATTERNS) {
            let match;
            pattern.regex.lastIndex = 0; // Reset regex state

            while ((match = pattern.regex.exec(text)) !== null) {
                findings.push({
                    pattern: pattern.regex.source,
                    matchedText: match[0],
                    category: pattern.category,
                    severity: pattern.severity,
                    description: pattern.description,
                    position: {
                        start: match.index,
                        end: match.index + match[0].length
                    }
                });
            }
        }

        // Deduplicate overlapping findings
        const deduped = this.deduplicateFindings(findings);

        // Calculate overall severity
        const severity = this.calculateSeverity(deduped);

        return {
            hasSqlInjection: deduped.length > 0,
            findings: deduped,
            severity
        };
    }

    /**
     * Quick check without detailed findings
     */
    public hasSqlInjection(text: string): boolean {
        for (const pattern of SQL_PATTERNS) {
            pattern.regex.lastIndex = 0;
            if (pattern.regex.test(text)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Get findings grouped by category
     */
    public scanByCategory(text: string): Record<SqlCategory, SqlFinding[]> {
        const result = this.scan(text);
        const grouped: Record<SqlCategory, SqlFinding[]> = {
            destructive: [],
            data_extraction: [],
            authentication_bypass: [],
            union_attack: [],
            comment_injection: [],
            stacked_queries: [],
            blind_injection: [],
            error_based: []
        };

        for (const finding of result.findings) {
            grouped[finding.category].push(finding);
        }

        return grouped;
    }

    private deduplicateFindings(findings: SqlFinding[]): SqlFinding[] {
        // Sort by position
        findings.sort((a, b) => a.position.start - b.position.start);

        const result: SqlFinding[] = [];
        let lastEnd = -1;

        for (const finding of findings) {
            // If this finding starts after the last one ended, include it
            if (finding.position.start >= lastEnd) {
                result.push(finding);
                lastEnd = finding.position.end;
            } else if (this.severityRank(finding.severity) > this.severityRank(result[result.length - 1]?.severity || 'low')) {
                // If overlapping but higher severity, replace
                result[result.length - 1] = finding;
                lastEnd = finding.position.end;
            }
        }

        return result;
    }

    private severityRank(severity: string): number {
        const ranks: Record<string, number> = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        };
        return ranks[severity] || 0;
    }

    private calculateSeverity(findings: SqlFinding[]): SqlInjectionResult['severity'] {
        if (findings.length === 0) {return 'none';}

        const hasCritical = findings.some(f => f.severity === 'critical');
        const hasHigh = findings.some(f => f.severity === 'high');
        const hasMedium = findings.some(f => f.severity === 'medium');

        if (hasCritical) {return 'critical';}
        if (hasHigh) {return 'high';}
        if (hasMedium) {return 'medium';}
        return 'low';
    }
}

// Singleton instance
export const databaseGuard = new DatabaseGuard();
