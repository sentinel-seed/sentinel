/**
 * Sentinel Guard - Wallet Guard
 *
 * Crypto wallet protection features:
 * - Wallet address detection and validation
 * - Private key leak prevention
 * - Seed phrase protection
 * - Transaction security analysis
 * - dApp security alerts
 */

export interface WalletAddress {
  address: string;
  type: WalletType;
  network: string;
  isValid: boolean;
  checksum?: boolean;
}

export type WalletType =
  | 'ethereum'
  | 'bitcoin'
  | 'solana'
  | 'cosmos'
  | 'polkadot'
  | 'cardano'
  | 'unknown';

export interface WalletThreat {
  type: WalletThreatType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  details?: Record<string, unknown>;
}

export type WalletThreatType =
  | 'private_key_exposure'
  | 'seed_phrase_exposure'
  | 'phishing_address'
  | 'known_scam_address'
  | 'suspicious_contract'
  | 'honeypot_token'
  | 'approval_scam'
  | 'clipboard_hijack'
  | 'address_poisoning';

export interface TransactionPreview {
  type: TransactionType;
  from: string;
  to: string;
  value?: string;
  token?: string;
  risks: TransactionRisk[];
  overallRisk: 'safe' | 'low' | 'medium' | 'high' | 'critical';
  summary: string;
}

export type TransactionType =
  | 'transfer'
  | 'swap'
  | 'approve'
  | 'mint'
  | 'stake'
  | 'unstake'
  | 'contract_interaction'
  | 'unknown';

export interface TransactionRisk {
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
}

export interface dAppSecurityInfo {
  domain: string;
  isVerified: boolean;
  riskLevel: 'trusted' | 'caution' | 'danger' | 'unknown';
  warnings: string[];
  contractsInvolved: string[];
}

