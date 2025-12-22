/**
 * EU AI Act Compliance Patterns
 *
 * Pattern definitions for detecting potential EU AI Act violations.
 * Based on the EU AI Act (Regulation 2024/1689) final text.
 *
 * Key articles covered:
 * - Article 5: Prohibited AI practices
 * - Article 6: Classification of high-risk AI systems
 * - Article 9: Risk management system
 * - Article 13: Transparency and provision of information
 * - Article 14: Human oversight
 * - Article 15: Accuracy, robustness, and cybersecurity
 *
 * Reference: https://artificialintelligenceact.eu/
 */

import { CompliancePattern, ProhibitedPractice, HighRiskContext, THSPGate } from '../types';

// ============================================================================
// ARTICLE 5: PROHIBITED PRACTICES PATTERNS
// ============================================================================

/**
 * Patterns for detecting Article 5 prohibited practices.
 * These practices are completely banned under the EU AI Act.
 */
export const PROHIBITED_PRACTICE_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // Article 5(1)(c): Social Scoring
    // -------------------------------------------------------------------------
    {
        id: 'euai_art5_1c_social_score',
        pattern: /\b(social\s*scor(e|ing)|citizen\s*scor(e|ing)|credit\s*scor(e|ing)\s*system|trustworthiness\s*scor(e|ing)|behavior\s*scor(e|ing)|reputation\s*scor(e|ing)\s*system)\b/gi,
        description: 'Social scoring system that evaluates or classifies natural persons',
        severity: 'critical',
        gates: ['harm', 'purpose'],
        category: 'Article 5(1)(c)',
    },
    {
        id: 'euai_art5_1c_social_eval',
        pattern: /\b(evaluat(e|ing)\s+(citizen|person|individual|user)s?\s+(trustworthiness|reliability|character)|rank(ing)?\s+(citizen|person|individual)s?\s+based\s+on\s+behavior)\b/gi,
        description: 'Evaluation of persons based on social behavior',
        severity: 'critical',
        gates: ['harm', 'purpose'],
        category: 'Article 5(1)(c)',
    },

    // -------------------------------------------------------------------------
    // Article 5(1)(g): Biometric Categorization (Sensitive Categories)
    // -------------------------------------------------------------------------
    {
        id: 'euai_art5_1g_biometric_race',
        pattern: /\b(biometric\s*(categoriz|classif)(ation|y|ing)|facial\s*(analysis|recognition))\s*.{0,50}(race|ethnic|racial|ethnicity)\b/gi,
        description: 'Biometric categorization by race or ethnicity',
        severity: 'critical',
        gates: ['harm', 'truth'],
        category: 'Article 5(1)(g)',
    },
    {
        id: 'euai_art5_1g_biometric_politics',
        pattern: /\b(biometric|facial)\s*.{0,30}(political\s*(opinion|affiliation|view)|religious\s*belief|sexual\s*orientation)\b/gi,
        description: 'Biometric categorization by political/religious/sexual orientation',
        severity: 'critical',
        gates: ['harm', 'truth'],
        category: 'Article 5(1)(g)',
    },

    // -------------------------------------------------------------------------
    // Article 5(1)(f): Emotion Recognition in Certain Contexts
    // -------------------------------------------------------------------------
    {
        id: 'euai_art5_1f_emotion_workplace',
        pattern: /\b(emotion\s*(recognition|detection|analysis)|facial\s*expression\s*(analysis|recognition)|sentiment\s*analysis)\s*.{0,50}(workplace|employee|worker|staff|office)\b/gi,
        description: 'Emotion recognition in workplace context',
        severity: 'critical',
        gates: ['harm', 'scope'],
        category: 'Article 5(1)(f)',
    },
    {
        id: 'euai_art5_1f_emotion_education',
        pattern: /\b(emotion\s*(recognition|detection|analysis)|facial\s*expression\s*(analysis|recognition))\s*.{0,50}(school|education|student|classroom|learning)\b/gi,
        description: 'Emotion recognition in educational context',
        severity: 'critical',
        gates: ['harm', 'scope'],
        category: 'Article 5(1)(f)',
    },

    // -------------------------------------------------------------------------
    // Article 5(1)(d): Predictive Policing (Individual Risk)
    // -------------------------------------------------------------------------
    {
        id: 'euai_art5_1d_predictive_crime',
        pattern: /\b(predict(ing|ive)?\s*(crime|criminal|offense|offender)|crime\s*predict(ion|ing|ive)|risk\s*of\s*(offending|reoffending|criminal))\b/gi,
        description: 'Predictive policing or crime risk assessment',
        severity: 'critical',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Article 5(1)(d)',
    },
    {
        id: 'euai_art5_1d_recidivism',
        pattern: /\b(recidivism\s*(prediction|risk|assessment|score)|likelihood\s+(of|to)\s+(reoffend|commit\s+crime))\b/gi,
        description: 'Recidivism prediction system',
        severity: 'critical',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Article 5(1)(d)',
    },

    // -------------------------------------------------------------------------
    // Article 5(1)(a): Subliminal Manipulation
    // -------------------------------------------------------------------------
    {
        id: 'euai_art5_1a_subliminal',
        pattern: /\b(subliminal\s*(technique|manipulation|message|influence)|below\s*conscious\s*awareness|manipulat(e|ing)\s*.{0,30}without\s*(their\s*)?(awareness|knowledge))\b/gi,
        description: 'Subliminal manipulation technique',
        severity: 'critical',
        gates: ['truth', 'harm', 'scope'],
        category: 'Article 5(1)(a)',
    },
    {
        id: 'euai_art5_1a_dark_patterns',
        pattern: /\b(dark\s*pattern|deceptive\s*design|manipulative\s*interface|coercive\s*ux)\b/gi,
        description: 'Potentially manipulative design patterns',
        severity: 'high',
        gates: ['truth', 'harm'],
        category: 'Article 5(1)(a)',
    },

    // -------------------------------------------------------------------------
    // Article 5(1)(b): Vulnerability Exploitation
    // -------------------------------------------------------------------------
    {
        id: 'euai_art5_1b_vulnerable_age',
        pattern: /\b(exploit(ing|ation)?\s*.{0,30}(child|children|elderly|aged|minor|senior)|target(ing)?\s*(vulnerable|elderly|children|minor))\b/gi,
        description: 'Exploitation of vulnerable groups (age)',
        severity: 'critical',
        gates: ['harm', 'purpose'],
        category: 'Article 5(1)(b)',
    },
    {
        id: 'euai_art5_1b_vulnerable_disability',
        pattern: /\b(exploit(ing|ation)?\s*.{0,30}(disab(led|ility)|mental\s*(health|illness)|cognitive\s*(impairment|disability)))\b/gi,
        description: 'Exploitation of vulnerable groups (disability)',
        severity: 'critical',
        gates: ['harm', 'purpose'],
        category: 'Article 5(1)(b)',
    },

    // -------------------------------------------------------------------------
    // Article 5(1)(e): Real-time Remote Biometric Identification (Public Spaces)
    // -------------------------------------------------------------------------
    {
        id: 'euai_art5_1e_realtime_biometric',
        pattern: /\b(real[\s-]*time\s*(biometric|facial)\s*(identification|recognition)|live\s*(facial|biometric)\s*(scanning|recognition)|public\s*(space|area)\s*(facial|biometric))\b/gi,
        description: 'Real-time biometric identification in public spaces',
        severity: 'critical',
        gates: ['harm', 'scope'],
        category: 'Article 5(1)(e)',
    },
    {
        id: 'euai_art5_1e_mass_surveillance',
        pattern: /\b(mass\s*surveillance|population[\s-]*wide\s*(monitoring|surveillance|tracking)|untargeted\s*(facial|biometric)\s*(scanning|recognition))\b/gi,
        description: 'Mass biometric surveillance',
        severity: 'critical',
        gates: ['harm', 'scope', 'purpose'],
        category: 'Article 5(1)(e)',
    },
];

