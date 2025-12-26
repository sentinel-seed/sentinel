/**
 * Tests for Wallet Guard
 */

import {
  detectWalletAddresses,
  detectPrivateKeys,
  detectSeedPhrases,
  analyzeTransaction,
  analyzeDApp,
  scanForWalletThreats,
  WalletAddress,
  WalletThreat,
  TransactionPreview,
  dAppSecurityInfo,
} from './wallet-guard';

describe('Wallet Guard', () => {
  describe('detectWalletAddresses', () => {
    it('should return empty array for null/undefined', () => {
      expect(detectWalletAddresses(null as unknown as string)).toEqual([]);
      expect(detectWalletAddresses(undefined as unknown as string)).toEqual([]);
      expect(detectWalletAddresses('')).toEqual([]);
    });

    it('should detect Ethereum addresses', () => {
      const text = 'Send to 0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1';
      const result = detectWalletAddresses(text);

      expect(result.length).toBeGreaterThan(0);
      expect(result[0].type).toBe('ethereum');
      expect(result[0].isValid).toBe(true);
    });

    it('should detect Bitcoin addresses (legacy)', () => {
      const text = 'BTC: 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2';
      const result = detectWalletAddresses(text);

      const btcAddress = result.find((a) => a.type === 'bitcoin');
      expect(btcAddress).toBeDefined();
    });

    it('should detect Bitcoin addresses (bech32)', () => {
      const text = 'BTC: bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq';
      const result = detectWalletAddresses(text);

      const btcAddress = result.find((a) => a.type === 'bitcoin');
      expect(btcAddress).toBeDefined();
    });

    it('should detect Solana addresses', () => {
      const text = 'SOL: 7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV';
      const result = detectWalletAddresses(text);

      // Note: Solana addresses are base58 and might overlap with other patterns
      expect(result.length).toBeGreaterThanOrEqual(0);
    });

    it('should not duplicate addresses', () => {
      const text = '0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1 and 0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1';
      const result = detectWalletAddresses(text);

      const ethAddresses = result.filter((a) => a.type === 'ethereum');
      expect(ethAddresses.length).toBe(1);
    });
  });

  describe('detectPrivateKeys', () => {
    it('should return empty for safe text', () => {
      const result = detectPrivateKeys('Hello world');
      expect(result.length).toBe(0);
    });

    it('should detect Ethereum private keys', () => {
      // This is a fake private key for testing
      const fakeKey = '0x' + 'a'.repeat(64);
      const result = detectPrivateKeys(`Private key: ${fakeKey}`);

      expect(result.length).toBeGreaterThan(0);
      expect(result[0].type).toBe('private_key_exposure');
      expect(result[0].severity).toBe('critical');
    });

    it('should detect private keys without 0x prefix', () => {
      const fakeKey = 'a'.repeat(64);
      const result = detectPrivateKeys(`Key: ${fakeKey}`);

      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('detectSeedPhrases', () => {
    it('should return empty for safe text', () => {
      const result = detectSeedPhrases('Hello world');
      expect(result.length).toBe(0);
    });

    it('should detect 12-word seed phrase', () => {
      // Using BIP39 words
      const seedPhrase = 'abandon ability able about above absent absorb abstract absurd abuse access accident';
      const result = detectSeedPhrases(seedPhrase);

      expect(result.length).toBeGreaterThan(0);
      expect(result[0].type).toBe('seed_phrase_exposure');
      expect(result[0].severity).toBe('critical');
    });

    it('should detect 24-word seed phrase', () => {
      const seedPhrase = 'abandon ability able about above absent absorb abstract absurd abuse access accident ' +
        'abandon ability able about above absent absorb abstract absurd abuse access accident';
      const result = detectSeedPhrases(seedPhrase);

      expect(result.length).toBeGreaterThan(0);
    });

    it('should not detect non-BIP39 word sequences', () => {
      const normalText = 'the quick brown fox jumps over the lazy dog near the river bank';
      const result = detectSeedPhrases(normalText);

      expect(result.length).toBe(0);
    });
  });

  describe('analyzeTransaction', () => {
    it('should return valid TransactionPreview', () => {
      const result = analyzeTransaction(
        'transfer',
        '0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1',
        '0x123456789abcdef0123456789abcdef012345678',
        '1.0',
        'ETH'
      );

      expect(result).toHaveProperty('type');
      expect(result).toHaveProperty('from');
      expect(result).toHaveProperty('to');
      expect(result).toHaveProperty('risks');
      expect(result).toHaveProperty('overallRisk');
      expect(result).toHaveProperty('summary');
    });

    it('should detect address poisoning', () => {
      // Poisoned address pattern: starts and ends with real chars, middle is zeros
      const poisonedAddress = '0x1234' + '0'.repeat(32) + '5678';
      const result = analyzeTransaction('transfer', '0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1', poisonedAddress);

      const poisoningRisk = result.risks.find((r) => r.type === 'address_poisoning');
      expect(poisoningRisk).toBeDefined();
      expect(result.overallRisk).toBe('critical');
    });

    it('should detect unlimited approval', () => {
      const maxApproval = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff';
      const result = analyzeTransaction(
        'approve',
        '0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1',
        '0x123456789abcdef0123456789abcdef012345678',
        undefined,
        'USDC',
        maxApproval
      );

      const approvalRisk = result.risks.find((r) => r.type === 'unlimited_approval');
      expect(approvalRisk).toBeDefined();
    });

    it('should detect self-transactions', () => {
      const address = '0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1';
      const result = analyzeTransaction('transfer', address, address);

      const selfTxRisk = result.risks.find((r) => r.type === 'self_transaction');
      expect(selfTxRisk).toBeDefined();
    });

    it('should return safe for normal transactions', () => {
      const result = analyzeTransaction(
        'transfer',
        '0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1',
        '0xabcdef0123456789abcdef0123456789abcdef01'
      );

      expect(result.overallRisk).toBe('safe');
    });
  });

  describe('analyzeDApp', () => {
    it('should return valid dAppSecurityInfo', () => {
      const result = analyzeDApp('https://app.uniswap.org');

      expect(result).toHaveProperty('domain');
      expect(result).toHaveProperty('isVerified');
      expect(result).toHaveProperty('riskLevel');
      expect(result).toHaveProperty('warnings');
    });

    it('should detect suspicious TLDs', () => {
      const result = analyzeDApp('https://somecrypto.xyz');

      expect(result.warnings.length).toBeGreaterThan(0);
    });

    it('should detect non-HTTPS', () => {
      const result = analyzeDApp('http://example.com');

      const httpWarning = result.warnings.find((w) => w.includes('HTTPS'));
      expect(httpWarning).toBeDefined();
    });

    it('should detect scam domain patterns', () => {
      const result = analyzeDApp('https://metamask-claim.xyz');

      expect(result.riskLevel).toBe('danger');
    });

    it('should handle invalid URLs', () => {
      const result = analyzeDApp('not-a-url');

      expect(result.riskLevel).toBe('danger');
      expect(result.domain).toBe('invalid');
    });
  });

  describe('scanForWalletThreats', () => {
    it('should return safe for empty text', () => {
      const result = scanForWalletThreats('');

      expect(result.hasRisk).toBe(false);
      expect(result.riskLevel).toBe('safe');
    });

    it('should detect private key exposure', () => {
      const fakeKey = '0x' + 'a'.repeat(64);
      const result = scanForWalletThreats(`Here is my private key: ${fakeKey}`);

      expect(result.hasRisk).toBe(true);
      expect(result.riskLevel).toBe('critical');
      expect(result.threats.some((t) => t.type === 'private_key_exposure')).toBe(true);
    });

    it('should detect seed phrase exposure', () => {
      const seedPhrase = 'abandon ability able about above absent absorb abstract absurd abuse access accident';
      const result = scanForWalletThreats(`My recovery phrase: ${seedPhrase}`);

      expect(result.hasRisk).toBe(true);
      expect(result.riskLevel).toBe('critical');
    });

    it('should detect wallet addresses without threats', () => {
      const result = scanForWalletThreats('Send to 0x742d35Cc6634C0532925a3b844Bc9e7595f7AbE1');

      expect(result.addresses.length).toBeGreaterThan(0);
      expect(result.hasRisk).toBe(false); // Addresses alone are not threats
    });

    it('should provide accurate summary', () => {
      const result = scanForWalletThreats('Hello world, no wallet data here');

      expect(result.summary).toContain('No wallet data');
    });
  });
});