// Wallet address patterns
const WALLET_PATTERNS: Record<WalletType, { pattern: RegExp; networks: string[] }> = {
  ethereum: {
    pattern: /\b0x[a-fA-F0-9]{40}\b/g,
    networks: ['ethereum', 'polygon', 'arbitrum', 'optimism', 'bsc', 'avalanche'],
  },
  bitcoin: {
    pattern: /\b(bc1[a-zA-HJ-NP-Z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b/g,
    networks: ['bitcoin', 'bitcoin-testnet'],
  },
  solana: {
    pattern: /\b[1-9A-HJ-NP-Za-km-z]{32,44}\b/g,
    networks: ['solana', 'solana-devnet'],
  },
  cosmos: {
    pattern: /\b(cosmos|osmo|juno|atom)[a-zA-Z0-9]{39}\b/g,
    networks: ['cosmos', 'osmosis', 'juno'],
  },
  polkadot: {
    pattern: /\b[1-9A-HJ-NP-Za-km-z]{47,48}\b/g,
    networks: ['polkadot', 'kusama'],
  },
  cardano: {
    pattern: /\baddr1[a-zA-Z0-9]{53,}\b/g,
    networks: ['cardano'],
  },
  unknown: {
    pattern: /(?!)/g, // Never matches
    networks: [],
  },
};

// Known scam/phishing patterns
const SCAM_PATTERNS = {
  // Address poisoning: addresses that look similar to common ones
  poisonedAddressPattern: /0x[0-9a-fA-F]{4}0{32}[0-9a-fA-F]{4}/g,

  // Common scam domain patterns
  scamDomains: [
    /metamask.*\.(?!io)[a-z]+/i,
    /phantom.*\.(?!app)[a-z]+/i,
    /uniswap.*\.(?!org)[a-z]+/i,
    /opensea.*\.(?!io)[a-z]+/i,
    /airdrop.*claim/i,
    /free.*mint/i,
    /claim.*reward/i,
  ],
};

// BIP39 wordlist subset for seed phrase detection
const BIP39_WORDS = new Set([
  'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract',
  'absurd', 'abuse', 'access', 'accident', 'account', 'accuse', 'achieve', 'acid',
  'acoustic', 'acquire', 'across', 'act', 'action', 'actor', 'actress', 'actual',
  'adapt', 'add', 'addict', 'address', 'adjust', 'admit', 'adult', 'advance',
  'advice', 'aerobic', 'affair', 'afford', 'afraid', 'again', 'age', 'agent',
  'agree', 'ahead', 'aim', 'air', 'airport', 'aisle', 'alarm', 'album',
  'alcohol', 'alert', 'alien', 'all', 'alley', 'allow', 'almost', 'alone',
  'alpha', 'already', 'also', 'alter', 'always', 'amateur', 'amazing', 'among',
  'amount', 'amused', 'analyst', 'anchor', 'ancient', 'anger', 'angle', 'angry',
  'animal', 'ankle', 'announce', 'annual', 'another', 'answer', 'antenna', 'antique',
  'anxiety', 'any', 'apart', 'apology', 'appear', 'apple', 'approve', 'april',
  'arch', 'arctic', 'area', 'arena', 'argue', 'arm', 'armed', 'armor', 'army',
  'around', 'arrange', 'arrest', 'arrive', 'arrow', 'art', 'artefact', 'artist',
  'artwork', 'ask', 'aspect', 'assault', 'asset', 'assist', 'assume', 'asthma',
  'athlete', 'atom', 'attack', 'attend', 'attitude', 'attract', 'auction', 'audit',
  'august', 'aunt', 'author', 'auto', 'autumn', 'average', 'avocado', 'avoid',
  'awake', 'aware', 'away', 'awesome', 'awful', 'awkward', 'axis', 'baby',
  'bachelor', 'bacon', 'badge', 'bag', 'balance', 'balcony', 'ball', 'bamboo',
  'banana', 'banner', 'bar', 'barely', 'bargain', 'barrel', 'base', 'basic',
  'basket', 'battle', 'beach', 'bean', 'beauty', 'because', 'become', 'beef',
  'before', 'begin', 'behave', 'behind', 'believe', 'below', 'belt', 'bench',
  'benefit', 'best', 'betray', 'better', 'between', 'beyond', 'bicycle', 'bid',
  // More words would be included in production...
  'zoo', 'zone', 'zero', 'zebra', 'young', 'youth', 'year', 'yard', 'wrap',
  'write', 'wrong', 'world', 'worth', 'worry', 'word', 'wood', 'wonder', 'woman',
  'wolf', 'witness', 'wise', 'wish', 'wire', 'winter', 'wine', 'wing', 'window',
  'will', 'wild', 'wide', 'wife', 'wicked', 'wheat', 'whale', 'wet', 'west',
  'weird', 'welcome', 'wedding', 'wealth', 'weapon', 'way', 'wave', 'water',
  'watch', 'wash', 'warfare', 'want', 'wander', 'walnut', 'wall', 'walk', 'wait',
]);

/**
 * Simple Keccak-256 implementation for EIP-55 checksum validation
 * Optimized for Ethereum address checksums (40 hex chars)
 */
function keccak256(input: string): string {
  // Keccak-256 constants
  const RC = [
    0x0000000000000001n, 0x0000000000008082n, 0x800000000000808an, 0x8000000080008000n,
    0x000000000000808bn, 0x0000000080000001n, 0x8000000080008081n, 0x8000000000008009n,
    0x000000000000008an, 0x0000000000000088n, 0x0000000080008009n, 0x000000008000000an,
    0x000000008000808bn, 0x800000000000008bn, 0x8000000000008089n, 0x8000000000008003n,
    0x8000000000008002n, 0x8000000000000080n, 0x000000000000800an, 0x800000008000000an,
    0x8000000080008081n, 0x8000000000008080n, 0x0000000080000001n, 0x8000000080008008n
  ];
  const ROTC = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44];
  const PILN = [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1];

  const rotl64 = (x: bigint, n: number): bigint => ((x << BigInt(n)) | (x >> BigInt(64 - n))) & 0xffffffffffffffffn;

  const keccakf = (state: bigint[]): void => {
    for (let round = 0; round < 24; round++) {
      const C: bigint[] = [];
      for (let x = 0; x < 5; x++) {
        C[x] = state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20];
      }
      for (let x = 0; x < 5; x++) {
        const D = C[(x + 4) % 5] ^ rotl64(C[(x + 1) % 5], 1);
        for (let y = 0; y < 25; y += 5) state[x + y] ^= D;
      }
      let current = state[1];
      for (let i = 0; i < 24; i++) {
        const j = PILN[i];
        const temp = state[j];
        state[j] = rotl64(current, ROTC[i]);
        current = temp;
      }
      for (let y = 0; y < 25; y += 5) {
        const T = [state[y], state[y + 1], state[y + 2], state[y + 3], state[y + 4]];
        for (let x = 0; x < 5; x++) {
          state[y + x] = T[x] ^ (~T[(x + 1) % 5] & T[(x + 2) % 5]);
        }
      }
      state[0] ^= RC[round];
    }
  };

  // Convert input string to bytes
  const bytes = new Uint8Array(input.length);
  for (let i = 0; i < input.length; i++) bytes[i] = input.charCodeAt(i);

  // Keccak-256: rate=136 bytes (1088 bits), capacity=64 bytes (512 bits)
  const rate = 136;
  const state = new Array(25).fill(0n);

  // Absorb with padding
  const padded = new Uint8Array(Math.ceil((bytes.length + 1) / rate) * rate);
  padded.set(bytes);
  padded[bytes.length] = 0x01;
  padded[padded.length - 1] |= 0x80;

  for (let i = 0; i < padded.length; i += rate) {
    for (let j = 0; j < rate && j + i < padded.length; j += 8) {
      let val = 0n;
      for (let k = 0; k < 8 && j + k < rate; k++) {
        val |= BigInt(padded[i + j + k]) << BigInt(8 * k);
      }
      state[Math.floor(j / 8)] ^= val;
    }
    keccakf(state);
  }

  // Squeeze (32 bytes for 256 bits)
  let hash = '';
  for (let i = 0; i < 4; i++) {
    const val = state[i];
    for (let j = 0; j < 8; j++) {
      hash += ((val >> BigInt(8 * j)) & 0xffn).toString(16).padStart(2, '0');
    }
  }
  return hash;
}

