/**
 * EU AI Act Compliance Module
 *
 * Exports for EU AI Act compliance checking.
 */

export { EUAIActChecker, checkEUAIActCompliance } from './checker';

export {
    ALL_EU_AI_ACT_PATTERNS,
    PROHIBITED_PRACTICE_PATTERNS,
    HIGH_RISK_CONTEXT_PATTERNS,
    TRANSPARENCY_PATTERNS,
    HUMAN_OVERSIGHT_PATTERNS,
    PATTERN_TO_PROHIBITED_PRACTICE,
    PATTERN_TO_HIGH_RISK_CONTEXT,
    getPatternsForArticle,
    getPatternsBySeverity,
    getPatternsByGate,
} from './patterns';
