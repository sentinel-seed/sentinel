import * as vscode from 'vscode';

const OPENAI_KEY = 'sentinel.openaiApiKey';
const ANTHROPIC_KEY = 'sentinel.anthropicApiKey';

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
     */
    async setOpenAIKey(key: string): Promise<void> {
        await this.secretStorage.store(OPENAI_KEY, key);
    }

    /**
     * Get Anthropic API key from secure storage
     */
    async getAnthropicKey(): Promise<string | undefined> {
        return await this.secretStorage.get(ANTHROPIC_KEY);
    }

    /**
     * Store Anthropic API key in secure storage
     */
    async setAnthropicKey(key: string): Promise<void> {
        await this.secretStorage.store(ANTHROPIC_KEY, key);
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
            openai: !!openai,
            anthropic: !!anthropic
        };
    }

    /**
     * Migrate keys from settings to secure storage
     * Call this on activation to migrate existing keys
     */
    async migrateFromSettings(): Promise<void> {
        const config = vscode.workspace.getConfiguration('sentinel');

        // Migrate OpenAI key
        const openaiKey = config.get<string>('openaiApiKey');
        if (openaiKey && openaiKey.startsWith('sk-')) {
            await this.setOpenAIKey(openaiKey);
            // Clear from settings (user should do this manually for safety)
            vscode.window.showInformationMessage(
                'Sentinel: API key migrated to secure storage. Consider removing it from settings for security.'
            );
        }

        // Migrate Anthropic key
        const anthropicKey = config.get<string>('anthropicApiKey');
        if (anthropicKey && anthropicKey.startsWith('sk-ant-')) {
            await this.setAnthropicKey(anthropicKey);
            vscode.window.showInformationMessage(
                'Sentinel: Anthropic API key migrated to secure storage. Consider removing it from settings for security.'
            );
        }
    }
}

/**
 * Command to set API key via input prompt
 */
export async function promptForApiKey(
    secretManager: SecretManager,
    provider: 'openai' | 'anthropic'
): Promise<boolean> {
    const providerName = provider === 'openai' ? 'OpenAI' : 'Anthropic';
    const prefix = provider === 'openai' ? 'sk-' : 'sk-ant-';

    const key = await vscode.window.showInputBox({
        prompt: `Enter your ${providerName} API key`,
        password: true,
        placeHolder: `${prefix}...`,
        validateInput: (value) => {
            if (!value) {
                return 'API key is required';
            }
            if (!value.startsWith(prefix)) {
                return `${providerName} API keys should start with "${prefix}"`;
            }
            return undefined;
        }
    });

    if (key) {
        if (provider === 'openai') {
            await secretManager.setOpenAIKey(key);
        } else {
            await secretManager.setAnthropicKey(key);
        }
        vscode.window.showInformationMessage(`${providerName} API key saved securely.`);
        return true;
    }

    return false;
}