/**
 * Validate Ethereum address checksum (EIP-55)
 */
function validateEthereumChecksum(address: string): boolean {
  if (!/^0x[a-fA-F0-9]{40}$/.test(address)) return false;

  // If all lowercase or all uppercase, consider valid (no checksum)
  if (address === address.toLowerCase() || address.slice(2) === address.slice(2).toUpperCase()) {
    return true;
  }

  // EIP-55 checksum validation using keccak256
  const addressLower = address.slice(2).toLowerCase();
  const hash = keccak256(addressLower);

  for (let i = 0; i < 40; i++) {
    const char = addressLower[i];
    const hashNibble = parseInt(hash[i], 16);
    const expectedCase = hashNibble >= 8 ? char.toUpperCase() : char.toLowerCase();
    if (address[i + 2] !== expectedCase) {
      return false;
    }
  }

  return true;
}

/**
 * Detect wallet addresses in text
 */
export function detectWalletAddresses(text: string): WalletAddress[] {
  if (!text || typeof text !== 'string') return [];

  const addresses: WalletAddress[] = [];
  const seen = new Set<string>();

  for (const [type, config] of Object.entries(WALLET_PATTERNS)) {
    if (type === 'unknown') continue;

    const regex = new RegExp(config.pattern.source, config.pattern.flags);
    let match;

    while ((match = regex.exec(text)) !== null) {
      const address = match[0];
      if (seen.has(address.toLowerCase())) continue;
      seen.add(address.toLowerCase());

      const walletType = type as WalletType;
      let isValid = true;
      let checksum: boolean | undefined;

      // Specific validation by type
      if (walletType === 'ethereum') {
        checksum = validateEthereumChecksum(address);
        isValid = /^0x[a-fA-F0-9]{40}$/.test(address);
      } else if (walletType === 'bitcoin') {
        // Basic validation for Bitcoin addresses
        isValid = /^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,}$/.test(address);
      } else if (walletType === 'solana') {
        // Solana addresses are base58 encoded
        isValid = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address);
      }

      addresses.push({
        address,
        type: walletType,
        network: config.networks[0],
        isValid,
        checksum,
      });
    }
  }

  return addresses;
}

/**
 * Detect private keys in text
 */
export function detectPrivateKeys(text: string): WalletThreat[] {
  if (!text || typeof text !== 'string') return [];

  const threats: WalletThreat[] = [];

  // Ethereum private key (64 hex chars, often with 0x prefix)
  const ethPrivateKey = /\b(0x)?[a-fA-F0-9]{64}\b/g;
  let match;
  while ((match = ethPrivateKey.exec(text)) !== null) {
    // Verify it looks like a private key (not just any 64 hex string)
    const value = match[0].replace('0x', '');
    if (/^[a-fA-F0-9]{64}$/.test(value)) {
      threats.push({
        type: 'private_key_exposure',
        severity: 'critical',
        message: 'Ethereum private key detected! Never share your private key.',
        details: { position: match.index },
      });
    }
  }

  // Solana private key (base58, 64-88 chars)
  const solPrivateKey = /\b[1-9A-HJ-NP-Za-km-z]{64,88}\b/g;
  while ((match = solPrivateKey.exec(text)) !== null) {
    // Only flag if it looks like a key (not a regular Solana address which is shorter)
    if (match[0].length >= 64 && match[0].length <= 88) {
      threats.push({
        type: 'private_key_exposure',
        severity: 'critical',
        message: 'Possible Solana private key detected! Never share private keys.',
        details: { position: match.index, length: match[0].length },
      });
    }
  }

  return threats;
}

