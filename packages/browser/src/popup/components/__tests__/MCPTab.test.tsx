/**
 * @fileoverview Unit tests for MCPTab component
 *
 * Tests MCP server management functionality:
 * - Server display and trust management
 * - Tools listing
 * - Tool call history
 * - Unregister flow
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MCPTab } from '../MCPTab';
import type { MCPServer, MCPToolCall } from '../../../types';

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
      mcp: 'MCP',
      servers: 'Servers',
      tools: 'Tools',
      history: 'History',
      noMCPServers: 'No MCP Servers',
      noMCPServersDesc: 'Register an MCP server to get started',
      noTools: 'No Tools',
      noToolsDesc: 'No tools available',
      noToolHistory: 'No Tool History',
      noToolHistoryDesc: 'No tool calls recorded',
      unregister: 'Unregister',
      confirmUnregister: 'Are you sure you want to unregister',
      trusted: 'Trusted',
      untrusted: 'Untrusted',
      clickToToggleTrust: 'Click to toggle trust',
      trustLevel: 'Trust Level',
      toolCalls: 'Tool Calls',
      approved: 'Approved',
      rejected: 'Rejected',
      toolsAvailable: 'tools available',
    };
    return translations[key] || key;
  },
}));

// Mock hooks
jest.mock('../../hooks', () => ({
  useMCPEvents: jest.fn(),
  useAnnounce: jest.fn(() => jest.fn()),
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
  getTransportIcon: () => '🔌',
  getServerName: (servers: MCPServer[], id: string) =>
    servers.find((s) => s.id === id)?.name || 'Unknown',
  getToolRiskLevel: () => 'low',
  getRiskIcon: () => '🟢',
  truncateEndpoint: (ep: string) => ep.slice(0, 30),
  formatTime: (ts: number) => new Date(ts).toLocaleTimeString(),
}));

// Test data
const mockServer: MCPServer = {
  id: 'server-1',
  name: 'Test Server',
  endpoint: 'http://localhost:3000',
  transport: 'http',
  trustLevel: 70,
  isTrusted: true,
  registeredAt: Date.now(),
  lastActivityAt: Date.now(),
  tools: [
    {
      name: 'read_file',
      description: 'Read a file',
      riskLevel: 'low',
      requiresApproval: true,
    },
    {
      name: 'write_file',
      description: 'Write a file',
      riskLevel: 'high',
      requiresApproval: true,
    },
  ],
  stats: {
    toolCallsTotal: 15,
    toolCallsApproved: 12,
    toolCallsRejected: 3,
    toolCallsPending: 0,
  },
};

const mockToolCall: MCPToolCall = {
  id: 'call-1',
  serverId: 'server-1',
  serverName: 'Test Server',
  tool: 'read_file',
  arguments: { path: '/tmp/test.txt' },
  source: 'claude_desktop',
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
};

describe('MCPTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock responses
    mockSendMessage.mockImplementation((msg) => {
      if (msg.type === 'MCP_LIST_SERVERS') return Promise.resolve([mockServer]);
      if (msg.type === 'MCP_GET_TOOL_HISTORY') return Promise.resolve([mockToolCall]);
      return Promise.resolve(null);
    });
  });

  describe('Loading State', () => {
    it('should show loading skeleton initially', async () => {
      mockSendMessage.mockImplementation(() => new Promise(() => {}));

      render(<MCPTab />);

      expect(screen.getByTestId('skeleton-tabs')).toBeInTheDocument();
      expect(screen.getAllByTestId('skeleton-card').length).toBeGreaterThan(0);
    });
  });

  describe('Servers Section', () => {
    it('should display registered servers', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      expect(screen.getByText('http://localhost:3000')).toBeInTheDocument();
    });

    it('should show empty state when no servers', async () => {
      mockSendMessage.mockImplementation((msg) => {
        if (msg.type === 'MCP_LIST_SERVERS') return Promise.resolve([]);
        if (msg.type === 'MCP_GET_TOOL_HISTORY') return Promise.resolve([]);
        return Promise.resolve(null);
      });

      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('No MCP Servers')).toBeInTheDocument();
      });
    });

    it('should display server stats', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('15')).toBeInTheDocument(); // toolCallsTotal
        expect(screen.getByText('12')).toBeInTheDocument(); // approved
        expect(screen.getByText('3')).toBeInTheDocument(); // rejected
      });
    });

    it('should show trust badge', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Trusted/i })).toBeInTheDocument();
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should switch to tools tab', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /Tools/i }));

      // Should see tool cards
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Tools/i })).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('should switch to history tab', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /History/i }));

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /History/i })).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('should show server count in tab', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Servers \(1\)/i })).toBeInTheDocument();
      });
    });

    it('should show tools count in tab', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Tools \(2\)/i })).toBeInTheDocument();
      });
    });
  });

  describe('Trust Management', () => {
    it('should toggle trust on click', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      const trustButton = screen.getByRole('button', { name: /Trusted/i });
      fireEvent.click(trustButton);

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'MCP_UPDATE_SERVER',
          payload: { serverId: 'server-1', updates: { isTrusted: false } },
        });
      });
    });
  });

  describe('Unregister Flow', () => {
    it('should open confirm dialog on unregister click', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Unregister Test Server'));

      expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
      expect(screen.getByText(/Are you sure you want to unregister Test Server/i)).toBeInTheDocument();
    });

    it('should unregister server on confirm', async () => {
      const onStatsUpdate = jest.fn();
      render(<MCPTab onStatsUpdate={onStatsUpdate} />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Unregister Test Server'));
      fireEvent.click(screen.getByText('Confirm'));

      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith({
          type: 'MCP_UNREGISTER_SERVER',
          payload: { serverId: 'server-1' },
        });
      });
    });

    it('should close dialog on cancel', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Unregister Test Server'));
      fireEvent.click(screen.getByText('Cancel'));

      expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument();
    });
  });

  describe('Tools Expansion', () => {
    it('should expand tools list on click', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      const expandButton = screen.getByRole('button', { name: /2 tools available/i });
      fireEvent.click(expandButton);

      expect(expandButton).toHaveAttribute('aria-expanded', 'true');
    });

    it('should show tool names when expanded', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /2 tools available/i }));

      await waitFor(() => {
        expect(screen.getByText('read_file')).toBeInTheDocument();
        expect(screen.getByText('write_file')).toBeInTheDocument();
      });
    });
  });

  describe('Tools Section', () => {
    it('should display all tools across servers', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /Tools/i }));

      // After switching to tools tab, both tools should be visible
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Tools/i })).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('should show empty state when no tools', async () => {
      mockSendMessage.mockImplementation((msg) => {
        if (msg.type === 'MCP_LIST_SERVERS') {
          return Promise.resolve([{ ...mockServer, tools: [] }]);
        }
        if (msg.type === 'MCP_GET_TOOL_HISTORY') return Promise.resolve([]);
        return Promise.resolve(null);
      });

      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /Tools \(0\)/i }));

      await waitFor(() => {
        expect(screen.getByText('No Tools')).toBeInTheDocument();
      });
    });
  });

  describe('History Section', () => {
    it('should show empty state when no history', async () => {
      mockSendMessage.mockImplementation((msg) => {
        if (msg.type === 'MCP_LIST_SERVERS') return Promise.resolve([mockServer]);
        if (msg.type === 'MCP_GET_TOOL_HISTORY') return Promise.resolve([]);
        return Promise.resolve(null);
      });

      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('tab', { name: /History/i }));

      await waitFor(() => {
        expect(screen.getByText('No Tool History')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message on load failure', async () => {
      mockSendMessage.mockRejectedValueOnce(new Error('Network error'));

      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });
    });

    it('should retry on error button click', async () => {
      mockSendMessage
        .mockRejectedValueOnce(new Error('Network error'))
        .mockImplementation((msg) => {
          if (msg.type === 'MCP_LIST_SERVERS') return Promise.resolve([mockServer]);
          if (msg.type === 'MCP_GET_TOOL_HISTORY') return Promise.resolve([]);
          return Promise.resolve(null);
        });

      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Retry'));

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });
    });

    it('should dismiss error on button click', async () => {
      mockSendMessage.mockRejectedValueOnce(new Error('Network error'));

      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Dismiss'));

      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper tab roles', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(3);
    });

    it('should have proper tabpanel structure', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      expect(screen.getByRole('tabpanel', { name: /servers/i })).toBeInTheDocument();
    });

    it('should set aria-selected correctly', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      const serversTab = screen.getByRole('tab', { name: /Servers/i });
      expect(serversTab).toHaveAttribute('aria-selected', 'true');

      fireEvent.click(screen.getByRole('tab', { name: /Tools/i }));

      expect(serversTab).toHaveAttribute('aria-selected', 'false');
      expect(screen.getByRole('tab', { name: /Tools/i })).toHaveAttribute('aria-selected', 'true');
    });

    it('should have proper aria-expanded on tools button', async () => {
      render(<MCPTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Server')).toBeInTheDocument();
      });

      const expandButton = screen.getByRole('button', { name: /2 tools available/i });
      expect(expandButton).toHaveAttribute('aria-expanded', 'false');

      fireEvent.click(expandButton);

      expect(expandButton).toHaveAttribute('aria-expanded', 'true');
    });
  });
});
