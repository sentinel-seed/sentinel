/**
 * CSA AI Controls Matrix Compliance Module
 *
 * Exports for CSA AICM compliance checking.
 */

export {
    CSAAICMChecker,
    checkCSAAICMCompliance,
    getThspSupportedDomains,
} from './checker';

export {
    ALL_CSA_AICM_PATTERNS,
    MODEL_SECURITY_PATTERNS,
    DATA_SECURITY_PATTERNS,
    GOVERNANCE_PATTERNS,
    APPLICATION_SECURITY_PATTERNS,
    SUPPLY_CHAIN_PATTERNS,
    THREAT_PATTERNS,
    DOMAIN_GATE_MAPPING,
    THREAT_GATE_MAPPING,
    DOMAIN_RECOMMENDATIONS,
    getSupportedDomains,
    getDomainDisplayName,
    getPatternsForDomain,
} from './patterns';
