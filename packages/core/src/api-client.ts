/**
 * Sentinel API Client - For semantic (LLM-based) validation
 *
 * Calls the Sentinel API for real semantic analysis using LLMs.
 * Use this when you need more accurate validation than heuristics.
 *
 * Falls back to heuristic validation if API is unavailable.
 *
 * @author Sentinel Team
 * @license MIT
 */

import { validateTHSP, THSPResult } from './validator';

// =============================================================================
// TYPES
// =============================================================================

export interface ApiConfig {
  baseUrl: string;
  timeout?: number;
  apiKey?: string;
}

export interface ValidateRequest {
  text: string;
}

export interface ValidateResponse {
  is_safe: boolean;
  violations: string[];
  gates: {
    truth?: { passed: boolean; violations: string[] };
    harm?: { passed: boolean; violations: string[] };
    scope?: { passed: boolean; violations: string[] };
    purpose?: { passed: boolean; violations: string[] };
    jailbreak_detected?: boolean;
  };
}

export interface SemanticValidateRequest {
  text: string;
  provider?: 'openai' | 'anthropic';
  model?: string;
}

export interface SemanticValidateResponse {
  is_safe: boolean;
  truth_passes: boolean;
  harm_passes: boolean;
  scope_passes: boolean;
  purpose_passes: boolean;
  violated_gate: string | null;
  reasoning: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

// =============================================================================
// API CLIENT
// =============================================================================

const DEFAULT_CONFIG: ApiConfig = {
  baseUrl: 'https://api.sentinelseed.dev',
  timeout: 10000,
};

let config: ApiConfig = { ...DEFAULT_CONFIG };

/**
 * Configure the API client
 */
export function configureApi(newConfig: Partial<ApiConfig>): void {
  config = { ...config, ...newConfig };
}

/**
 * Get current API configuration
 */
export function getApiConfig(): ApiConfig {
  return { ...config };
}

/**
 * Validate text using the heuristic API endpoint
 *
 * @param text - Text to validate
 * @returns Promise<ValidateResponse>
 */
export async function validateViaApi(text: string): Promise<ValidateResponse> {
  const response = await fetch(`${config.baseUrl}/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
    },
    body: JSON.stringify({ text }),
    signal: AbortSignal.timeout(config.timeout || 10000),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Validate text using semantic (LLM-based) analysis
 *
 * @param text - Text to validate
 * @param provider - LLM provider (openai, anthropic)
 * @param model - Model to use
 * @returns Promise<SemanticValidateResponse>
 */
export async function validateSemantic(
  text: string,
  provider: 'openai' | 'anthropic' = 'openai',
  model?: string
): Promise<SemanticValidateResponse> {
  const response = await fetch(`${config.baseUrl}/validate/semantic`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
    },
    body: JSON.stringify({ text, provider, model }),
    signal: AbortSignal.timeout(config.timeout || 30000), // Semantic takes longer
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Validate with automatic fallback to heuristics if API fails
 *
 * @param text - Text to validate
 * @param preferSemantic - Whether to try semantic validation first
 * @returns Promise<THSPResult>
 */
export async function validateWithFallback(
  text: string,
  preferSemantic = false
): Promise<THSPResult> {
  // If semantic is preferred, try API first
  if (preferSemantic) {
    try {
      const result = await validateSemantic(text);
      return {
        truth: {
          passed: result.truth_passes,
          score: result.truth_passes ? 100 : 0,
          violations: result.violated_gate === 'truth' ? [result.reasoning] : [],
        },
        harm: {
          passed: result.harm_passes,
          score: result.harm_passes ? 100 : 0,
          violations: result.violated_gate === 'harm' ? [result.reasoning] : [],
        },
        scope: {
          passed: result.scope_passes,
          score: result.scope_passes ? 100 : 0,
          violations: result.violated_gate === 'scope' ? [result.reasoning] : [],
        },
        purpose: {
          passed: result.purpose_passes,
          score: result.purpose_passes ? 100 : 0,
          violations: result.violated_gate === 'purpose' ? [result.reasoning] : [],
        },
        jailbreak: {
          passed: result.is_safe,
          score: result.is_safe ? 100 : 0,
          violations: [],
        },
        overall: result.is_safe,
        summary: result.reasoning,
        riskLevel: result.risk_level,
      };
    } catch {
      // Fall through to heuristic validation
    }
  }

  // Try heuristic API
  try {
    const result = await validateViaApi(text);
    return {
      truth: {
        passed: result.gates.truth?.passed ?? true,
        score: result.gates.truth?.passed ? 100 : 0,
        violations: result.gates.truth?.violations ?? [],
      },
      harm: {
        passed: result.gates.harm?.passed ?? true,
        score: result.gates.harm?.passed ? 100 : 0,
        violations: result.gates.harm?.violations ?? [],
      },
      scope: {
        passed: result.gates.scope?.passed ?? true,
        score: result.gates.scope?.passed ? 100 : 0,
        violations: result.gates.scope?.violations ?? [],
      },
      purpose: {
        passed: result.gates.purpose?.passed ?? true,
        score: result.gates.purpose?.passed ? 100 : 0,
        violations: result.gates.purpose?.violations ?? [],
      },
      jailbreak: {
        passed: !result.gates.jailbreak_detected,
        score: result.gates.jailbreak_detected ? 0 : 100,
        violations: result.gates.jailbreak_detected ? ['Jailbreak detected'] : [],
      },
      overall: result.is_safe,
      summary: result.is_safe ? 'All gates passed' : `Violations: ${result.violations.join(', ')}`,
      riskLevel: result.is_safe ? 'low' : 'high',
    };
  } catch {
    // Final fallback: local heuristic validation
    return validateTHSP(text);
  }
}

/**
 * Check API health
 *
 * @returns Promise<boolean>
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${config.baseUrl}/health`, {
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    return false;
  }
}