// ============================================================================
// HIGH-RISK CONTEXT PATTERNS (Annex III)
// ============================================================================

/**
 * Patterns for detecting high-risk AI system contexts.
 * Systems in these areas require conformity assessment per Article 6.
 */
export const HIGH_RISK_CONTEXT_PATTERNS: CompliancePattern[] = [
    // -------------------------------------------------------------------------
    // Biometrics (Annex III, 1)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_biometrics',
        pattern: /\b(biometric\s*(verification|identification|authentication)|face\s*(recognition|detection|matching)|fingerprint\s*(recognition|matching)|iris\s*(recognition|scanning)|voice\s*(biometric|recognition|authentication))\b/gi,
        description: 'Biometric identification or verification system',
        severity: 'high',
        gates: ['harm', 'truth'],
        category: 'Annex III - Biometrics',
    },

    // -------------------------------------------------------------------------
    // Critical Infrastructure (Annex III, 2)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_infrastructure',
        pattern: /\b(critical\s*infrastructure|power\s*grid|water\s*supply|gas\s*distribution|transport\s*network|traffic\s*management|emergency\s*services)\b/gi,
        description: 'Critical infrastructure management system',
        severity: 'high',
        gates: ['harm', 'scope'],
        category: 'Annex III - Critical Infrastructure',
    },

    // -------------------------------------------------------------------------
    // Education and Vocational Training (Annex III, 3)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_education_access',
        pattern: /\b((admission|enrollment)\s*(decision|system|algorithm)|student\s*(selection|admission)|educational\s*(access|admission|placement)|grade\s*(prediction|algorithm)|learning\s*(assessment|evaluation)\s*system)\b/gi,
        description: 'Educational access or assessment system',
        severity: 'high',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Annex III - Education',
    },

    // -------------------------------------------------------------------------
    // Employment (Annex III, 4)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_employment_recruit',
        pattern: /\b((automated|ai|algorithmic)\s*(recruitment|hiring|screening)|candidate\s*(screening|ranking|filtering)|resume\s*(screening|parsing|ranking)|job\s*(matching|recommendation)\s*(algorithm|system))\b/gi,
        description: 'Automated recruitment or hiring system',
        severity: 'high',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Annex III - Employment',
    },
    {
        id: 'euai_annex3_employment_manage',
        pattern: /\b(employee\s*(monitoring|surveillance|tracking)|worker\s*(productivity|performance)\s*(monitoring|tracking)|workplace\s*(monitoring|surveillance))\b/gi,
        description: 'Employee monitoring or performance tracking',
        severity: 'high',
        gates: ['harm', 'scope'],
        category: 'Annex III - Employment',
    },

    // -------------------------------------------------------------------------
    // Essential Services (Annex III, 5)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_credit',
        pattern: /\b((credit|loan)\s*(scoring|decision|assessment|worthiness)|creditworthiness\s*(assessment|evaluation)|lending\s*(decision|algorithm)|financial\s*(risk|credit)\s*assessment)\b/gi,
        description: 'Credit scoring or lending decision system',
        severity: 'high',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Annex III - Essential Services',
    },
    {
        id: 'euai_annex3_insurance',
        pattern: /\b(insurance\s*(pricing|risk|underwriting)|health\s*insurance\s*(decision|assessment)|life\s*insurance\s*(risk|pricing))\b/gi,
        description: 'Insurance pricing or risk assessment',
        severity: 'high',
        gates: ['harm', 'truth'],
        category: 'Annex III - Essential Services',
    },
    {
        id: 'euai_annex3_benefits',
        pattern: /\b((social|public)\s*benefit(s)?\s*(decision|eligibility|assessment)|welfare\s*(decision|eligibility)|unemployment\s*(benefit|insurance)\s*(decision|eligibility))\b/gi,
        description: 'Public benefit eligibility assessment',
        severity: 'high',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Annex III - Essential Services',
    },

    // -------------------------------------------------------------------------
    // Law Enforcement (Annex III, 6)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_law_enforcement',
        pattern: /\b(law\s*enforcement\s*(ai|system|tool)|police\s*(ai|algorithm|system)|criminal\s*(investigation|profiling)|evidence\s*(analysis|assessment)\s*(ai|system))\b/gi,
        description: 'Law enforcement AI system',
        severity: 'high',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Annex III - Law Enforcement',
    },

    // -------------------------------------------------------------------------
    // Migration and Border Control (Annex III, 7)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_migration',
        pattern: /\b((asylum|visa|immigration)\s*(decision|assessment|processing)|border\s*(control|management)\s*(ai|system)|migration\s*(risk|assessment))\b/gi,
        description: 'Migration or asylum decision system',
        severity: 'high',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Annex III - Migration',
    },

    // -------------------------------------------------------------------------
    // Justice and Democracy (Annex III, 8)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_justice',
        pattern: /\b((judicial|court|legal)\s*(decision|support|assistance)\s*(system|ai)|sentencing\s*(recommendation|algorithm)|legal\s*(outcome|prediction)|justice\s*system\s*ai)\b/gi,
        description: 'Judicial decision support system',
        severity: 'high',
        gates: ['harm', 'truth', 'purpose'],
        category: 'Annex III - Justice',
    },
    {
        id: 'euai_annex3_democracy',
        pattern: /\b((election|voting)\s*(system|ai|algorithm)|electoral\s*(process|decision)|democratic\s*process|vote\s*(counting|tabulation)\s*(system|algorithm))\b/gi,
        description: 'Electoral or democratic process system',
        severity: 'high',
        gates: ['harm', 'truth', 'scope'],
        category: 'Annex III - Democracy',
    },

    // -------------------------------------------------------------------------
    // Safety Components (Annex III)
    // -------------------------------------------------------------------------
    {
        id: 'euai_annex3_safety',
        pattern: /\b(safety[\s-]*(critical|component)|medical\s*device\s*(ai|system)|autonomous\s*vehicle|self[\s-]*driving|surgical\s*robot|aviation\s*(ai|system))\b/gi,
        description: 'Safety-critical AI component',
        severity: 'high',
        gates: ['harm', 'scope'],
        category: 'Annex III - Safety Components',
    },
];

