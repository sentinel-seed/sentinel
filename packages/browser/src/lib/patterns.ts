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

// BIP39 wordlist (2048 words) - first 200 most common for quick validation
// Full list at: https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt
const BIP39_COMMON_WORDS = new Set([
  'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract',
  'absurd', 'abuse', 'access', 'accident', 'account', 'accuse', 'achieve', 'acid',
  'acoustic', 'acquire', 'across', 'act', 'action', 'actor', 'actress', 'actual',
  'adapt', 'add', 'addict', 'address', 'adjust', 'admit', 'adult', 'advance',
  'advice', 'aerobic', 'affair', 'afford', 'afraid', 'again', 'age', 'agent',
  'agree', 'ahead', 'aim', 'air', 'airport', 'aisle', 'alarm', 'album',
  'alcohol', 'alert', 'alien', 'all', 'alley', 'allow', 'almost', 'alone',
  'alpha', 'already', 'also', 'alter', 'always', 'amateur', 'amazing', 'among',
  'amount', 'amused', 'analyst', 'anchor', 'ancient', 'anger', 'angle', 'angry',
  'animal', 'ankle', 'announce', 'annual', 'answer', 'antenna', 'antique', 'anxiety',
  'any', 'apart', 'apology', 'appear', 'apple', 'approve', 'april', 'arch',
  'area', 'arena', 'argue', 'arm', 'armed', 'armor', 'army', 'around',
  'arrange', 'arrest', 'arrive', 'arrow', 'art', 'artefact', 'artist', 'artwork',
  'ask', 'aspect', 'assault', 'asset', 'assist', 'assume', 'asthma', 'athlete',
  'atom', 'attack', 'attend', 'attitude', 'attract', 'auction', 'audit', 'august',
  'aunt', 'author', 'auto', 'autumn', 'average', 'avocado', 'avoid', 'awake',
  'aware', 'away', 'awesome', 'awful', 'awkward', 'axis', 'baby', 'bachelor',
  'bacon', 'badge', 'bag', 'balance', 'balcony', 'ball', 'bamboo', 'banana',
  'banner', 'bar', 'barely', 'bargain', 'barrel', 'base', 'basic', 'basket',
  'battle', 'beach', 'bean', 'beauty', 'because', 'become', 'beef', 'before',
  'begin', 'behave', 'behind', 'believe', 'below', 'belt', 'bench', 'benefit',
  'best', 'betray', 'better', 'between', 'beyond', 'bicycle', 'bid', 'bike',
  'bind', 'biology', 'bird', 'birth', 'bitter', 'black', 'blade', 'blame',
  'blanket', 'blast', 'bleak', 'bless', 'blind', 'blood', 'blossom', 'blouse',
  'blue', 'blur', 'blush', 'board', 'boat', 'body', 'boil', 'bomb',
  // Common non-BIP39 words that should NOT trigger seed detection
]);

// Words that commonly appear in regular text but aren't likely in seed phrases
const COMMON_TEXT_WORDS = new Set([
  'the', 'and', 'for', 'are', 'but', 'not', 'you', 'this', 'that', 'have',
  'from', 'with', 'they', 'will', 'would', 'there', 'their', 'what', 'which',
  'when', 'where', 'who', 'how', 'can', 'could', 'should', 'would', 'been',
  'was', 'were', 'has', 'had', 'does', 'did', 'just', 'very', 'more', 'most',
  'some', 'than', 'then', 'into', 'only', 'other', 'such', 'these', 'those',
  'your', 'our', 'his', 'her', 'its', 'my', 'we', 'us', 'them', 'him',
]);

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
 * Check if a sequence of words is likely a BIP39 seed phrase
 * Returns true if it looks like a real seed phrase
 */
function isLikelySeedPhrase(words: string[]): boolean {
  // Must have exactly 12 or 24 words
  if (words.length !== 12 && words.length !== 24) return false;

  // Count words that are in BIP39 wordlist vs common text words
  let bip39Count = 0;
  let commonTextCount = 0;

  for (const word of words) {
    const lower = word.toLowerCase();
    if (BIP39_COMMON_WORDS.has(lower)) bip39Count++;
    if (COMMON_TEXT_WORDS.has(lower)) commonTextCount++;
  }

  // If more than 2 common text words, likely not a seed phrase
  if (commonTextCount > 2) return false;

  // Seed phrases should have most words from BIP39 list
  // At least 50% should be recognizable BIP39 words
  const bip39Ratio = bip39Count / words.length;
  return bip39Ratio >= 0.5;
}

