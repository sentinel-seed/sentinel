/**
 * @fileoverview Unit tests for SettingsTab component
 *
 * Tests settings functionality including:
 * - Loading and displaying settings
 * - Section navigation
 * - Updating general settings
 * - AgentShield settings
 * - MCPGateway settings
 * - Approval settings
 * - Advanced data management
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SettingsTab } from '../SettingsTab';
import type { Settings } from '../../../types';

// Mock chrome.runtime
const mockSendMessage = jest.fn();

global.chrome = {
  runtime: {
    sendMessage: mockSendMessage,
  },
} as unknown as typeof chrome;

// Mock URL.createObjectURL and URL.revokeObjectURL for export
global.URL.createObjectURL = jest.fn(() => 'blob:test');
global.URL.revokeObjectURL = jest.fn();

// Mock i18n
jest.mock('../../../lib/i18n', () => ({
  t: (key: string) => {
    const translations: Record<string, string> = {
      loading: 'Loading...',
      general: 'General',
      agentShield: 'Agent Shield',
      mcpGateway: 'MCP Gateway',
      approval: 'Approval',
      advanced: 'Advanced',
      enabled: 'Enabled',
      enableProtection: 'Enable protection',
      protectionLevel: 'Protection Level',
      howAggressive: 'How aggressive',
      notifications: 'Notifications',
      showNotifications: 'Show notifications',
      language: 'Language',
      selectLanguage: 'Select language',
      protectedPlatforms: 'Protected Platforms',
      basic: 'Basic',
      recommended: 'Recommended',
      maximum: 'Maximum',
      agentShieldDesc: 'Protect against malicious AI agent actions',
      enableAgentShield: 'Enable Agent Shield',
      trustThreshold: 'Trust Threshold',
      trustThresholdDesc: 'Minimum trust level',
      memoryInjectionDetection: 'Memory Injection Detection',
      memoryInjectionDesc: 'Scan for injection',
      maxAutoApproveValue: 'Max Auto-Approve Value',
      maxAutoApproveDesc: 'Maximum value for auto-approval',
      mcpGatewayDesc: 'Monitor MCP server tool calls',
      enableMCPGateway: 'Enable MCP Gateway',
      interceptAll: 'Intercept All Tools',
      interceptAllDesc: 'Intercept all tool calls',
      trustedServers: 'Trusted Servers',
      trustedServersDesc: 'Servers that bypass approval',
      serverNamePlaceholder: 'Enter server name...',
      noTrustedServers: 'No trusted servers',
      approvalDesc: 'Configure action approval',
      enableApproval: 'Enable approval',
      defaultAction: 'Default Action',
      defaultActionDesc: 'Action when no rules match',
      autoApprove: 'Auto-approve',
      autoReject: 'Auto-reject',
      requireApproval: 'Require Approval',
      approvalTimeout: 'Approval Timeout',
      approvalTimeoutDesc: 'Time before expiry',
      approvalNotifications: 'Approval Notifications',
      approvalNotificationsDesc: 'Show notifications',
      dataManagement: 'Data Management',
      exportSettings: 'Export Settings',
      exportSettingsDesc: 'Download as JSON',
      importSettings: 'Import Settings',
      importSettingsDesc: 'Load from JSON',
      resetSettings: 'Reset to Defaults',
      resetSettingsDesc: 'Restore default values',
      reset: 'Reset',
      resetSettingsConfirm: 'Are you sure you want to reset?',
      clearAllData: 'Clear All Data',
      clearAllDataDesc: 'Delete all data',
      clearData: 'Clear Data',
      clearAllDataConfirm: 'Are you sure you want to clear all data?',
      about: 'About',
      version: 'Version',
      website: 'Website',
      github: 'GitHub',
      export: 'Export',
      import: 'Import',
      cancel: 'Cancel',
    };
    return translations[key] || key;
  },
  setLanguage: jest.fn(),
  getAvailableLanguages: () => [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'pt', name: 'Português' },
  ],
  Translations: {},
}));

// Helper to create mock settings
function createMockSettings(overrides: Partial<Settings> = {}): Settings {
  return {
    enabled: true,
    protectionLevel: 'recommended',
    platforms: ['chatgpt', 'claude'],
    notifications: true,
    language: 'en',
    agentShield: {
      enabled: true,
      trustThreshold: 70,
      memoryInjectionDetection: true,
      maxAutoApproveValue: 100,
    },
    mcpGateway: {
      enabled: true,
      interceptAll: true,
      trustedServers: [],
    },
    approval: {
      enabled: true,
      defaultAction: 'require_approval',
      showNotifications: true,
      autoRejectTimeoutMs: 300000,
    },
    ...overrides,
  };
}

describe('SettingsTab', () => {
  const mockOnUpdate = jest.fn();
  const mockOnLanguageChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('loading state', () => {
    it('should show loading state when settings is null', () => {
      render(
        <SettingsTab
          settings={null}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe('section navigation', () => {
    it('should display all section buttons', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      expect(screen.getByText('General')).toBeInTheDocument();
      expect(screen.getByText('Agent Shield')).toBeInTheDocument();
      expect(screen.getByText('MCP Gateway')).toBeInTheDocument();
      expect(screen.getByText('Approval')).toBeInTheDocument();
      expect(screen.getByText('Advanced')).toBeInTheDocument();
    });

    it('should switch sections when clicking navigation buttons', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      // Click Agent Shield section
      fireEvent.click(screen.getByText('Agent Shield'));

      // Should show Agent Shield content
      expect(screen.getByText('Trust Threshold')).toBeInTheDocument();
    });
  });

  describe('general settings', () => {
    it('should display general settings by default', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      expect(screen.getByText('Enabled')).toBeInTheDocument();
      expect(screen.getByText('Protection Level')).toBeInTheDocument();
      expect(screen.getByText('Language')).toBeInTheDocument();
    });

    it('should toggle enabled setting', async () => {
      const settings = createMockSettings({ enabled: true });
      mockSendMessage.mockResolvedValue({ ...settings, enabled: false });

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      // There are multiple ON toggles, get all and click the first one (Enabled)
      const toggleButtons = screen.getAllByText('ON');
      fireEvent.click(toggleButtons[0]);

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'UPDATE_SETTINGS',
          payload: { enabled: false },
        });
      });
    });

    it('should display protected platforms', () => {
      const settings = createMockSettings({ platforms: ['chatgpt', 'claude'] });

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      expect(screen.getByText('Protected Platforms')).toBeInTheDocument();
      expect(screen.getByText('Chatgpt')).toBeInTheDocument();
      expect(screen.getByText('Claude')).toBeInTheDocument();
    });
  });

  describe('agentShield settings', () => {
    it('should display Agent Shield settings', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Agent Shield'));

      expect(screen.getByText('Trust Threshold')).toBeInTheDocument();
      expect(screen.getByText('Memory Injection Detection')).toBeInTheDocument();
      expect(screen.getByText('Max Auto-Approve Value')).toBeInTheDocument();
    });

    it('should display trust threshold slider value', () => {
      const settings = createMockSettings({
        agentShield: {
          enabled: true,
          trustThreshold: 75,
          memoryInjectionDetection: true,
          maxAutoApproveValue: 100,
        },
      });

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Agent Shield'));

      expect(screen.getByText('75%')).toBeInTheDocument();
    });
  });

  describe('mcpGateway settings', () => {
    it('should display MCP Gateway settings', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('MCP Gateway'));

      expect(screen.getByText('Intercept All Tools')).toBeInTheDocument();
      expect(screen.getByText('Trusted Servers')).toBeInTheDocument();
    });

    it('should display trusted servers list', () => {
      const settings = createMockSettings({
        mcpGateway: {
          enabled: true,
          interceptAll: true,
          trustedServers: ['file-server', 'db-server'],
        },
      });

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('MCP Gateway'));

      expect(screen.getByText('file-server')).toBeInTheDocument();
      expect(screen.getByText('db-server')).toBeInTheDocument();
    });

    it('should add trusted server', async () => {
      const settings = createMockSettings({
        mcpGateway: {
          enabled: true,
          interceptAll: true,
          trustedServers: [],
        },
      });

      const updatedSettings = {
        ...settings,
        mcpGateway: {
          ...settings.mcpGateway,
          trustedServers: ['new-server'],
        },
      };
      mockSendMessage.mockResolvedValue(updatedSettings);

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('MCP Gateway'));

      const input = screen.getByPlaceholderText('Enter server name...');
      fireEvent.change(input, { target: { value: 'new-server' } });

      const addButton = screen.getByText('+');
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'UPDATE_SETTINGS',
          payload: {
            mcpGateway: expect.objectContaining({
              trustedServers: ['new-server'],
            }),
          },
        });
      });
    });
  });

  describe('approval settings', () => {
    it('should display approval settings', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Approval'));

      expect(screen.getByText('Default Action')).toBeInTheDocument();
      expect(screen.getByText('Approval Timeout')).toBeInTheDocument();
      expect(screen.getByText('Approval Notifications')).toBeInTheDocument();
    });

    it('should display timeout options', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Approval'));

      // Find the timeout select
      const selects = screen.getAllByRole('combobox');
      const timeoutSelect = selects.find((s) =>
        Array.from((s as HTMLSelectElement).options).some((opt) => opt.text === '5 min')
      );

      expect(timeoutSelect).toBeTruthy();
    });
  });

  describe('advanced settings', () => {
    it('should display advanced settings', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Advanced'));

      expect(screen.getByText('Data Management')).toBeInTheDocument();
      expect(screen.getByText('Export Settings')).toBeInTheDocument();
      expect(screen.getByText('Import Settings')).toBeInTheDocument();
      expect(screen.getByText('Reset to Defaults')).toBeInTheDocument();
      expect(screen.getByText('Clear All Data')).toBeInTheDocument();
    });

    it('should display about section', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Advanced'));

      expect(screen.getByText('About')).toBeInTheDocument();
      expect(screen.getByText('Version')).toBeInTheDocument();
      expect(screen.getByText('Website')).toBeInTheDocument();
      expect(screen.getByText('GitHub')).toBeInTheDocument();
    });

    it('should show reset confirmation dialog', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Advanced'));
      fireEvent.click(screen.getByText('Reset'));

      // There will be multiple "Reset to Defaults" - one in the settings, one in dialog
      const resetTexts = screen.getAllByText('Reset to Defaults');
      expect(resetTexts.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });

    it('should show clear data confirmation dialog', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Advanced'));
      fireEvent.click(screen.getByText('Clear Data'));

      // There will be multiple "Clear All Data" elements
      const clearTexts = screen.getAllByText('Clear All Data');
      expect(clearTexts.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });

    it('should have export button', () => {
      const settings = createMockSettings();

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      fireEvent.click(screen.getByText('Advanced'));
      expect(screen.getByText('Export')).toBeInTheDocument();
    });
  });

  describe('error handling', () => {
    it('should handle update errors gracefully', async () => {
      const settings = createMockSettings();
      mockSendMessage.mockRejectedValue(new Error('Network error'));

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <SettingsTab
          settings={settings}
          onUpdate={mockOnUpdate}
          onLanguageChange={mockOnLanguageChange}
        />
      );

      // Find all toggle buttons and click the first one (Enabled toggle)
      const toggleButtons = screen.getAllByText('ON');
      fireEvent.click(toggleButtons[0]);

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          '[SettingsTab] Failed to update setting:',
          expect.any(Error)
        );
      });

      consoleSpy.mockRestore();
    });
  });
});
