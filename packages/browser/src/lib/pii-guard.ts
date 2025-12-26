/**
 * Sentinel Guard - PII Guard
 *
 * Advanced Personal Identifiable Information detection and protection.
 * Supports multiple regions (US, BR, EU) and various document types.
 */

export interface PIIMatch {
  type: string;
  category: PIICategory;
  value: string;
  masked: string;
  start: number;
  end: number;
  region: string;
  confidence: number;
  description: string;
}

export type PIICategory =
  | 'identity'      // SSN, CPF, passport
  | 'financial'     // Credit cards, bank accounts
  | 'contact'       // Phone, email, address
  | 'health'        // Medical IDs, health info
  | 'biometric'     // Fingerprints, face data references
  | 'location'      // GPS coordinates, addresses
  | 'auth';         // Passwords, PINs

export interface PIIPattern {
  name: string;
  pattern: RegExp;
  category: PIICategory;
  region: string;
  confidence: number;
  description: string;
  validator?: (match: string) => boolean;
}

// Luhn algorithm for credit card validation
function luhnCheck(num: string): boolean {
  const digits = num.replace(/\D/g, '');
  if (digits.length < 13 || digits.length > 19) return false;

  let sum = 0;
  let isEven = false;

  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = parseInt(digits[i], 10);

    if (isEven) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }

    sum += digit;
    isEven = !isEven;
  }

  return sum % 10 === 0;
}

// CPF validation (Brazilian ID)
function validateCPF(cpf: string): boolean {
  const cleaned = cpf.replace(/\D/g, '');
  if (cleaned.length !== 11) return false;

  // Check for known invalid patterns
  if (/^(\d)\1+$/.test(cleaned)) return false;

  // Validate check digits
  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(cleaned[i], 10) * (10 - i);
  }
  let remainder = (sum * 10) % 11;
  if (remainder === 10 || remainder === 11) remainder = 0;
  if (remainder !== parseInt(cleaned[9], 10)) return false;

  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(cleaned[i], 10) * (11 - i);
  }
  remainder = (sum * 10) % 11;
  if (remainder === 10 || remainder === 11) remainder = 0;
  if (remainder !== parseInt(cleaned[10], 10)) return false;

  return true;
}

// CNPJ validation (Brazilian company ID)
function validateCNPJ(cnpj: string): boolean {
  const cleaned = cnpj.replace(/\D/g, '');
  if (cleaned.length !== 14) return false;

  if (/^(\d)\1+$/.test(cleaned)) return false;

  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(cleaned[i], 10) * weights1[i];
  }
  let remainder = sum % 11;
  const digit1 = remainder < 2 ? 0 : 11 - remainder;
  if (digit1 !== parseInt(cleaned[12], 10)) return false;

  sum = 0;
  for (let i = 0; i < 13; i++) {
    sum += parseInt(cleaned[i], 10) * weights2[i];
  }
  remainder = sum % 11;
  const digit2 = remainder < 2 ? 0 : 11 - remainder;
  if (digit2 !== parseInt(cleaned[13], 10)) return false;

  return true;
}

