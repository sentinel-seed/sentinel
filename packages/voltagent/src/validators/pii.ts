/**
 * @sentinelseed/voltagent - PII Validator
 *
 * Detects and redacts Personally Identifiable Information (PII) from content.
 * Supports emails, phone numbers, SSNs, credit cards, IP addresses, and more.
 *
 * Key features:
 * - Detection: Identify PII in text
 * - Redaction: Replace PII with placeholder text
 * - Streaming: Process text chunks efficiently
 */

import type {
  PIIDetectionResult,
  PIIType,
  PIIMatch,
  PIIPatternDefinition,
} from '../types';

// =============================================================================
// Pattern Definitions
// =============================================================================

/**
 * PII detection patterns with redaction formats.
 */
const PII_PATTERNS: PIIPatternDefinition[] = [
  // Email addresses
  {
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    type: 'EMAIL',
    redactionFormat: '[EMAIL]',
  },

  // Phone numbers (various formats)
  {
    pattern: /\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g,
    type: 'PHONE',
    redactionFormat: '[PHONE]',
  },
  {
    pattern: /\b\+?[1-9]\d{1,14}\b/g,
    type: 'PHONE',
    redactionFormat: '[PHONE]',
    partialMatch: true,
  },

  // Social Security Numbers
  {
    pattern: /\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b/g,
    type: 'SSN',
    redactionFormat: '[SSN]',
  },

  // Credit Card Numbers (Visa, MasterCard, Amex, Discover)
  {
    pattern: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/g,
    type: 'CREDIT_CARD',
    redactionFormat: '[CREDIT_CARD]',
  },
  {
    pattern: /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g,
    type: 'CREDIT_CARD',
    redactionFormat: '[CREDIT_CARD]',
  },

  // IP Addresses (IPv4)
  {
    pattern: /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g,
    type: 'IP_ADDRESS',
    redactionFormat: '[IP_ADDRESS]',
  },

  // IPv6 Addresses
  {
    pattern: /\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b/g,
    type: 'IP_ADDRESS',
    redactionFormat: '[IP_ADDRESS]',
  },

  // Date of Birth patterns
  {
    pattern: /\b(?:0[1-9]|1[0-2])[-\/](?:0[1-9]|[12][0-9]|3[01])[-\/](?:19|20)\d{2}\b/g,
    type: 'DATE_OF_BIRTH',
    redactionFormat: '[DOB]',
  },
  {
    pattern: /\b(?:19|20)\d{2}[-\/](?:0[1-9]|1[0-2])[-\/](?:0[1-9]|[12][0-9]|3[01])\b/g,
    type: 'DATE_OF_BIRTH',
    redactionFormat: '[DOB]',
  },

  // API Keys (common patterns)
  {
    pattern: /\b[a-zA-Z0-9_-]{32,64}\b/g,
    type: 'API_KEY',
    redactionFormat: '[API_KEY]',
    partialMatch: true,
  },

  // AWS Access Key ID
  {
    pattern: /\bAKIA[0-9A-Z]{16}\b/g,
    type: 'AWS_KEY',
    redactionFormat: '[AWS_KEY]',
  },

  // AWS Secret Access Key
  {
    pattern: /\b[0-9a-zA-Z/+]{40}\b/g,
    type: 'AWS_KEY',
    redactionFormat: '[AWS_SECRET]',
    partialMatch: true,
  },

  // Private Keys
  {
    pattern: /-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[\s\S]+?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----/g,
    type: 'PRIVATE_KEY',
    redactionFormat: '[PRIVATE_KEY]',
  },

  // JWT Tokens
  {
    pattern: /\beyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b/g,
    type: 'JWT_TOKEN',
    redactionFormat: '[JWT_TOKEN]',
  },

  // Passport Numbers (US format)
  {
    pattern: /\b[A-Z]\d{8}\b/g,
    type: 'PASSPORT',
    redactionFormat: '[PASSPORT]',
  },

  // Driver License (generic pattern)
  {
    pattern: /\b[A-Z]{1,2}\d{6,8}\b/g,
    type: 'DRIVER_LICENSE',
    redactionFormat: '[DRIVER_LICENSE]',
    partialMatch: true,
  },
];

// =============================================================================
// Detection Functions
// =============================================================================

/**
 * Detect PII in content.
 *
 * @param content - Text to scan for PII
 * @param types - Optional array of specific PII types to detect
 * @param customPatterns - Optional custom patterns to include
 * @returns PIIDetectionResult with all matches
 *
 * @example
 * ```typescript
 * const result = detectPII("Contact me at john@example.com or 555-123-4567");
 * console.log(result.detected); // true
 * console.log(result.types); // ['EMAIL', 'PHONE']
 * console.log(result.count); // 2
 * ```
 */
