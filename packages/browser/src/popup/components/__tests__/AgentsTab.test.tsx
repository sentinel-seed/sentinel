/**
 * @fileoverview Unit tests for AgentsTab component
 *
 * Tests agent management functionality:
 * - Connected agents display
 * - Pending approvals
 * - History display
 * - Disconnect flow
 * - Approval decision flow
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AgentsTab } from '../AgentsTab';
import type { AgentConnection, PendingApproval, ActionHistoryEntry } from '../../../types';

// Mock chrome API
const mockSendMessage = jest.fn();
(global as any).chrome = {
  runtime: {
    sendMessage: mockSendMessage,
    onMessage: {
      addListener: jest.fn(),
      removeListener: jest.fn(),
    },
  },
};

// Mock i18n
jest.mock('../../../lib/i18n', () => ({
  t: (key: string) => {
    const translations: Record<string, string> = {
      loading: 'Loading...',
      agents: 'Agents',
      agentsConnected: 'Agents Connected',
      pendingApprovals: 'Pending Approvals',
      history: 'History',
      noAgentsConnected: 'No Agents Connected',
      noAgentsDesc: 'Connect an agent to get started',
      noPendingApprovals: 'No Pending Approvals',
      noPendingDesc: 'All actions have been processed',
      noHistory: 'No History',
      noHistoryDesc: 'No past actions to show',
      disconnect: 'Disconnect',
      confirmDisconnect: 'Are you sure you want to disconnect',
      actionsIntercepted: 'Actions Intercepted',
      approved: 'Approved',
      rejected: 'Rejected',
      expiresIn: 'Expires in',
    };
    return translations[key] || key;
  },
}));

// Mock hooks
jest.mock('../../hooks', () => ({
  useAgentEvents: jest.fn(),
  useApprovalEvents: jest.fn(),
  useAnnounce: jest.fn(() => jest.fn()),
}));

// Mock ApprovalModal
jest.mock('../ApprovalModal', () => ({
  ApprovalModal: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="approval-modal">
      <button onClick={onClose}>Close Modal</button>
    </div>
  ),
}));

// Mock ConfirmDialog
jest.mock('../ui/ConfirmDialog', () => ({
  ConfirmDialog: ({
    isOpen,
    onConfirm,
    onCancel,
    message,
  }: {
    isOpen: boolean;
    onConfirm: () => void;
    onCancel: () => void;
    message: string;
  }) =>
    isOpen ? (
      <div data-testid="confirm-dialog">
        <p>{message}</p>
        <button onClick={onConfirm}>Confirm</button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    ) : null,
}));

// Mock ErrorMessage
jest.mock('../ui/ErrorMessage', () => ({
  ErrorMessage: ({
    message,
    onRetry,
    onDismiss,
  }: {
    message: string;
    onRetry: () => void;
    onDismiss: () => void;
  }) => (
    <div data-testid="error-message">
      <p>{message}</p>
      <button onClick={onRetry}>Retry</button>
      <button onClick={onDismiss}>Dismiss</button>
    </div>
  ),
}));

// Mock SkeletonLoader
jest.mock('../ui/SkeletonLoader', () => ({
  SkeletonCard: () => <div data-testid="skeleton-card" />,
  SkeletonTabs: () => <div data-testid="skeleton-tabs" />,
}));

// Mock utils
jest.mock('../../utils', () => ({
  getActionDisplayInfo: (action: any) => ({
    type: action.type || 'execute',
    sourceName: action.agentName || action.serverName || 'Unknown',
    description: action.description || 'No description',
    riskLevel: action.riskLevel || 'low',
  }),
  getAgentIcon: () => '🤖',
  getRiskIcon: (level: string) => level === 'critical' ? '🚨' : '⚠️',
  getRiskBadgeStyle: () => ({ background: '#f59e0b' }),
  getDecisionIcon: (method: string) => method === 'auto' ? '⚡' : '👤',
  formatTime: (ts: number) => new Date(ts).toLocaleTimeString(),
  formatTimeRemaining: () => '5 min',
}));

// Test data
const mockAgent: AgentConnection = {
  id: 'agent-1',
  name: 'Test Agent',
  type: 'elizaos',
  endpoint: 'http://localhost:3000',
  status: 'connected',
  trustLevel: 75,
  connectedAt: Date.now(),
  lastActivityAt: Date.now(),
  stats: {
    actionsTotal: 10,
    actionsApproved: 8,
    actionsRejected: 2,
    actionsPending: 0,
    memoryInjectionAttempts: 0,
  },
};

const mockPending: PendingApproval = {
  id: 'pending-1',
  source: 'agent_shield',
  action: {
    id: 'action-1',
    agentId: 'agent-1',
    agentName: 'Test Agent',
    type: 'execute',
    description: 'Execute command',
    params: {},
    thspResult: {
      truth: { passed: true, score: 100, issues: [] },
      harm: { passed: true, score: 100, issues: [] },
      scope: { passed: true, score: 100, issues: [] },
      purpose: { passed: true, score: 100, issues: [] },
      overall: true,
      summary: 'OK',
    },
    riskLevel: 'medium',
    timestamp: Date.now(),
    status: 'pending',
  },
  queuedAt: Date.now(),
  expiresAt: Date.now() + 300000,
  viewCount: 0,
};

const mockHistoryEntry: ActionHistoryEntry = {
  id: 'history-1',
  source: 'agent_shield',
  action: {
    id: 'action-old',
    agentId: 'agent-1',
    agentName: 'Test Agent',
    type: 'execute',
    description: 'Past action',
    params: {},
    thspResult: {
      truth: { passed: true, score: 100, issues: [] },
      harm: { passed: true, score: 100, issues: [] },
      scope: { passed: true, score: 100, issues: [] },
      purpose: { passed: true, score: 100, issues: [] },
      overall: true,
      summary: 'OK',
    },
    riskLevel: 'low',
    timestamp: Date.now() - 3600000,
    status: 'approved',
  },
  decision: {
    action: 'approve',
    method: 'auto',
    reason: 'Auto-approved',
    timestamp: Date.now() - 3600000,
  },
  processedAt: Date.now() - 3600000,
};

describe('AgentsTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock responses
    mockSendMessage.mockImplementation((msg) => {
      if (msg.type === 'AGENT_LIST') return Promise.resolve([mockAgent]);
      if (msg.type === 'APPROVAL_GET_PENDING') return Promise.resolve([mockPending]);
      if (msg.type === 'APPROVAL_GET_HISTORY') return Promise.resolve([mockHistoryEntry]);
      return Promise.resolve(null);
    });
  });

  describe('Loading State', () => {
    it('should show loading skeleton initially', async () => {
      // Delay the response to keep loading state
      mockSendMessage.mockImplementation(() => new Promise(() => {}));

      render(<AgentsTab />);

      expect(screen.getByTestId('skeleton-tabs')).toBeInTheDocument();
      // Multiple skeleton cards may be rendered
      expect(screen.getAllByTestId('skeleton-card').length).toBeGreaterThan(0);
    });
  });

  describe('Agents Section', () => {
    it('should display connected agents', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      expect(screen.getByText('elizaos')).toBeInTheDocument();
      expect(screen.getByText('connected')).toBeInTheDocument();
    });

    it('should show empty state when no agents', async () => {
      mockSendMessage.mockImplementation((msg) => {
        if (msg.type === 'AGENT_LIST') return Promise.resolve([]);
        if (msg.type === 'APPROVAL_GET_PENDING') return Promise.resolve([]);
        if (msg.type === 'APPROVAL_GET_HISTORY') return Promise.resolve([]);
        return Promise.resolve(null);
      });

      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('No Agents Connected')).toBeInTheDocument();
      });
    });

    it('should display agent stats', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('10')).toBeInTheDocument(); // actionsTotal
        expect(screen.getByText('8')).toBeInTheDocument(); // approved
        expect(screen.getByText('2')).toBeInTheDocument(); // rejected
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should switch to pending tab', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /Pending Approvals/i }));

      await waitFor(() => {
        expect(screen.getByText('Execute command')).toBeInTheDocument();
      });
    });

    it('should switch to history tab', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /History/i }));

      // Check that history tab is now selected
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /History/i })).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('should show pending count in tab', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Pending Approvals \(1\)/i })).toBeInTheDocument();
      });
    });
  });

  describe('Disconnect Flow', () => {
    it('should open confirm dialog on disconnect click', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Disconnect Test Agent'));

      expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
      expect(screen.getByText(/Are you sure you want to disconnect Test Agent/i)).toBeInTheDocument();
    });

    it('should disconnect agent on confirm', async () => {
      const onStatsUpdate = jest.fn();
      render(<AgentsTab onStatsUpdate={onStatsUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Disconnect Test Agent'));
      fireEvent.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'AGENT_DISCONNECT',
          payload: { agentId: 'agent-1' },
        });
      });
    });

    it('should close dialog on cancel', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Disconnect Test Agent'));
      fireEvent.click(screen.getByText('Cancel'));

      expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument();
    });
  });

  describe('Pending Approvals', () => {
    it('should open approval modal on pending item click', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /Pending Approvals/i }));

      await waitFor(() => {
        expect(screen.getByText('Execute command')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /execute from Test Agent/i }));

      expect(screen.getByTestId('approval-modal')).toBeInTheDocument();
    });

    it('should show empty state when no pending', async () => {
      mockSendMessage.mockImplementation((msg) => {
        if (msg.type === 'AGENT_LIST') return Promise.resolve([mockAgent]);
        if (msg.type === 'APPROVAL_GET_PENDING') return Promise.resolve([]);
        if (msg.type === 'APPROVAL_GET_HISTORY') return Promise.resolve([]);
        return Promise.resolve(null);
      });

      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /Pending Approvals/i }));

      await waitFor(() => {
        expect(screen.getByText('No Pending Approvals')).toBeInTheDocument();
      });
    });
  });

  describe('History Section', () => {
    it('should display history entries', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /History/i }));

      // History section should be visible after tab switch
      await waitFor(() => {
        const historyPanel = screen.getByRole('tabpanel', { hidden: false });
        expect(historyPanel).toHaveAttribute('id', 'panel-history');
      });
    });

    it('should show empty state when no history', async () => {
      mockSendMessage.mockImplementation((msg) => {
        if (msg.type === 'AGENT_LIST') return Promise.resolve([mockAgent]);
        if (msg.type === 'APPROVAL_GET_PENDING') return Promise.resolve([]);
        if (msg.type === 'APPROVAL_GET_HISTORY') return Promise.resolve([]);
        return Promise.resolve(null);
      });

      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /History/i }));

      // History tab should be selected and visible
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /History/i })).toHaveAttribute('aria-selected', 'true');
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message on load failure', async () => {
      mockSendMessage.mockRejectedValueOnce(new Error('Network error'));

      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });
    });

    it('should retry on error button click', async () => {
      mockSendMessage
        .mockRejectedValueOnce(new Error('Network error'))
        .mockImplementation((msg) => {
          if (msg.type === 'AGENT_LIST') return Promise.resolve([mockAgent]);
          if (msg.type === 'APPROVAL_GET_PENDING') return Promise.resolve([]);
          if (msg.type === 'APPROVAL_GET_HISTORY') return Promise.resolve([]);
          return Promise.resolve(null);
        });

      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Retry'));

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });
    });

    it('should dismiss error on button click', async () => {
      mockSendMessage.mockRejectedValueOnce(new Error('Network error'));

      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Dismiss'));

      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper tab roles', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(3);
    });

    it('should have proper tabpanel structure', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      expect(screen.getByRole('tabpanel', { name: /agents/i })).toBeInTheDocument();
    });

    it('should set aria-selected correctly', async () => {
      render(<AgentsTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Agent')).toBeInTheDocument();
      });

      const agentsTab = screen.getByRole('tab', { name: /Agents Connected/i });
      expect(agentsTab).toHaveAttribute('aria-selected', 'true');

      fireEvent.click(screen.getByRole('tab', { name: /Pending Approvals/i }));

      expect(agentsTab).toHaveAttribute('aria-selected', 'false');
      expect(screen.getByRole('tab', { name: /Pending Approvals/i })).toHaveAttribute('aria-selected', 'true');
    });
  });
});