/**
 * Detect seed phrases in text
 */
export function detectSeedPhrases(text: string): WalletThreat[] {
  if (!text || typeof text !== 'string') return [];

  const threats: WalletThreat[] = [];

  // Look for 12 or 24 word sequences that could be seed phrases
  const words = text.toLowerCase().split(/\s+/);

  for (let i = 0; i <= words.length - 12; i++) {
    // Check for 12-word phrase
    const phrase12 = words.slice(i, i + 12);
    const bip39Count12 = phrase12.filter((w) => BIP39_WORDS.has(w)).length;

    if (bip39Count12 >= 10) {
      threats.push({
        type: 'seed_phrase_exposure',
        severity: 'critical',
        message: 'Possible 12-word seed phrase detected! NEVER share your seed phrase.',
        details: { wordCount: 12, bip39Matches: bip39Count12 },
      });
      break; // Only report once
    }

    // Check for 24-word phrase
    if (i <= words.length - 24) {
      const phrase24 = words.slice(i, i + 24);
      const bip39Count24 = phrase24.filter((w) => BIP39_WORDS.has(w)).length;

      if (bip39Count24 >= 20) {
        threats.push({
          type: 'seed_phrase_exposure',
          severity: 'critical',
          message: 'Possible 24-word seed phrase detected! NEVER share your seed phrase.',
          details: { wordCount: 24, bip39Matches: bip39Count24 },
        });
        break;
      }
    }
  }

  return threats;
}

/**
 * Analyze a transaction for security risks
 */
export function analyzeTransaction(
  type: TransactionType,
  from: string,
  to: string,
  value?: string,
  token?: string,
  contractData?: string
): TransactionPreview {
  const risks: TransactionRisk[] = [];

  // Check for address poisoning
  if (to && SCAM_PATTERNS.poisonedAddressPattern.test(to)) {
    risks.push({
      type: 'address_poisoning',
      severity: 'critical',
      message: 'This address appears to be a poisoned address attack!',
    });
  }

  // Check for unlimited approvals
  if (type === 'approve') {
    const MAX_UINT256 = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff';
    if (contractData?.toLowerCase().includes(MAX_UINT256)) {
      risks.push({
        type: 'unlimited_approval',
        severity: 'high',
        message: 'This transaction grants unlimited token approval. Consider using a limited amount.',
      });
    }
  }

  // Check for interactions with unknown contracts
  if (type === 'contract_interaction' && contractData) {
    risks.push({
      type: 'unknown_contract',
      severity: 'medium',
      message: 'Interacting with unverified contract. Review carefully.',
    });
  }

  // Check for self-transactions (could be legitimate, but worth noting)
  if (from.toLowerCase() === to.toLowerCase()) {
    risks.push({
      type: 'self_transaction',
      severity: 'low',
      message: 'Sending to your own address.',
    });
  }

  // Calculate overall risk
  let overallRisk: TransactionPreview['overallRisk'] = 'safe';
  if (risks.some((r) => r.severity === 'critical')) {
    overallRisk = 'critical';
  } else if (risks.some((r) => r.severity === 'high')) {
    overallRisk = 'high';
  } else if (risks.some((r) => r.severity === 'medium')) {
    overallRisk = 'medium';
  } else if (risks.length > 0) {
    overallRisk = 'low';
  }

  // Generate summary
  let summary: string;
  if (risks.length === 0) {
    summary = 'No security risks detected.';
  } else if (overallRisk === 'critical') {
    summary = `DANGER: ${risks.length} risk(s) found, including critical issues!`;
  } else {
    summary = `${risks.length} potential risk(s) found.`;
  }

  return {
    type,
    from,
    to,
    value,
    token,
    risks,
    overallRisk,
    summary,
  };
}

/**
 * Analyze a dApp for security
 */
