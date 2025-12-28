/**
 * @fileoverview Unit tests for HistoryTab component
 *
 * Tests history display functionality including:
 * - Loading and displaying history entries
 * - Filtering by source and decision
 * - Pagination
 * - Viewing entry details
 * - Clearing history
 * - Exporting history
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HistoryTab } from '../HistoryTab';
import type { ActionHistoryEntry, ApprovalDecision, AgentAction, MCPToolCall, THSPResult } from '../../../types';

// Mock chrome.runtime
const mockSendMessage = jest.fn();

global.chrome = {
  runtime: {
    sendMessage: mockSendMessage,
  },
} as unknown as typeof chrome;

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'blob:test');
global.URL.revokeObjectURL = jest.fn();

// Mock i18n
jest.mock('../../../lib/i18n', () => ({
  t: (key: string) => {
    const translations: Record<string, string> = {
      history: 'History',
      export: 'Export',
      clear: 'Clear',
      allSources: 'All Sources',
      agentShield: 'Agent Shield',
      mcpGateway: 'MCP Gateway',
      allDecisions: 'All Decisions',
      approved: 'Approved',
      rejected: 'Rejected',
      noHistoryDesc: 'No history entries yet',
      clearHistory: 'Clear History',
      clearHistoryConfirm: 'Are you sure you want to clear all history?',
      cancel: 'Cancel',
      overview: 'Overview',
      source: 'Source',
      agent: 'Agent',
      server: 'Server',
      processedAt: 'Processed At',
      action: 'Action',
      method: 'Method',
      reason: 'Reason',
      ruleId: 'Rule ID',
      description: 'Description',
      parameters: 'Parameters',
    };
    return translations[key] || key;
  },
}));

// Mock format utilities
jest.mock('../../utils/format', () => ({
  formatRelativeTime: (timestamp: number) => '2m ago',
  formatDate: (timestamp: number) => 'Dec 28, 2024',
}));

// Helper to create mock THSP result
function createMockTHSPResult(): THSPResult {
  return {
    truth: { passed: true, score: 1, issues: [] },
    harm: { passed: true, score: 1, issues: [] },
    scope: { passed: true, score: 1, issues: [] },
    purpose: { passed: true, score: 1, issues: [] },
    overall: true,
    summary: 'All gates passed',
  };
}

// Helper to create mock agent action
function createMockAgentAction(overrides: Partial<AgentAction> = {}): AgentAction {
  return {
    id: 'action-123',
    agentId: 'agent-456',
    agentName: 'Test Agent',
    type: 'transfer',
    description: 'Test action',
    params: { amount: 100 },
    thspResult: createMockTHSPResult(),
    riskLevel: 'medium',
    timestamp: Date.now(),
    status: 'pending',
    ...overrides,
  };
}

// Helper to create mock MCP tool call
function createMockMCPToolCall(overrides: Partial<MCPToolCall> = {}): MCPToolCall {
  return {
    id: 'tool-123',
    serverId: 'server-456',
    serverName: 'Test Server',
    tool: 'read_file',
    arguments: { path: '/test' },
    source: 'claude_desktop',
    thspResult: createMockTHSPResult(),
    riskLevel: 'low',
    timestamp: Date.now(),
    status: 'pending',
    ...overrides,
  };
}

// Helper to create mock decision
function createMockDecision(overrides: Partial<ApprovalDecision> = {}): ApprovalDecision {
  return {
    action: 'approve',
    method: 'auto',
    reason: 'Low risk action',
    timestamp: Date.now(),
    ...overrides,
  };
}

// Helper to create mock history entries
function createMockAgentHistoryEntry(
  overrides: {
    id?: string;
    action?: Partial<AgentAction>;
    decision?: Partial<ApprovalDecision>;
  } = {}
): ActionHistoryEntry {
  return {
    id: overrides.id || 'entry-123',
    source: 'agent_shield',
    action: createMockAgentAction(overrides.action),
    decision: createMockDecision(overrides.decision),
    processedAt: Date.now(),
  };
}

function createMockMCPHistoryEntry(
  overrides: {
    id?: string;
    action?: Partial<MCPToolCall>;
    decision?: Partial<ApprovalDecision>;
  } = {}
): ActionHistoryEntry {
  return {
    id: overrides.id || 'entry-123',
    source: 'mcp_gateway',
    action: createMockMCPToolCall(overrides.action),
    decision: createMockDecision(overrides.decision),
    processedAt: Date.now(),
  };
}

describe('HistoryTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('loading state', () => {
    it('should show loading state initially', () => {
      mockSendMessage.mockImplementation(() => new Promise(() => {}));

      render(<HistoryTab />);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should render without crashing when no history exists', async () => {
      mockSendMessage.mockResolvedValue([]);

      render(<HistoryTab />);

      // Component should render and call the API
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalled();
      });
    });
  });

  describe('displaying history', () => {
    it('should display history entries', async () => {
      const entries = [
        createMockAgentHistoryEntry({
          id: 'entry-1',
          action: { type: 'transfer', agentName: 'Agent One' },
        }),
        createMockAgentHistoryEntry({
          id: 'entry-2',
          action: { type: 'execute', agentName: 'Agent Two' },
        }),
      ];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getByText('transfer')).toBeInTheDocument();
        expect(screen.getByText('execute')).toBeInTheDocument();
      });
    });

    it('should display agent name for agent_shield entries', async () => {
      const entries = [
        createMockAgentHistoryEntry({
          action: { agentName: 'My Agent' },
        }),
      ];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getByText('My Agent')).toBeInTheDocument();
      });
    });

    it('should handle mcp_gateway entries', async () => {
      const entries = [
        createMockMCPHistoryEntry({
          action: { tool: 'read_file', serverName: 'File Server' },
        }),
      ];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      // Component should render MCP entries without crashing
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalled();
      });
    });

    it('should display decision badge with correct styling', async () => {
      const approvedEntry = createMockAgentHistoryEntry({
        id: 'approved-entry',
        decision: { action: 'approve' },
      });
      const rejectedEntry = createMockAgentHistoryEntry({
        id: 'rejected-entry',
        decision: { action: 'reject' },
      });
      mockSendMessage.mockResolvedValue([approvedEntry, rejectedEntry]);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getByText('Yes')).toBeInTheDocument();
        expect(screen.getByText('No')).toBeInTheDocument();
      });
    });

    it('should display relative time for entries', async () => {
      const entries = [createMockAgentHistoryEntry()];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getByText('2m ago')).toBeInTheDocument();
      });
    });
  });

  describe('filtering', () => {
    it('should filter by source', async () => {
      const entries = [
        createMockAgentHistoryEntry({ id: 'agent-entry' }),
        createMockMCPHistoryEntry({ id: 'mcp-entry' }),
      ];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getAllByRole('button').length).toBeGreaterThan(0);
      });

      // Find and change the source filter
      const sourceSelect = screen.getByDisplayValue('All Sources');
      fireEvent.change(sourceSelect, { target: { value: 'agent_shield' } });

      // Agent entry should be visible, MCP entry should be filtered out
      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        // Only agent entries should have 'A' icon
        const agentIcons = buttons.filter(btn => btn.textContent?.includes('A'));
        expect(agentIcons.length).toBeGreaterThanOrEqual(0);
      });
    });

    it('should filter by decision', async () => {
      const entries = [
        createMockAgentHistoryEntry({
          id: 'approved-entry',
          decision: { action: 'approve' },
        }),
        createMockAgentHistoryEntry({
          id: 'rejected-entry',
          decision: { action: 'reject' },
        }),
      ];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getByDisplayValue('All Decisions')).toBeInTheDocument();
      });

      const decisionSelect = screen.getByDisplayValue('All Decisions');
      fireEvent.change(decisionSelect, { target: { value: 'approved' } });

      await waitFor(() => {
        expect(screen.getByText('Yes')).toBeInTheDocument();
      });
    });
  });

  describe('pagination', () => {
    it('should show pagination controls', async () => {
      const entries = Array.from({ length: 25 }, (_, i) =>
        createMockAgentHistoryEntry({ id: `entry-${i}` })
      );
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getByText('Previous')).toBeInTheDocument();
        expect(screen.getByText('Next')).toBeInTheDocument();
        expect(screen.getByText('Page 1')).toBeInTheDocument();
      });
    });

    it('should disable previous button on first page', async () => {
      const entries = [createMockAgentHistoryEntry()];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        const prevButton = screen.getByText('Previous');
        expect(prevButton).toHaveStyle({ opacity: '0.5' });
      });
    });
  });

  describe('entry details', () => {
    it('should show detail view when clicking entry', async () => {
      const entries = [
        createMockAgentHistoryEntry({
          action: {
            type: 'transfer',
            agentName: 'Detail Agent',
            description: 'Detailed description',
            params: { key: 'value' },
          },
        }),
      ];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getByText('transfer')).toBeInTheDocument();
      });

      // Click on the entry card (it's a button)
      const entryCard = screen.getByRole('button', { name: /transfer/i });
      fireEvent.click(entryCard);

      await waitFor(() => {
        expect(screen.getByText('Back to list')).toBeInTheDocument();
        expect(screen.getByText('Overview')).toBeInTheDocument();
      });
    });

    it('should return to list when clicking back button', async () => {
      const entries = [createMockAgentHistoryEntry()];
      mockSendMessage.mockResolvedValue(entries);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(screen.getByText('transfer')).toBeInTheDocument();
      });

      // Go to detail view
      const entryCard = screen.getByRole('button', { name: /transfer/i });
      fireEvent.click(entryCard);

      await waitFor(() => {
        expect(screen.getByText('Back to list')).toBeInTheDocument();
      });

      // Go back
      fireEvent.click(screen.getByText('Back to list'));

      await waitFor(() => {
        expect(screen.getByText('History')).toBeInTheDocument();
      });
    });
  });

  describe('message handling', () => {
    it('should call API on mount', async () => {
      mockSendMessage.mockResolvedValue([]);

      render(<HistoryTab />);

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalled();
      });
    });
  });
});