// ============================================================================
// TRANSPARENCY REQUIREMENT PATTERNS (Article 52)
// ============================================================================

/**
 * Patterns for detecting transparency obligations.
 */
export const TRANSPARENCY_PATTERNS: CompliancePattern[] = [
    {
        id: 'euai_art52_chatbot',
        pattern: /\b(chatbot|conversational\s*ai|virtual\s*assistant|ai\s*assistant)\b/gi,
        description: 'AI system interacting with humans (transparency required)',
        severity: 'medium',
        gates: ['truth'],
        category: 'Article 52 - Transparency',
    },
    {
        id: 'euai_art52_deepfake',
        pattern: /\b(deepfake|synthetic\s*media|ai[\s-]*generated\s*(image|video|audio)|face\s*swap)\b/gi,
        description: 'Synthetic media generation (disclosure required)',
        severity: 'medium',
        gates: ['truth'],
        category: 'Article 52 - Transparency',
    },
    {
        id: 'euai_art52_generated',
        pattern: /\b(ai[\s-]*generated\s*(content|text|article)|generated\s*by\s*(ai|artificial\s*intelligence)|machine[\s-]*generated)\b/gi,
        description: 'AI-generated content (disclosure may be required)',
        severity: 'low',
        gates: ['truth'],
        category: 'Article 52 - Transparency',
    },
];

