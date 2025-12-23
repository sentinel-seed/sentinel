/**
 * Sentinel Guard - Detection Patterns
 *
 * Patterns for detecting secrets, PII, and other sensitive data.
 * Adapted from VS Code extension for browser use.
 */

export interface PatternMatch {
  type: string;
  value: string;
  start: number;
  end: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
}

// API Keys and Tokens
export const SECRET_PATTERNS: Record<string, RegExp> = {
  // AWS
  aws_access_key: /AKIA[0-9A-Z]{16}/g,
  aws_secret_key: /(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])/g,

  // GitHub
  github_token: /ghp_[a-zA-Z0-9]{36}/g,
  github_oauth: /gho_[a-zA-Z0-9]{36}/g,
  github_app: /(?:ghu|ghs)_[a-zA-Z0-9]{36}/g,

  // OpenAI
  openai_key: /sk-[a-zA-Z0-9]{48}/g,
  openai_project: /sk-proj-[a-zA-Z0-9-_]{80,}/g,

  // Anthropic
  anthropic_key: /sk-ant-[a-zA-Z0-9-]{95}/g,

  // Google
  google_api_key: /AIza[0-9A-Za-z-_]{35}/g,

  // Stripe
  stripe_secret: /sk_live_[0-9a-zA-Z]{24}/g,
  stripe_publishable: /pk_live_[0-9a-zA-Z]{24}/g,

  // Generic patterns
  api_key_generic: /(?:api[_-]?key|apikey)['":\s=]+['"]?([a-zA-Z0-9-_]{20,})['"]?/gi,
  bearer_token: /Bearer\s+[a-zA-Z0-9-_.~+/]+=*/g,
  basic_auth: /Basic\s+[a-zA-Z0-9+/]+=*/g,

  // Private keys
  private_key_header: /-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----/g,
  private_key_ec: /-----BEGIN\s+EC\s+PRIVATE\s+KEY-----/g,

  // Database
  connection_string: /(?:mongodb|postgres|mysql|redis):\/\/[^\s'"]+/gi,
};

// Crypto-specific patterns
export const CRYPTO_PATTERNS: Record<string, RegExp> = {
  // Ethereum
  eth_private_key: /0x[a-fA-F0-9]{64}/g,

  // Seed phrases (BIP39)
  seed_phrase_12: /\b(?:[a-z]+\s+){11}[a-z]+\b/gi,
  seed_phrase_24: /\b(?:[a-z]+\s+){23}[a-z]+\b/gi,

  // Solana
  solana_private_key: /[1-9A-HJ-NP-Za-km-z]{87,88}/g,
};

// Personal Identifiable Information
export const PII_PATTERNS: Record<string, RegExp> = {
  // Email
  email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,

  // Phone numbers
  phone_us: /\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g,
  phone_br: /\b(?:\+55[-.\s]?)?\(?\d{2}\)?[-.\s]?\d{4,5}[-.\s]?\d{4}\b/g,
  phone_intl: /\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}/g,

  // ID numbers
  ssn: /\b\d{3}-\d{2}-\d{4}\b/g,
  cpf: /\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g,

  // Financial
  credit_card: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,

  // Passwords in context
  password_context:
    /(?:password|passwd|pwd|senha)['":\s=]+['"]?([^\s'"]{6,})['"]?/gi,
};

// Severity mapping
const SEVERITY_MAP: Record<string, PatternMatch['severity']> = {
  aws_access_key: 'critical',
  aws_secret_key: 'critical',
  openai_key: 'critical',
  anthropic_key: 'critical',
  private_key_header: 'critical',
  eth_private_key: 'critical',
  seed_phrase_12: 'critical',
  seed_phrase_24: 'critical',
  solana_private_key: 'critical',
  github_token: 'high',
  stripe_secret: 'high',
  connection_string: 'high',
  password_context: 'high',
  credit_card: 'high',
  ssn: 'high',
  cpf: 'high',
  api_key_generic: 'medium',
  bearer_token: 'medium',
  email: 'low',
  phone_us: 'low',
  phone_br: 'low',
};

