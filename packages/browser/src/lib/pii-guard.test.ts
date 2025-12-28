/**
 * Tests for PII Guard
 */

import {
  scanForPII,
  scanForHighConfidencePII,
  scanForPIIByCategory,
  scanForPIIByRegion,
  maskAllPII,
  getPIISummary,
} from './pii-guard';

describe('PII Guard', () => {
  describe('scanForPII', () => {
    it('should return empty array for null/undefined input', () => {
      expect(scanForPII(null as unknown as string)).toEqual([]);
      expect(scanForPII(undefined as unknown as string)).toEqual([]);
      expect(scanForPII('')).toEqual([]);
    });

    // US SSN Tests
    describe('US SSN Detection', () => {
      it('should detect valid SSN format', () => {
        const result = scanForPII('My SSN is 123-45-6789');
        expect(result.some((m) => m.type === 'ssn')).toBe(true);
      });

      it('should reject invalid SSN (area 000)', () => {
        const result = scanForPII('SSN: 000-45-6789');
        expect(result.some((m) => m.type === 'ssn')).toBe(false);
      });

      it('should reject invalid SSN (area 666)', () => {
        const result = scanForPII('SSN: 666-45-6789');
        expect(result.some((m) => m.type === 'ssn')).toBe(false);
      });
    });

    // Brazilian CPF Tests
    describe('Brazilian CPF Detection', () => {
      it('should detect valid CPF format', () => {
        const result = scanForPII('CPF: 123.456.789-09');
        expect(result.some((m) => m.type === 'cpf')).toBe(true);
      });

      it('should validate CPF check digits', () => {
        // Valid CPF: 529.982.247-25
        const validResult = scanForPII('CPF: 529.982.247-25');
        const validMatch = validResult.find((m) => m.type === 'cpf');
        expect(validMatch?.confidence).toBe(95);
      });
    });

    // Credit Card Tests
    describe('Credit Card Detection', () => {
      it('should detect Visa cards', () => {
        const result = scanForPII('Card: 4111-1111-1111-1111');
        expect(result.some((m) => m.type === 'credit_card_visa')).toBe(true);
      });

      it('should detect Mastercard', () => {
        const result = scanForPII('Card: 5500-0000-0000-0004');
        expect(result.some((m) => m.type === 'credit_card_mastercard')).toBe(true);
      });

      it('should detect Amex', () => {
        const result = scanForPII('Card: 3782-822463-10005');
        expect(result.some((m) => m.type === 'credit_card_amex')).toBe(true);
      });

      it('should validate credit card with Luhn algorithm', () => {
        // Valid Visa test card
        const result = scanForPII('4111111111111111');
        const match = result.find((m) => m.type === 'credit_card_visa');
        expect(match).toBeDefined();
      });
    });

    // Email Tests
    describe('Email Detection', () => {
      it('should detect real email addresses', () => {
        const result = scanForPII('Contact: user@gmail.com');
        expect(result.some((m) => m.type === 'email')).toBe(true);
      });

      it('should skip @example.com addresses (test domains)', () => {
        const result = scanForPII('Email: test@example.com');
        // Should be filtered out as false positive
        const match = result.find((m) => m.type === 'email' && m.value === 'test@example.com');
        expect(match).toBeUndefined();
      });

      it('should detect corporate email addresses', () => {
        const result = scanForPII('Email: john.doe@company.org');
        expect(result.some((m) => m.type === 'email')).toBe(true);
      });
    });

    // Phone Tests
    describe('Phone Detection', () => {
      it('should detect US phone numbers', () => {
        const result = scanForPII('Call me at (555) 123-4567');
        expect(result.some((m) => m.type === 'phone_us')).toBe(true);
      });

      it('should detect Brazilian phone numbers', () => {
        const result = scanForPII('Telefone: (11) 98765-4321');
        expect(result.some((m) => m.type === 'phone_br')).toBe(true);
      });
    });

    // Password Detection
    describe('Password Detection', () => {
      it('should detect password in context', () => {
        const result = scanForPII('password: mysecretpass123');
        expect(result.some((m) => m.type === 'password_context')).toBe(true);
      });

      it('should detect senha (Portuguese)', () => {
        const result = scanForPII('senha: minhasenha123');
        expect(result.some((m) => m.type === 'password_context')).toBe(true);
      });
    });

    // IBAN Tests
    describe('IBAN Detection', () => {
      it('should detect IBAN', () => {
        const result = scanForPII('IBAN: DE89370400440532013000');
        expect(result.some((m) => m.type === 'iban')).toBe(true);
      });
    });

    // GPS Coordinates
    describe('GPS Detection', () => {
      it('should detect GPS coordinates', () => {
        const result = scanForPII('Location: 40.7128, -74.0060');
        expect(result.some((m) => m.type === 'gps_coordinates')).toBe(true);
      });
    });
  });

  describe('scanForHighConfidencePII', () => {
    it('should only return high confidence matches', () => {
      const text = 'SSN: 123-45-6789, some random text';
      const result = scanForHighConfidencePII(text, 80);

      for (const match of result) {
        expect(match.confidence).toBeGreaterThanOrEqual(80);
      }
    });

    it('should filter out low confidence matches', () => {
      const text = 'Some 12345 numbers';
      const allMatches = scanForPII(text);
      const highConfidence = scanForHighConfidencePII(text, 80);

      expect(highConfidence.length).toBeLessThanOrEqual(allMatches.length);
    });
  });

  describe('scanForPIIByCategory', () => {
    it('should filter by financial category', () => {
      const text = 'Card: 4111-1111-1111-1111, SSN: 123-45-6789';
      const result = scanForPIIByCategory(text, 'financial');

      for (const match of result) {
        expect(match.category).toBe('financial');
      }
    });

    it('should filter by identity category', () => {
      const text = 'SSN: 123-45-6789, CPF: 123.456.789-09';
      const result = scanForPIIByCategory(text, 'identity');

      for (const match of result) {
        expect(match.category).toBe('identity');
      }
    });
  });

  describe('scanForPIIByRegion', () => {
    it('should filter by US region', () => {
      const text = 'SSN: 123-45-6789, CPF: 123.456.789-09';
      const result = scanForPIIByRegion(text, 'US');

      for (const match of result) {
        expect(['US', 'GLOBAL']).toContain(match.region);
      }
    });

    it('should filter by BR region', () => {
      const text = 'CPF: 123.456.789-09, Tel: (11) 98765-4321';
      const result = scanForPIIByRegion(text, 'BR');

      for (const match of result) {
        expect(['BR', 'GLOBAL']).toContain(match.region);
      }
    });
  });

  describe('maskAllPII', () => {
    it('should return original text for empty input', () => {
      expect(maskAllPII('')).toBe('');
      expect(maskAllPII(null as unknown as string)).toBe('');
    });

    it('should mask SSN', () => {
      const result = maskAllPII('SSN: 123-45-6789', 90);
      expect(result).not.toContain('123-45-6789');
    });

    it('should mask credit cards', () => {
      const result = maskAllPII('Card: 4111-1111-1111-1111', 90);
      expect(result).not.toContain('4111-1111-1111-1111');
    });

    it('should preserve non-PII text', () => {
      const result = maskAllPII('Hello world', 80);
      expect(result).toBe('Hello world');
    });
  });

  describe('getPIISummary', () => {
    it('should return valid summary structure', () => {
      const text = 'SSN: 123-45-6789, Email: user@email.com';
      const summary = getPIISummary(text);

      expect(summary).toHaveProperty('total');
      expect(summary).toHaveProperty('byCategory');
      expect(summary).toHaveProperty('byRegion');
      expect(summary).toHaveProperty('highRisk');
      expect(summary).toHaveProperty('items');
      expect(typeof summary.total).toBe('number');
    });

    it('should count items correctly', () => {
      const text = 'SSN: 123-45-6789';
      const summary = getPIISummary(text);

      expect(summary.total).toBeGreaterThan(0);
    });

    it('should categorize correctly', () => {
      const text = 'Card: 4111-1111-1111-1111';
      const summary = getPIISummary(text);

      expect(summary.byCategory.financial).toBeGreaterThan(0);
    });
  });
});