/**
 * Scan text for secrets and sensitive data
 */
export function scanForSecrets(text: string): PatternMatch[] {
  // Guard against null/undefined/non-string input
  if (!text || typeof text !== 'string') {
    return [];
  }

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
      // Validate seed phrases more carefully to reduce false positives
      if (type.startsWith('seed_phrase')) {
        const words = match[0].toLowerCase().split(/\s+/);
        if (!isLikelySeedPhrase(words)) continue;
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
  // Guard against null/undefined/non-string input
  if (!text || typeof text !== 'string') {
    return [];
  }

  const matches: PatternMatch[] = [];

  for (const [type, pattern] of Object.entries(PII_PATTERNS)) {
    const regex = new RegExp(pattern.source, pattern.flags);
    let match;

    while ((match = regex.exec(text)) !== null) {
      // M007: SSN pattern also matches phone numbers - add context check
      if (type === 'ssn') {
        // Check if it's preceded by phone-related context
        const before = text.substring(Math.max(0, match.index - 20), match.index).toLowerCase();
        if (before.includes('phone') || before.includes('tel') || before.includes('call') || before.includes('fax')) {
          continue;
        }
      }

      // M008: Email pattern too broad - skip code-like patterns
      if (type === 'email') {
        const value = match[0];
        // Skip if it looks like code (e.g., @decorator, @annotation)
        if (value.startsWith('@') || /^[a-z_]+@[a-z_]+\.[a-z]{2}$/i.test(value)) {
          continue;
        }
      }

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
 * Remove overlapping matches, keeping higher severity ones
 */
function deduplicateMatches(matches: PatternMatch[]): PatternMatch[] {
  if (matches.length <= 1) return matches;

  // Sort by severity (critical > high > medium > low) then by start position
  const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  const sorted = [...matches].sort((a, b) => {
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
    if (severityDiff !== 0) return severityDiff;
    return a.start - b.start;
  });

  const result: PatternMatch[] = [];
  const covered = new Set<number>();

  for (const match of sorted) {
    // Check if any position in this match is already covered
    let overlaps = false;
    for (let i = match.start; i < match.end; i++) {
      if (covered.has(i)) {
        overlaps = true;
        break;
      }
    }

    if (!overlaps) {
      result.push(match);
      // Mark all positions as covered
      for (let i = match.start; i < match.end; i++) {
        covered.add(i);
      }
    }
  }

  return result;
}

/**
 * Scan text for all sensitive data
 */
export function scanAll(text: string): PatternMatch[] {
  // Guard against null/undefined/non-string input
  if (!text || typeof text !== 'string') {
    return [];
  }

  const secrets = scanForSecrets(text);
  const pii = scanForPII(text);

  // Deduplicate overlapping matches, keeping higher severity
  const all = [...secrets, ...pii];
  const deduplicated = deduplicateMatches(all);

  // Sort by severity for display
  const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  return deduplicated.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);
}

/**
 * Mask sensitive data in text, handling overlaps correctly
 */
export function maskSensitiveData(
  text: string,
  matches: PatternMatch[]
): string {
  // Guard against null/undefined/non-string input
  if (!text || typeof text !== 'string') {
    return text ?? '';
  }

  if (!matches || !Array.isArray(matches) || matches.length === 0) {
    return text;
  }

  // First deduplicate to avoid overlap corruption
  const deduplicated = deduplicateMatches(matches);

  // Sort by position (reverse) to maintain indices while replacing
  const sorted = [...deduplicated].sort((a, b) => b.start - a.start);

  let result = text;
  for (const match of sorted) {
    // Safety check: ensure indices are within bounds
    if (match.start < 0 || match.end > result.length || match.start >= match.end) {
      continue;
    }

    const valueLen = match.end - match.start;
    const showChars = Math.min(4, Math.floor(valueLen / 2));
    const masked = match.value.substring(0, showChars) + '****';
    result = result.substring(0, match.start) + masked + result.substring(match.end);
  }

  return result;
}