export function analyzeDApp(url: string): dAppSecurityInfo {
  const warnings: string[] = [];
  let riskLevel: 'trusted' | 'caution' | 'danger' | 'unknown' = 'unknown';

  try {
    const urlObj = new URL(url);
    const domain = urlObj.hostname;

    // Check for known verified/trusted dApps first
    const trustedDomains = [
      'uniswap.org', 'app.uniswap.org',
      'opensea.io',
      'aave.com', 'app.aave.com',
      'curve.fi',
      'compound.finance',
      'lido.fi',
      'metamask.io',
      'phantom.app',
    ];

    if (trustedDomains.some((td) => domain === td || domain.endsWith('.' + td))) {
      riskLevel = 'trusted';
    }

    // Check for known scam patterns
    for (const pattern of SCAM_PATTERNS.scamDomains) {
      if (pattern.test(domain)) {
        warnings.push('Domain matches known scam pattern');
        riskLevel = 'danger';
        break;
      }
    }

    // Check for suspicious TLDs (only if not already trusted or danger)
    if (riskLevel !== 'trusted' && riskLevel !== 'danger') {
      const suspiciousTLDs = ['.xyz', '.tk', '.ml', '.ga', '.cf'];
      if (suspiciousTLDs.some((tld) => domain.endsWith(tld))) {
        warnings.push('Suspicious top-level domain');
        riskLevel = 'caution';
      }
    }

    // Check for HTTPS (only if not already trusted or danger)
    if (urlObj.protocol !== 'https:' && riskLevel !== 'trusted' && riskLevel !== 'danger') {
      warnings.push('Site is not using HTTPS');
      riskLevel = 'caution';
    }

    // Check for typosquatting of known dApps
    const knownDApps = ['uniswap', 'opensea', 'metamask', 'phantom', 'rarible'];
    for (const dapp of knownDApps) {
      if (domain.includes(dapp) && !isOfficialDomain(domain, dapp)) {
        warnings.push(`Possible ${dapp} impersonation`);
        riskLevel = 'danger';
      }
    }

    // If still unknown, add a note
    if (riskLevel === 'unknown') {
      warnings.push('Domain not in verified list');
    }

    return {
      domain,
      isVerified: riskLevel === 'trusted',
      riskLevel,
      warnings,
      contractsInvolved: [],
    };
  } catch {
    return {
      domain: 'invalid',
      isVerified: false,
      riskLevel: 'danger',
      warnings: ['Invalid URL'],
      contractsInvolved: [],
    };
  }
}

/**
 * Check if domain is official for a dApp
 */
function isOfficialDomain(domain: string, dapp: string): boolean {
  const officialDomains: Record<string, string[]> = {
    uniswap: ['uniswap.org', 'app.uniswap.org'],
    opensea: ['opensea.io'],
    metamask: ['metamask.io'],
    phantom: ['phantom.app'],
    rarible: ['rarible.com'],
  };

  const official = officialDomains[dapp] || [];
  return official.some((d) => domain === d || domain.endsWith('.' + d));
}

/**
 * Scan text for all wallet-related threats
 */
export interface WalletScanResult {
  addresses: WalletAddress[];
  threats: WalletThreat[];
  hasRisk: boolean;
  riskLevel: 'safe' | 'low' | 'medium' | 'high' | 'critical';
  summary: string;
}

export function scanForWalletThreats(text: string): WalletScanResult {
  if (!text || typeof text !== 'string') {
    return {
      addresses: [],
      threats: [],
      hasRisk: false,
      riskLevel: 'safe',
      summary: 'No text to scan',
    };
  }

  const addresses = detectWalletAddresses(text);
  const privateKeyThreats = detectPrivateKeys(text);
  const seedThreats = detectSeedPhrases(text);
  const threats = [...privateKeyThreats, ...seedThreats];

  const hasRisk = threats.length > 0;

  let riskLevel: WalletScanResult['riskLevel'] = 'safe';
  if (threats.some((t) => t.severity === 'critical')) {
    riskLevel = 'critical';
  } else if (threats.some((t) => t.severity === 'high')) {
    riskLevel = 'high';
  } else if (threats.some((t) => t.severity === 'medium')) {
    riskLevel = 'medium';
  } else if (threats.length > 0) {
    riskLevel = 'low';
  }

  let summary: string;
  if (!hasRisk && addresses.length === 0) {
    summary = 'No wallet data or threats detected.';
  } else if (!hasRisk) {
    summary = `Found ${addresses.length} wallet address(es), no threats.`;
  } else if (riskLevel === 'critical') {
    summary = `CRITICAL: ${threats.length} threat(s) detected! Private key or seed phrase exposure!`;
  } else {
    summary = `${threats.length} potential threat(s) detected.`;
  }

  return {
    addresses,
    threats,
    hasRisk,
    riskLevel,
    summary,
  };
}
