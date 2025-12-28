/**
 * @fileoverview Unit tests for RulesTab component
 *
 * Tests rule management functionality including:
 * - Loading and displaying rules
 * - Creating new rules
 * - Editing existing rules
 * - Deleting rules
 * - Import/export functionality
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { RulesTab } from '../RulesTab';
import type { ApprovalRule } from '../../../types';

// Mock chrome.runtime
const mockSendMessage = jest.fn();

global.chrome = {
  runtime: {
    sendMessage: mockSendMessage,
  },
} as unknown as typeof chrome;

// Mock i18n
jest.mock('../../../lib/i18n', () => ({
  t: (key: string) => {
    const translations: Record<string, string> = {
      rules: 'Rules',
      newRule: 'New Rule',
      export: 'Export',
      import: 'Import',
      noRulesDesc: 'No rules configured yet',
      createFirstRule: 'Create First Rule',
      createRule: 'Create Rule',
      editRule: 'Edit Rule',
      name: 'Name',
      description: 'Description',
      priority: 'Priority',
      conditions: 'Conditions',
      action: 'Action',
      reason: 'Reason',
      enabled: 'Enabled',
      disable: 'Disable',
      enable: 'Enable',
      edit: 'Edit',
      delete: 'Delete',
      deleteRule: 'Delete Rule',
      deleteRuleConfirm: 'Are you sure you want to delete this rule?',
      cancel: 'Cancel',
      save: 'Save',
    };
    return translations[key] || key;
  },
}));

// Helper to create mock rules
function createMockRule(overrides: Partial<ApprovalRule> = {}): ApprovalRule {
  return {
    id: 'rule-123',
    name: 'Test Rule',
    description: 'A test rule',
    priority: 50,
    enabled: true,
    conditions: [
      { field: 'riskLevel', operator: 'equals', value: 'high' },
    ],
    action: 'require_approval',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    ...overrides,
  };
}

describe('RulesTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('loading state', () => {
    it('should show loading state initially', () => {
      mockSendMessage.mockImplementation(() => new Promise(() => {}));

      render(<RulesTab />);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty state when no rules exist', async () => {
      mockSendMessage.mockResolvedValue([]);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText(/no rules/i)).toBeInTheDocument();
      });
    });

    it('should show create first rule button in empty state', async () => {
      mockSendMessage.mockResolvedValue([]);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Create First Rule')).toBeInTheDocument();
      });
    });
  });

  describe('displaying rules', () => {
    it('should display rules list when rules exist', async () => {
      const rules = [
        createMockRule({ id: 'rule-1', name: 'Rule One' }),
        createMockRule({ id: 'rule-2', name: 'Rule Two' }),
      ];
      mockSendMessage.mockResolvedValue(rules);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Rule One')).toBeInTheDocument();
        expect(screen.getByText('Rule Two')).toBeInTheDocument();
      });
    });

    it('should display rule priority', async () => {
      const rules = [createMockRule({ priority: 75 })];
      mockSendMessage.mockResolvedValue(rules);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('P75')).toBeInTheDocument();
      });
    });

    it('should display rule action badge', async () => {
      const rules = [createMockRule({ action: 'auto_approve' })];
      mockSendMessage.mockResolvedValue(rules);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText(/auto approve/i)).toBeInTheDocument();
      });
    });

    it('should display disabled rule with reduced opacity style', async () => {
      const rules = [createMockRule({ enabled: false })];
      mockSendMessage.mockResolvedValue(rules);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('OFF')).toBeInTheDocument();
      });
    });
  });

  describe('creating rules', () => {
    it('should open editor when clicking new rule button', async () => {
      mockSendMessage.mockResolvedValue([]);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Create First Rule')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Create First Rule'));

      expect(screen.getByText('Create Rule')).toBeInTheDocument();
    });

    it('should call APPROVAL_CREATE_RULE when saving new rule', async () => {
      mockSendMessage
        .mockResolvedValueOnce([]) // Initial load
        .mockResolvedValueOnce({ id: 'new-rule' }) // Create rule
        .mockResolvedValueOnce([]); // Reload after create

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Create First Rule')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Create First Rule'));

      // Fill in the form
      const nameInput = screen.getByPlaceholderText(/block high-risk/i);
      fireEvent.change(nameInput, { target: { value: 'My New Rule' } });

      // Save
      fireEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'APPROVAL_CREATE_RULE',
            payload: expect.objectContaining({
              name: 'My New Rule',
            }),
          })
        );
      });
    });
  });

  describe('toggling rules', () => {
    it('should call APPROVAL_UPDATE_RULE when toggling rule', async () => {
      const rules = [createMockRule({ enabled: true })];
      mockSendMessage
        .mockResolvedValueOnce(rules) // Initial load
        .mockResolvedValueOnce({ ...rules[0], enabled: false }) // Toggle
        .mockResolvedValueOnce(rules); // Reload

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('ON')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('ON'));

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'APPROVAL_UPDATE_RULE',
            payload: expect.objectContaining({
              enabled: false,
            }),
          })
        );
      });
    });
  });

  describe('deleting rules', () => {
    it('should show confirmation dialog when clicking delete', async () => {
      const rules = [createMockRule()];
      mockSendMessage.mockResolvedValue(rules);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Rule')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Delete'));

      expect(screen.getByText('Delete Rule')).toBeInTheDocument();
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });

    it('should call APPROVAL_DELETE_RULE when confirming deletion', async () => {
      const rules = [createMockRule({ id: 'rule-to-delete' })];
      mockSendMessage
        .mockResolvedValueOnce(rules) // Initial load
        .mockResolvedValueOnce(true) // Delete
        .mockResolvedValueOnce([]); // Reload

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Rule')).toBeInTheDocument();
      });

      // Click delete button
      fireEvent.click(screen.getByText('Delete'));

      // Confirm deletion - find the confirm button in the dialog
      const confirmButtons = screen.getAllByRole('button');
      const deleteConfirmButton = confirmButtons.find(
        btn => btn.textContent === 'Delete' && btn !== screen.getByText('Delete')
      );

      if (deleteConfirmButton) {
        fireEvent.click(deleteConfirmButton);
      }

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'APPROVAL_DELETE_RULE',
            payload: 'rule-to-delete',
          })
        );
      });
    });
  });

  describe('editing rules', () => {
    it('should open editor with rule data when clicking edit', async () => {
      const rules = [createMockRule({ name: 'Existing Rule', description: 'Existing description' })];
      mockSendMessage.mockResolvedValue(rules);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Existing Rule')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Edit'));

      expect(screen.getByText('Edit Rule')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Existing Rule')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Existing description')).toBeInTheDocument();
    });
  });

  describe('message handling', () => {
    it('should send APPROVAL_GET_RULES on mount', async () => {
      mockSendMessage.mockResolvedValue([]);

      render(<RulesTab />);

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({ type: 'APPROVAL_GET_RULES' });
      });
    });
  });

  describe('error handling', () => {
    it('should show error state when loading fails', async () => {
      mockSendMessage.mockRejectedValue(new Error('Network error'));

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    it('should retry loading when clicking retry button', async () => {
      mockSendMessage
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce([]);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Retry'));

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('priority validation', () => {
    it('should clamp priority to 0-1000 range', async () => {
      mockSendMessage.mockResolvedValue([]);

      render(<RulesTab />);

      await waitFor(() => {
        expect(screen.getByText('Create First Rule')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Create First Rule'));

      // Find priority input by label
      const priorityLabel = screen.getByText(/priority/i);
      const priorityInput = priorityLabel.parentElement?.querySelector('input[type="number"]');

      expect(priorityInput).toBeInTheDocument();
      expect(priorityInput).toHaveAttribute('min', '0');
      expect(priorityInput).toHaveAttribute('max', '1000');
    });
  });
});