export function detectPII(
  content: string,
  types?: PIIType[],
  customPatterns?: PIIPatternDefinition[]
): PIIDetectionResult {
  // Handle invalid input
  if (!content || typeof content !== 'string') {
    return {
      detected: false,
      types: [],
      matches: [],
      count: 0,
    };
  }

  const matches: PIIMatch[] = [];
  const typeSet = new Set<PIIType>();

  // Determine which patterns to use
  let patternsToCheck = PII_PATTERNS;
  if (types && types.length > 0) {
    patternsToCheck = PII_PATTERNS.filter((p) => types.includes(p.type));
  }

  // Add custom patterns
  if (customPatterns) {
    patternsToCheck = [...patternsToCheck, ...customPatterns];
  }

  // Check each pattern
  for (const { pattern, type } of patternsToCheck) {
    // Clone regex to avoid state issues with global flag
    const regex = new RegExp(pattern.source, pattern.flags);
    let match;

    while ((match = regex.exec(content)) !== null) {
      // Avoid false positives for partial match patterns
      if (isLikelyFalsePositive(match[0], type)) {
        continue;
      }

      typeSet.add(type);
      matches.push({
        type,
        value: match[0],
        start: match.index,
        end: match.index + match[0].length,
        confidence: calculateConfidence(match[0], type),
      });
    }
  }

  // Deduplicate overlapping matches
  const deduplicatedMatches = deduplicateMatches(matches);

  return {
    detected: deduplicatedMatches.length > 0,
    types: Array.from(typeSet),
    matches: deduplicatedMatches,
    count: deduplicatedMatches.length,
  };
}

/**
 * Quick check for any PII presence.
 * Faster than full detection, doesn't return match details.
 *
 * @param content - Text to check
 * @returns true if any PII is detected
 */
export function hasPII(content: string): boolean {
  if (!content || typeof content !== 'string') {
    return false;
  }

  // Quick patterns for common PII
  const quickPatterns = [
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email
    /\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b/, // SSN
    /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b/, // Credit card
    /\bAKIA[0-9A-Z]{16}\b/, // AWS key
    /-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----/, // Private key
  ];

  return quickPatterns.some((p) => p.test(content));
}

// =============================================================================
// Redaction Functions
// =============================================================================

/**
 * Redact PII from content.
 *
 * @param content - Text containing PII
 * @param types - Optional array of specific PII types to redact
 * @param customFormat - Optional custom redaction format
 * @returns Text with PII replaced by redaction placeholders
 *
 * @example
 * ```typescript
 * const redacted = redactPII("Email: john@example.com, Phone: 555-123-4567");
 * console.log(redacted); // "Email: [EMAIL], Phone: [PHONE]"
 * ```
 */
export function redactPII(
  content: string,
  types?: PIIType[],
  customFormat?: string | ((type: PIIType, value: string) => string)
): string {
  if (!content || typeof content !== 'string') {
    return content ?? '';
  }

  // Detect all PII first
  const detection = detectPII(content, types);

  if (!detection.detected) {
    return content;
  }

  // Sort matches by position (descending) to replace from end to start
  const sortedMatches = [...detection.matches].sort((a, b) => b.start - a.start);

  let result = content;

  for (const match of sortedMatches) {
    const replacement = getRedactionText(match.type, match.value, customFormat);
    result = result.substring(0, match.start) + replacement + result.substring(match.end);
  }

  return result;
}

/**
 * Redact PII with partial masking (preserve format).
 * Useful when you want to keep some context.
 *
 * @param content - Text containing PII
 * @returns Text with partially masked PII
 *
 * @example
 * ```typescript
 * const masked = maskPII("Email: john@example.com");
 * console.log(masked); // "Email: j***@example.com"
 * ```
 */
export function maskPII(content: string): string {
  if (!content || typeof content !== 'string') {
    return content ?? '';
  }

  let result = content;

  // Mask emails: keep first char and domain
  result = result.replace(
    /\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b/gi,
    '$1***@$2'
  );

  // Mask phone numbers: keep last 4 digits
  result = result.replace(
    /\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?(\d{4})\b/g,
    '***-***-$1'
  );

  // Mask SSN: keep last 4 digits
  result = result.replace(
    /\b\d{3}[-\s]?\d{2}[-\s]?(\d{4})\b/g,
    '***-**-$1'
  );

  // Mask credit cards: keep last 4 digits
  result = result.replace(
    /\b(?:\d{4}[-\s]?){3}(\d{4})\b/g,
    '****-****-****-$1'
  );

  return result;
}

// =============================================================================
// Streaming Support
// =============================================================================

/**
 * Create a PII redaction function for streaming content.
 * Maintains state across chunks for accurate detection.
 *
 * @param types - Optional PII types to redact
 * @returns Function that processes text chunks
 */
