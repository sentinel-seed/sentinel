import * as vscode from 'vscode';

const OPENAI_KEY = 'sentinel.openaiApiKey';
const ANTHROPIC_KEY = 'sentinel.anthropicApiKey';

// Common API key prefixes (for validation hints, not strict enforcement)
const OPENAI_PREFIXES = ['sk-', 'sk-proj-'];
const ANTHROPIC_PREFIXES = ['sk-ant-'];

/**
 * Secure storage for API keys using VS Code's SecretStorage
 */
export class SecretManager {
    private secretStorage: vscode.SecretStorage;

    constructor(context: vscode.ExtensionContext) {
        this.secretStorage = context.secrets;
    }

    /**
     * Get OpenAI API key from secure storage
     */
    async getOpenAIKey(): Promise<string | undefined> {
        return await this.secretStorage.get(OPENAI_KEY);
    }

    /**
     * Store OpenAI API key in secure storage
     * Validates that key is not empty
     */
    async setOpenAIKey(key: string): Promise<void> {
        if (!key || key.trim() === '') {
            throw new Error('API key cannot be empty');
        }
        await this.secretStorage.store(OPENAI_KEY, key.trim());
    }

    /**
     * Get Anthropic API key from secure storage
     */
    async getAnthropicKey(): Promise<string | undefined> {
        return await this.secretStorage.get(ANTHROPIC_KEY);
    }

    /**
     * Store Anthropic API key in secure storage
     * Validates that key is not empty
     */
    async setAnthropicKey(key: string): Promise<void> {
        if (!key || key.trim() === '') {
            throw new Error('API key cannot be empty');
        }
        await this.secretStorage.store(ANTHROPIC_KEY, key.trim());
    }

    /**
     * Delete a stored key
     */
    async deleteKey(provider: 'openai' | 'anthropic'): Promise<void> {
        const key = provider === 'openai' ? OPENAI_KEY : ANTHROPIC_KEY;
        await this.secretStorage.delete(key);
    }

    /**
     * Check if keys are stored in secure storage
     */
    async hasStoredKeys(): Promise<{ openai: boolean; anthropic: boolean }> {
        const openai = await this.getOpenAIKey();
        const anthropic = await this.getAnthropicKey();
        return {
            openai: !!openai && openai.trim() !== '',
            anthropic: !!anthropic && anthropic.trim() !== ''
        };
    }

    /**
     * Migrate keys from settings to secure storage
     * Call this on activation to migrate existing keys
     */
    async migrateFromSettings(): Promise<void> {
        const config = vscode.workspace.getConfiguration('sentinel');
        let migrated = false;

        // Migrate OpenAI key - accept any key that looks like an API key
        const openaiKey = config.get<string>('openaiApiKey');
        if (openaiKey && openaiKey.trim() !== '' && this.looksLikeApiKey(openaiKey)) {
            await this.setOpenAIKey(openaiKey);
            migrated = true;
        }

        // Migrate Anthropic key
        const anthropicKey = config.get<string>('anthropicApiKey');
        if (anthropicKey && anthropicKey.trim() !== '' && this.looksLikeApiKey(anthropicKey)) {
            await this.setAnthropicKey(anthropicKey);
            migrated = true;
        }

        // Offer to clear settings if keys were migrated
        if (migrated) {
            const choice = await vscode.window.showInformationMessage(
                'Sentinel: API keys migrated to secure storage. Remove from settings for security?',
                'Yes, remove from settings',
                'No, keep them'
            );

            if (choice === 'Yes, remove from settings') {
                await this.clearSettingsKeys();
            }
        }
    }

    /**
     * Check if a string looks like an API key (basic validation)
     */
    private looksLikeApiKey(value: string): boolean {
        // At minimum, should be reasonably long and not obviously wrong
        return value.length >= 20;
    }

    /**
     * Clear API keys from VS Code settings
     */
    private async clearSettingsKeys(): Promise<void> {
        const config = vscode.workspace.getConfiguration('sentinel');
        try {
            await config.update('openaiApiKey', undefined, vscode.ConfigurationTarget.Global);
            await config.update('anthropicApiKey', undefined, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage('Sentinel: API keys removed from settings.');
        } catch (error) {
            console.warn('Failed to clear API keys from settings:', error);
        }
    }
}

/**
 * Command to set API key via input prompt
 * Uses flexible validation that warns but doesn't block non-standard key formats
 */
export async function promptForApiKey(
    secretManager: SecretManager,
    provider: 'openai' | 'anthropic'
): Promise<boolean> {
    const providerName = provider === 'openai' ? 'OpenAI' : 'Anthropic';
    const expectedPrefixes = provider === 'openai' ? OPENAI_PREFIXES : ANTHROPIC_PREFIXES;
    const placeholderPrefix = expectedPrefixes[0];

    const key = await vscode.window.showInputBox({
        prompt: `Enter your ${providerName} API key`,
        password: true,
        placeHolder: `${placeholderPrefix}...`,
        validateInput: (value) => {
            if (!value || value.trim() === '') {
                return 'API key is required';
            }

            // Minimum length check
            if (value.length < 20) {
                return 'API key seems too short. Please check and try again.';
            }

            // Warn about unexpected prefix but don't block
            const hasExpectedPrefix = expectedPrefixes.some(prefix => value.startsWith(prefix));
            if (!hasExpectedPrefix) {
                // Return warning as hint, not error (null allows submission)
                return undefined; // Allow non-standard keys
            }

            return undefined;
        }
    });

    if (key && key.trim() !== '') {
        try {
            if (provider === 'openai') {
                await secretManager.setOpenAIKey(key);
            } else {
                await secretManager.setAnthropicKey(key);
            }
            vscode.window.showInformationMessage(`${providerName} API key saved securely.`);
            return true;
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            vscode.window.showErrorMessage(`Failed to save API key: ${message}`);
            return false;
        }
    }

    return false;
}