// Human-readable messages
const MESSAGES: Record<string, string> = {
  aws_access_key: 'AWS Access Key detected',
  aws_secret_key: 'Potential AWS Secret Key detected',
  openai_key: 'OpenAI API Key detected',
  anthropic_key: 'Anthropic API Key detected',
  github_token: 'GitHub Personal Access Token detected',
  private_key_header: 'Private Key detected',
  eth_private_key: 'Ethereum Private Key detected',
  seed_phrase_12: 'Potential seed phrase (12 words) detected',
  seed_phrase_24: 'Potential seed phrase (24 words) detected',
  solana_private_key: 'Potential Solana Private Key detected',
  password_context: 'Password detected in text',
  credit_card: 'Credit card number detected',
  ssn: 'Social Security Number detected',
  cpf: 'CPF (Brazilian ID) detected',
  email: 'Email address detected',
  connection_string: 'Database connection string detected',
};

/**
 * Scan text for secrets and sensitive data
 */
export function scanForSecrets(text: string): PatternMatch[] {
  const matches: PatternMatch[] = [];

  // Check secret patterns
  for (const [type, pattern] of Object.entries(SECRET_PATTERNS)) {
    const regex = new RegExp(pattern.source, pattern.flags);
    let match;

    while ((match = regex.exec(text)) !== null) {
      matches.push({
        type,
        value: match[0],
        start: match.index,
        end: match.index + match[0].length,
        severity: SEVERITY_MAP[type] || 'medium',
        message: MESSAGES[type] || `${type} detected`,
      });
    }
  }

  // Check crypto patterns
  for (const [type, pattern] of Object.entries(CRYPTO_PATTERNS)) {
    const regex = new RegExp(pattern.source, pattern.flags);
    let match;

    while ((match = regex.exec(text)) !== null) {
      // Skip if likely not a real seed phrase (common words)
      if (type.startsWith('seed_phrase')) {
        const words = match[0].toLowerCase().split(/\s+/);
        const commonWords = ['the', 'and', 'for', 'are', 'but', 'not', 'you'];
        const hasCommon = words.some((w) => commonWords.includes(w));
        if (hasCommon) continue;
      }

      matches.push({
        type,
        value: match[0],
        start: match.index,
        end: match.index + match[0].length,
        severity: SEVERITY_MAP[type] || 'critical',
        message: MESSAGES[type] || `${type} detected`,
      });
    }
  }

  return matches;
}

/**
 * Scan text for PII
 */
export function scanForPII(text: string): PatternMatch[] {
  const matches: PatternMatch[] = [];

  for (const [type, pattern] of Object.entries(PII_PATTERNS)) {
    const regex = new RegExp(pattern.source, pattern.flags);
    let match;

    while ((match = regex.exec(text)) !== null) {
      matches.push({
        type,
        value: match[0],
        start: match.index,
        end: match.index + match[0].length,
        severity: SEVERITY_MAP[type] || 'medium',
        message: MESSAGES[type] || `${type} detected`,
      });
    }
  }

  return matches;
}

/**
 * Scan text for all sensitive data
 */
export function scanAll(text: string): PatternMatch[] {
  const secrets = scanForSecrets(text);
  const pii = scanForPII(text);

  // Deduplicate overlapping matches
  const all = [...secrets, ...pii];
  return all.sort((a, b) => b.severity.localeCompare(a.severity));
}

/**
 * Mask sensitive data in text
 */
export function maskSensitiveData(
  text: string,
  matches: PatternMatch[]
): string {
  let result = text;

  // Sort by position (reverse) to maintain indices
  const sorted = [...matches].sort((a, b) => b.start - a.start);

  for (const match of sorted) {
    const masked = match.value.substring(0, 4) + '****';
    result = result.substring(0, match.start) + masked + result.substring(match.end);
  }

  return result;
}