export function createStreamingRedactor(
  types?: PIIType[]
): (chunk: string, buffer: string) => { output: string; newBuffer: string } {
  return (chunk: string, buffer: string) => {
    // Combine buffer with new chunk
    const combined = buffer + chunk;

    // Find a safe split point (avoid splitting in middle of potential PII)
    const splitPoint = findSafeSplitPoint(combined);

    // Process the safe portion
    const toProcess = combined.substring(0, splitPoint);
    const newBuffer = combined.substring(splitPoint);

    // Redact PII in the safe portion
    const output = redactPII(toProcess, types);

    return { output, newBuffer };
  };
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get redaction text for a PII type.
 */
function getRedactionText(
  type: PIIType,
  value: string,
  customFormat?: string | ((type: PIIType, value: string) => string)
): string {
  if (customFormat) {
    if (typeof customFormat === 'function') {
      return customFormat(type, value);
    }
    return customFormat;
  }

  // Find the pattern definition for the type
  const patternDef = PII_PATTERNS.find((p) => p.type === type);
  return patternDef?.redactionFormat ?? `[${type}]`;
}

/**
 * Calculate confidence score for a match.
 */
function calculateConfidence(value: string, type: PIIType): number {
  // Higher confidence for more specific patterns
  switch (type) {
    case 'EMAIL':
      return value.includes('@') ? 0.95 : 0.5;
    case 'SSN':
      return /^\d{3}-\d{2}-\d{4}$/.test(value) ? 0.95 : 0.8;
    case 'CREDIT_CARD':
      return luhnCheck(value.replace(/\D/g, '')) ? 0.95 : 0.7;
    case 'AWS_KEY':
      return value.startsWith('AKIA') ? 0.98 : 0.7;
    case 'PRIVATE_KEY':
      return 0.99;
    case 'JWT_TOKEN':
      return value.split('.').length === 3 ? 0.95 : 0.5;
    default:
      return 0.8;
  }
}

/**
 * Check if a match is likely a false positive.
 */
function isLikelyFalsePositive(value: string, type: PIIType): boolean {
  // Too short for most PII types
  if (value.length < 5) {
    return true;
  }

  // API keys - avoid matching common words
  if (type === 'API_KEY') {
    const lowerValue = value.toLowerCase();
    const commonWords = ['function', 'constructor', 'prototype', 'undefined'];
    if (commonWords.some((word) => lowerValue.includes(word))) {
      return true;
    }
  }

  return false;
}

/**
 * Deduplicate overlapping matches (keep higher confidence).
 */
function deduplicateMatches(matches: PIIMatch[]): PIIMatch[] {
  if (matches.length <= 1) {
    return matches;
  }

  // Sort by start position
  const sorted = [...matches].sort((a, b) => a.start - b.start);
  const result: PIIMatch[] = [];

  for (const match of sorted) {
    const lastMatch = result[result.length - 1];

    // Check for overlap with last match
    if (lastMatch && match.start < lastMatch.end) {
      // Keep the one with higher confidence
      if (match.confidence > lastMatch.confidence) {
        result[result.length - 1] = match;
      }
    } else {
      result.push(match);
    }
  }

  return result;
}

/**
 * Find a safe point to split text for streaming.
 * Avoids splitting in the middle of potential PII.
 */
function findSafeSplitPoint(text: string): number {
  // If text is short, process it all
  if (text.length < 50) {
    return text.length;
  }

  // Look for natural break points (whitespace, punctuation) near the end
  const minKeep = 50; // Keep at least 50 chars in buffer
  const searchStart = Math.max(0, text.length - minKeep);

  // Find last whitespace in the safe zone
  for (let i = text.length - 1; i >= searchStart; i--) {
    if (/\s/.test(text[i] ?? '')) {
      return i + 1;
    }
  }

  // No good split point found, keep more in buffer
  return searchStart;
}

/**
 * Luhn algorithm for credit card validation.
 */
function luhnCheck(value: string): boolean {
  if (!/^\d+$/.test(value)) {
    return false;
  }

  let sum = 0;
  let isEven = false;

  for (let i = value.length - 1; i >= 0; i--) {
    let digit = parseInt(value[i] ?? '0', 10);

    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }

    sum += digit;
    isEven = !isEven;
  }

  return sum % 10 === 0;
}

// =============================================================================
// Pattern Access
// =============================================================================

/**
 * Get patterns for a specific PII type.
 */
export function getPatternsForType(type: PIIType): PIIPatternDefinition[] {
  return PII_PATTERNS.filter((p) => p.type === type);
}

/**
 * Get all supported PII types.
 */
export function getSupportedTypes(): PIIType[] {
  return [...new Set(PII_PATTERNS.map((p) => p.type))];
}

/**
 * Get total pattern count.
 */
export function getPatternCount(): number {
  return PII_PATTERNS.length;
}