// ============================================================================
// HUMAN OVERSIGHT PATTERNS (Article 14)
// ============================================================================

/**
 * Patterns indicating human oversight requirements.
 */
export const HUMAN_OVERSIGHT_PATTERNS: CompliancePattern[] = [
    {
        id: 'euai_art14_automated_decision',
        pattern: /\b(fully\s*automated\s*decision|no\s*human\s*(review|oversight|intervention)|autonomous\s*decision[\s-]*making)\b/gi,
        description: 'Automated decision without human oversight',
        severity: 'high',
        gates: ['scope', 'purpose'],
        category: 'Article 14 - Human Oversight',
    },
    {
        id: 'euai_art14_override',
        pattern: /\b(cannot\s*be\s*(overridden|stopped)|no\s*(override|stop)\s*(capability|option)|irreversible\s*(decision|action))\b/gi,
        description: 'System without override capability',
        severity: 'high',
        gates: ['scope'],
        category: 'Article 14 - Human Oversight',
    },
];

// ============================================================================
// MAPPING TABLES
// ============================================================================

/**
 * Maps pattern IDs to prohibited practice types.
 */
export const PATTERN_TO_PROHIBITED_PRACTICE: Record<string, ProhibitedPractice> = {
    'euai_art5_1c_social_score': 'social_scoring',
    'euai_art5_1c_social_eval': 'social_scoring',
    'euai_art5_1g_biometric_race': 'biometric_categorization',
    'euai_art5_1g_biometric_politics': 'biometric_categorization',
    'euai_art5_1f_emotion_workplace': 'workplace_emotion',
    'euai_art5_1f_emotion_education': 'emotion_recognition',
    'euai_art5_1d_predictive_crime': 'predictive_policing',
    'euai_art5_1d_recidivism': 'predictive_policing',
    'euai_art5_1a_subliminal': 'subliminal_manipulation',
    'euai_art5_1a_dark_patterns': 'subliminal_manipulation',
    'euai_art5_1b_vulnerable_age': 'vulnerability_exploitation',
    'euai_art5_1b_vulnerable_disability': 'vulnerability_exploitation',
    'euai_art5_1e_realtime_biometric': 'facial_recognition_db',
    'euai_art5_1e_mass_surveillance': 'facial_recognition_db',
};