// All PII patterns organized by region
const PII_PATTERNS: PIIPattern[] = [
  // === IDENTITY DOCUMENTS ===

  // US
  {
    name: 'ssn',
    pattern: /\b(\d{3})-(\d{2})-(\d{4})\b/g,
    category: 'identity',
    region: 'US',
    confidence: 95,
    description: 'Social Security Number',
    validator: (m) => {
      const parts = m.split('-');
      const area = parseInt(parts[0], 10);
      // SSA doesn't issue certain area numbers
      return area !== 0 && area !== 666 && area < 900;
    },
  },
  {
    name: 'ssn_nodash',
    pattern: /\b(\d{9})\b/g,
    category: 'identity',
    region: 'US',
    confidence: 40, // Lower confidence without dashes
    description: 'Possible SSN (no dashes)',
    validator: (m) => {
      if (m.length !== 9) return false;
      const area = parseInt(m.substring(0, 3), 10);
      return area !== 0 && area !== 666 && area < 900;
    },
  },
  {
    name: 'us_passport',
    pattern: /\b[A-Z]?\d{8,9}\b/g,
    category: 'identity',
    region: 'US',
    confidence: 50,
    description: 'Possible US Passport Number',
  },
  {
    name: 'drivers_license',
    pattern: /\b[A-Z]{1,2}\d{5,8}\b/gi,
    category: 'identity',
    region: 'US',
    confidence: 40,
    description: 'Possible Driver\'s License',
  },

  // Brazil
  {
    name: 'cpf',
    pattern: /\b(\d{3})\.(\d{3})\.(\d{3})-(\d{2})\b/g,
    category: 'identity',
    region: 'BR',
    confidence: 95,
    description: 'CPF (Brazilian Individual Taxpayer ID)',
    validator: (m) => validateCPF(m),
  },
  {
    name: 'cpf_nodots',
    pattern: /\b(\d{11})\b/g,
    category: 'identity',
    region: 'BR',
    confidence: 60,
    description: 'Possible CPF (no formatting)',
    validator: (m) => m.length === 11 && validateCPF(m),
  },
  {
    name: 'cnpj',
    pattern: /\b(\d{2})\.(\d{3})\.(\d{3})\/(\d{4})-(\d{2})\b/g,
    category: 'identity',
    region: 'BR',
    confidence: 95,
    description: 'CNPJ (Brazilian Company ID)',
    validator: (m) => validateCNPJ(m),
  },
  {
    name: 'rg',
    pattern: /\b(\d{1,2})\.?(\d{3})\.?(\d{3})-?(\d|X)\b/gi,
    category: 'identity',
    region: 'BR',
    confidence: 70,
    description: 'RG (Brazilian General Registry)',
  },

  // EU
  {
    name: 'uk_nino',
    pattern: /\b[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b/gi,
    category: 'identity',
    region: 'UK',
    confidence: 90,
    description: 'UK National Insurance Number',
  },
  {
    name: 'de_personalausweis',
    pattern: /\b[CFGHJKLMNPRTVWXYZ0-9]{9}\b/g,
    category: 'identity',
    region: 'DE',
    confidence: 40, // Low confidence, needs context
    description: 'Possible German ID Card Number',
  },
  {
    name: 'fr_insee',
    pattern: /\b[12]\d{2}(0[1-9]|1[0-2])\d{8}\b/g,
    category: 'identity',
    region: 'FR',
    confidence: 85,
    description: 'French INSEE Number',
  },
  {
    name: 'es_dni',
    pattern: /\b\d{8}[A-Z]\b/gi,
    category: 'identity',
    region: 'ES',
    confidence: 85,
    description: 'Spanish DNI',
  },
  {
    name: 'it_codice_fiscale',
    pattern: /\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b/gi,
    category: 'identity',
    region: 'IT',
    confidence: 90,
    description: 'Italian Codice Fiscale',
  },

  // === FINANCIAL ===

  // Credit Cards (Global)
  {
    name: 'credit_card_visa',
    pattern: /\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g,
    category: 'financial',
    region: 'GLOBAL',
    confidence: 95,
    description: 'Visa Credit Card',
    validator: (m) => luhnCheck(m),
  },
  {
    name: 'credit_card_mastercard',
    pattern: /\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g,
    category: 'financial',
    region: 'GLOBAL',
    confidence: 95,
    description: 'Mastercard Credit Card',
    validator: (m) => luhnCheck(m),
  },
  {
    name: 'credit_card_amex',
    pattern: /\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b/g,
    category: 'financial',
    region: 'GLOBAL',
    confidence: 95,
    description: 'American Express Card',
    validator: (m) => luhnCheck(m),
  },
  {
    name: 'credit_card_discover',
    pattern: /\b6(?:011|5\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g,
    category: 'financial',
    region: 'GLOBAL',
    confidence: 95,
    description: 'Discover Card',
    validator: (m) => luhnCheck(m),
  },

  // Bank accounts
  {
    name: 'iban',
    pattern: /\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b/g,
    category: 'financial',
    region: 'EU',
    confidence: 90,
    description: 'IBAN (International Bank Account Number)',
  },
  {
    name: 'us_routing',
    pattern: /\b\d{9}\b/g,
    category: 'financial',
    region: 'US',
    confidence: 30, // Low confidence alone
    description: 'Possible US Routing Number',
  },
  {
    name: 'br_bank_account',
    pattern: /\bagencia[:\s]*(\d{4})[-\s]*conta[:\s]*(\d{5,12})-?(\d)\b/gi,
    category: 'financial',
    region: 'BR',
    confidence: 90,
    description: 'Brazilian Bank Account',
  },

  // === CONTACT INFO ===

  // Email
  {
    name: 'email',
    pattern: /\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b/g,
    category: 'contact',
    region: 'GLOBAL',
    confidence: 85,
    description: 'Email Address',
    validator: (m) => {
      // Skip obvious false positives
      if (m.includes('@example.') || m.includes('@test.')) return false;
      if (m.startsWith('@') || m.endsWith('@')) return false;
      return true;
    },
  },

  // Phone numbers
  {
    name: 'phone_us',
    pattern: /\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g,
    category: 'contact',
    region: 'US',
    confidence: 80,
    description: 'US Phone Number',
  },
  {
    name: 'phone_br',
    pattern: /\b(?:\+55[-.\s]?)?\(?\d{2}\)?[-.\s]?\d{4,5}[-.\s]?\d{4}\b/g,
    category: 'contact',
    region: 'BR',
    confidence: 80,
    description: 'Brazilian Phone Number',
  },
  {
    name: 'phone_uk',
    pattern: /\b(?:\+44[-.\s]?|0)\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b/g,
    category: 'contact',
    region: 'UK',
    confidence: 75,
    description: 'UK Phone Number',
  },
  {
    name: 'phone_intl',
    pattern: /\b\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b/g,
    category: 'contact',
    region: 'GLOBAL',
    confidence: 70,
    description: 'International Phone Number',
  },

  // Addresses
  {
    name: 'us_zip',
    pattern: /\b\d{5}(?:-\d{4})?\b/g,
    category: 'location',
    region: 'US',
    confidence: 40,
    description: 'US ZIP Code',
  },
  {
    name: 'br_cep',
    pattern: /\b\d{5}-?\d{3}\b/g,
    category: 'location',
    region: 'BR',
    confidence: 50,
    description: 'Brazilian CEP',
  },
  {
    name: 'uk_postcode',
    pattern: /\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b/gi,
    category: 'location',
    region: 'UK',
    confidence: 70,
    description: 'UK Postcode',
  },

  // === LOCATION ===

  {
    name: 'gps_coordinates',
    pattern: /\b-?\d{1,3}\.\d{4,8},\s?-?\d{1,3}\.\d{4,8}\b/g,
    category: 'location',
    region: 'GLOBAL',
    confidence: 85,
    description: 'GPS Coordinates',
  },

  // === HEALTH ===

  {
    name: 'us_medicare',
    pattern: /\b[1-9][A-Z]{1}[A-Z0-9]{1}\d{4}[A-Z]{1}\b/g,
    category: 'health',
    region: 'US',
    confidence: 80,
    description: 'US Medicare Beneficiary Identifier',
  },
  {
    name: 'br_sus',
    pattern: /\b\d{15}\b/g,
    category: 'health',
    region: 'BR',
    confidence: 40, // Low confidence, needs context
    description: 'Possible Brazilian SUS Card Number',
  },

  // === AUTH ===

  {
    name: 'password_context',
    pattern: /(?:password|passwd|pwd|senha|secret)['":\s=]+['"]?([^\s'"]{6,})['"]?/gi,
    category: 'auth',
    region: 'GLOBAL',
    confidence: 95,
    description: 'Password in Text',
  },
  {
    name: 'pin_context',
    pattern: /(?:pin|code|codigo)['":\s=]+['"]?(\d{4,6})['"]?/gi,
    category: 'auth',
    region: 'GLOBAL',
    confidence: 80,
    description: 'PIN/Code in Text',
  },
];

/**
 * Mask a PII value for display
 */
function maskValue(value: string, category: PIICategory): string {
  const len = value.length;

  switch (category) {
    case 'identity':
    case 'financial':
      // Show first 2 and last 2 characters
      if (len <= 6) return '*'.repeat(len);
      return value.slice(0, 2) + '*'.repeat(len - 4) + value.slice(-2);

    case 'contact':
      // For email, show domain
      if (value.includes('@')) {
        const [local, domain] = value.split('@');
        return local[0] + '***@' + domain;
      }
      // For phone, show last 4
      return '*'.repeat(len - 4) + value.slice(-4);

    case 'auth':
      // Never show any part of passwords/PINs
      return '*'.repeat(Math.min(len, 12));

    case 'location':
      // Partially mask
      return value.slice(0, Math.floor(len / 2)) + '*'.repeat(Math.ceil(len / 2));

    default:
      return '*'.repeat(len);
  }
}

/**
 * Scan text for all PII patterns
 */
export function scanForPII(text: string): PIIMatch[] {
  if (!text || typeof text !== 'string') {
    return [];
  }

  const matches: PIIMatch[] = [];
  const seenRanges = new Set<string>();

  for (const pattern of PII_PATTERNS) {
    const regex = new RegExp(pattern.pattern.source, pattern.pattern.flags);
    let match;

    while ((match = regex.exec(text)) !== null) {
      const value = match[0];
      const start = match.index;
      const end = start + value.length;

      // Skip if we already have a match at this position
      const rangeKey = `${start}-${end}`;
      if (seenRanges.has(rangeKey)) continue;

      // Run validator if exists
      if (pattern.validator && !pattern.validator(value)) {
        continue;
      }

      seenRanges.add(rangeKey);

      matches.push({
        type: pattern.name,
        category: pattern.category,
        value,
        masked: maskValue(value, pattern.category),
        start,
        end,
        region: pattern.region,
        confidence: pattern.confidence,
        description: pattern.description,
      });
    }
  }

  // Sort by position
  return matches.sort((a, b) => a.start - b.start);
}

/**
 * Get high-confidence PII matches only
 */
export function scanForHighConfidencePII(text: string, minConfidence = 70): PIIMatch[] {
  return scanForPII(text).filter((m) => m.confidence >= minConfidence);
}

/**
 * Scan for PII by category
 */
export function scanForPIIByCategory(text: string, category: PIICategory): PIIMatch[] {
  return scanForPII(text).filter((m) => m.category === category);
}

/**
 * Scan for PII by region
 */
export function scanForPIIByRegion(text: string, region: string): PIIMatch[] {
  return scanForPII(text).filter((m) => m.region === region || m.region === 'GLOBAL');
}

/**
 * Mask all PII in text
 */
export function maskAllPII(text: string, minConfidence = 70): string {
  if (!text || typeof text !== 'string') return text ?? '';

  const matches = scanForHighConfidencePII(text, minConfidence);
  if (matches.length === 0) return text;

  // Sort by position (descending) to replace from end
  const sorted = [...matches].sort((a, b) => b.start - a.start);

  let result = text;
  for (const match of sorted) {
    result = result.slice(0, match.start) + match.masked + result.slice(match.end);
  }

  return result;
}

/**
 * Get a summary of detected PII
 */
export interface PIISummary {
  total: number;
  byCategory: Record<PIICategory, number>;
  byRegion: Record<string, number>;
  highRisk: number;
  items: Array<{ type: string; masked: string; category: PIICategory }>;
}

export function getPIISummary(text: string): PIISummary {
  const matches = scanForPII(text);

  const byCategory: Record<string, number> = {};
  const byRegion: Record<string, number> = {};

  for (const match of matches) {
    byCategory[match.category] = (byCategory[match.category] || 0) + 1;
    byRegion[match.region] = (byRegion[match.region] || 0) + 1;
  }

  return {
    total: matches.length,
    byCategory: byCategory as Record<PIICategory, number>,
    byRegion,
    highRisk: matches.filter((m) => m.confidence >= 80).length,
    items: matches.map((m) => ({
      type: m.type,
      masked: m.masked,
      category: m.category,
    })),
  };
}
