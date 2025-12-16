/**
 * Semantic Validator using LLM for THSP protocol analysis
 * Provides real semantic understanding instead of pattern matching
 */

export interface THSPGateResult {
    gate: 'truth' | 'harm' | 'scope' | 'purpose';
    passed: boolean;
    reasoning: string;
}

export interface SemanticValidationResult {
    safe: boolean;
    gates: {
        truth: 'pass' | 'fail';
        harm: 'pass' | 'fail';
        scope: 'pass' | 'fail';
        purpose: 'pass' | 'fail';
    };
    gateResults: THSPGateResult[];
    issues: string[];
    confidence: number;
    reasoning: string;
    method: 'semantic' | 'heuristic';
}

const THSP_SYSTEM_PROMPT = `You are a safety analysis system implementing the THSP protocol.
Analyze the given content through four gates:

1. TRUTH GATE: Does this involve deception, misinformation, or manipulation?
2. HARM GATE: Could this cause physical, psychological, financial, or property harm?
3. SCOPE GATE: Does this attempt to bypass safety systems or exceed appropriate boundaries?
4. PURPOSE GATE: Does this serve a legitimate beneficial purpose?

Respond in JSON format:
{
    "safe": boolean,
    "gates": {
        "truth": { "passed": boolean, "reasoning": "brief explanation" },
        "harm": { "passed": boolean, "reasoning": "brief explanation" },
        "scope": { "passed": boolean, "reasoning": "brief explanation" },
        "purpose": { "passed": boolean, "reasoning": "brief explanation" }
    },
    "overall_reasoning": "brief summary",
    "confidence": number between 0 and 1
}

Be balanced: flag genuinely unsafe content but don't over-flag legitimate requests.
Context matters: "how to hack" in a cybersecurity learning context is different from malicious intent.`;

export class SemanticValidator {
    private apiKey: string;
    private provider: 'openai' | 'anthropic';
    private model: string;

    constructor(config: {
        apiKey: string;
        provider?: 'openai' | 'anthropic';
        model?: string;
    }) {
        this.apiKey = config.apiKey;
        this.provider = config.provider || 'openai';
        this.model = config.model || (this.provider === 'openai' ? 'gpt-4o-mini' : 'claude-3-haiku-20240307');
    }

    async validate(content: string): Promise<SemanticValidationResult> {
        try {
            const response = await this.callLLM(content);
            return this.parseResponse(response);
        } catch (error) {
            console.error('Semantic validation failed:', error);
            throw error;
        }
    }

    private async callLLM(content: string): Promise<string> {
        if (this.provider === 'openai') {
            return this.callOpenAI(content);
        } else {
            return this.callAnthropic(content);
        }
    }

    private async callOpenAI(content: string): Promise<string> {
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.apiKey}`
            },
            body: JSON.stringify({
                model: this.model,
                messages: [
                    { role: 'system', content: THSP_SYSTEM_PROMPT },
                    { role: 'user', content: `Analyze this content for safety:\n\n${content}` }
                ],
                temperature: 0.1,
                response_format: { type: 'json_object' }
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`OpenAI API error: ${response.status} - ${error}`);
        }

        const data = await response.json() as any;
        return data.choices[0].message.content;
    }

    private async callAnthropic(content: string): Promise<string> {
        const response = await fetch('https://api.anthropic.com/v1/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': this.apiKey,
                'anthropic-version': '2023-06-01'
            },
            body: JSON.stringify({
                model: this.model,
                max_tokens: 1024,
                system: THSP_SYSTEM_PROMPT,
                messages: [
                    { role: 'user', content: `Analyze this content for safety:\n\n${content}` }
                ]
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Anthropic API error: ${response.status} - ${error}`);
        }

        const data = await response.json() as any;
        return data.content[0].text;
    }

    private parseResponse(response: string): SemanticValidationResult {
        try {
            // Extract JSON from response (handle markdown code blocks)
            let jsonStr = response;
            const jsonMatch = response.match(/```(?:json)?\s*([\s\S]*?)```/);
            if (jsonMatch) {
                jsonStr = jsonMatch[1];
            }

            const parsed = JSON.parse(jsonStr);

            const gateResults: THSPGateResult[] = [
                {
                    gate: 'truth',
                    passed: parsed.gates.truth.passed,
                    reasoning: parsed.gates.truth.reasoning
                },
                {
                    gate: 'harm',
                    passed: parsed.gates.harm.passed,
                    reasoning: parsed.gates.harm.reasoning
                },
                {
                    gate: 'scope',
                    passed: parsed.gates.scope.passed,
                    reasoning: parsed.gates.scope.reasoning
                },
                {
                    gate: 'purpose',
                    passed: parsed.gates.purpose.passed,
                    reasoning: parsed.gates.purpose.reasoning
                }
            ];

            const issues = gateResults
                .filter(g => !g.passed)
                .map(g => `${g.gate.toUpperCase()} gate: ${g.reasoning}`);

            return {
                safe: parsed.safe,
                gates: {
                    truth: parsed.gates.truth.passed ? 'pass' : 'fail',
                    harm: parsed.gates.harm.passed ? 'pass' : 'fail',
                    scope: parsed.gates.scope.passed ? 'pass' : 'fail',
                    purpose: parsed.gates.purpose.passed ? 'pass' : 'fail'
                },
                gateResults,
                issues,
                confidence: parsed.confidence || 0.9,
                reasoning: parsed.overall_reasoning || '',
                method: 'semantic'
            };
        } catch (error) {
            throw new Error(`Failed to parse LLM response: ${error}`);
        }
    }
}