/**
 * Maps pattern IDs to high-risk contexts.
 */
export const PATTERN_TO_HIGH_RISK_CONTEXT: Record<string, HighRiskContext> = {
    'euai_annex3_biometrics': 'biometrics',
    'euai_annex3_infrastructure': 'critical_infrastructure',
    'euai_annex3_education_access': 'education',
    'euai_annex3_employment_recruit': 'employment',
    'euai_annex3_employment_manage': 'employment',
    'euai_annex3_credit': 'essential_services',
    'euai_annex3_insurance': 'essential_services',
    'euai_annex3_benefits': 'essential_services',
    'euai_annex3_law_enforcement': 'law_enforcement',
    'euai_annex3_migration': 'migration',
    'euai_annex3_justice': 'justice',
    'euai_annex3_democracy': 'democratic_processes',
    'euai_annex3_safety': 'safety_components',
};

// ============================================================================
// COMBINED EXPORTS
// ============================================================================

/**
 * All EU AI Act patterns combined.
 */
export const ALL_EU_AI_ACT_PATTERNS: CompliancePattern[] = [
    ...PROHIBITED_PRACTICE_PATTERNS,
    ...HIGH_RISK_CONTEXT_PATTERNS,
    ...TRANSPARENCY_PATTERNS,
    ...HUMAN_OVERSIGHT_PATTERNS,
];

/**
 * Gets all patterns for a specific article.
 */
export function getPatternsForArticle(article: string): CompliancePattern[] {
    return ALL_EU_AI_ACT_PATTERNS.filter(p => p.category.includes(article));
}

/**
 * Gets patterns by severity level.
 */
export function getPatternsBySeverity(severity: 'critical' | 'high' | 'medium' | 'low'): CompliancePattern[] {
    return ALL_EU_AI_ACT_PATTERNS.filter(p => p.severity === severity);
}

/**
 * Gets patterns that involve specific THSP gates.
 */
export function getPatternsByGate(gate: THSPGate): CompliancePattern[] {
    return ALL_EU_AI_ACT_PATTERNS.filter(p => p.gates.includes(gate));
}
