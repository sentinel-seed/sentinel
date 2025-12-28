/**
 * @fileoverview Unit tests for Tool Interceptor
 *
 * Tests MCP tool call interception functionality:
 * - Risk calculation
 * - Tool call creation
 * - Interception and approval routing
 * - Batch operations
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  calculateToolRisk,
  createToolCall,
  interceptToolCall,
  interceptBatch,
} from '../tool-interceptor';
import type { MCPServer, MCPTool } from '../../types';

// Mock dependencies
jest.mock('../../lib/thsp', () => ({
  validateTHSP: jest.fn(() => ({
    truth: { passed: true, score: 100, issues: [] },
    harm: { passed: true, score: 100, issues: [] },
    scope: { passed: true, score: 100, issues: [] },
    purpose: { passed: true, score: 100, issues: [] },
    overall: true,
    summary: 'All checks passed',
  })),
}));

jest.mock('../../approval/approval-engine', () => ({
  processAction: jest.fn(() =>
    Promise.resolve({
      decision: {
        action: 'approve',
        method: 'auto',
        reason: 'Auto-approved by rule',
        timestamp: Date.now(),
      },
    })
  ),
}));

jest.mock('../../approval/approval-queue', () => ({
  updateBadge: jest.fn(() => Promise.resolve()),
  showApprovalNotification: jest.fn(() => Promise.resolve()),
}));

jest.mock('../tool-validator', () => ({
  validateTool: jest.fn(() => Promise.resolve({ safe: true })),
}));

// Helper to create mock tool
function createMockTool(name: string, options: Partial<MCPTool> = {}): MCPTool {
  return {
    name,
    description: options.description ?? `Tool: ${name}`,
    inputSchema: options.inputSchema ?? {},
    riskLevel: options.riskLevel ?? 'low',
    requiresApproval: options.requiresApproval ?? true,
  };
}

// Mock server
const mockServer: MCPServer = {
  id: 'server-1',
  name: 'Test Server',
  endpoint: 'http://localhost:3000',
  transport: 'http',
  trustLevel: 50,
  isTrusted: false,
  registeredAt: Date.now(),
  lastActivityAt: Date.now(),
  tools: [
    createMockTool('read_file', { riskLevel: 'medium' }),
    createMockTool('write_file', { riskLevel: 'high' }),
    createMockTool('execute_command', { riskLevel: 'critical' }),
    createMockTool('get_info', { riskLevel: 'low', requiresApproval: false }),
  ],
  stats: {
    toolCallsTotal: 0,
    toolCallsApproved: 0,
    toolCallsRejected: 0,
    toolCallsPending: 0,
  },
};

jest.mock('../server-registry', () => ({
  getMCPServer: jest.fn(() => Promise.resolve(mockServer)),
  recordApprovedCall: jest.fn(() => Promise.resolve(mockServer)),
  recordRejectedCall: jest.fn(() => Promise.resolve(mockServer)),
}));

const mockRegistry = jest.requireMock('../server-registry');
const mockApprovalEngine = jest.requireMock('../../approval/approval-engine');
const mockApprovalQueue = jest.requireMock('../../approval/approval-queue');
const mockToolValidator = jest.requireMock('../tool-validator');

describe('Tool Interceptor', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRegistry.getMCPServer.mockResolvedValue(mockServer);
  });

  describe('calculateToolRisk', () => {
    const createServer = (trustLevel: number, isTrusted = false): MCPServer => ({
      ...mockServer,
      trustLevel,
      isTrusted,
    });

    it('should return low risk for safe tools from trusted server', () => {
      const tool = createMockTool('get_info', { riskLevel: 'low' });
      const server = createServer(90, true);
      const risk = calculateToolRisk(tool, server, {});

      expect(risk).toBe('low');
    });

    it('should return high risk for dangerous tools', () => {
      const tool = createMockTool('execute_shell', { riskLevel: 'high' });
      const server = createServer(50);
      const risk = calculateToolRisk(tool, server, {});

      expect(['high', 'critical']).toContain(risk);
    });

    it('should increase risk for sensitive paths in args', () => {
      const tool = createMockTool('read_file', { riskLevel: 'low' });
      const server = createServer(70);

      const normalRisk = calculateToolRisk(tool, server, { path: '/home/user/file.txt' });
      const sensitiveRisk = calculateToolRisk(tool, server, { path: '/etc/passwd' });

      const riskOrder = ['low', 'medium', 'high', 'critical'];
      // Sensitive path should have equal or higher risk
      expect(riskOrder.indexOf(sensitiveRisk)).toBeGreaterThanOrEqual(riskOrder.indexOf(normalRisk));
    });

    it('should increase risk for URLs in args', () => {
      const tool = createMockTool('fetch_url', { riskLevel: 'low' });
      const server = createServer(70);

      const noUrlRisk = calculateToolRisk(tool, server, { data: 'hello' });
      const urlRisk = calculateToolRisk(tool, server, { url: 'https://evil.com/malware' });

      const riskOrder = ['low', 'medium', 'high', 'critical'];
      expect(riskOrder.indexOf(urlRisk)).toBeGreaterThanOrEqual(riskOrder.indexOf(noUrlRisk));
    });

    it('should increase risk for code execution patterns', () => {
      const tool = createMockTool('run_script', { riskLevel: 'medium' });
      const server = createServer(60);

      const safeRisk = calculateToolRisk(tool, server, { code: 'print(1)' });
      const evalRisk = calculateToolRisk(tool, server, { code: 'eval("os.system()")' });

      const riskOrder = ['low', 'medium', 'high', 'critical'];
      expect(riskOrder.indexOf(evalRisk)).toBeGreaterThan(riskOrder.indexOf(safeRisk));
    });

    it('should reduce risk for trusted servers', () => {
      const tool = createMockTool('read_file', { riskLevel: 'medium' });

      const untrustedServer = createServer(50, false);
      const trustedServer = createServer(50, true);

      const untrustedRisk = calculateToolRisk(tool, untrustedServer, {});
      const trustedRisk = calculateToolRisk(tool, trustedServer, {});

      const riskOrder = ['low', 'medium', 'high', 'critical'];
      expect(riskOrder.indexOf(trustedRisk)).toBeLessThanOrEqual(riskOrder.indexOf(untrustedRisk));
    });

    it('should increase risk for low trust servers', () => {
      const tool = createMockTool('write_file', { riskLevel: 'medium' });

      const lowTrust = createServer(20);
      const highTrust = createServer(90);

      const lowTrustRisk = calculateToolRisk(tool, lowTrust, {});
      const highTrustRisk = calculateToolRisk(tool, highTrust, {});

      const riskOrder = ['low', 'medium', 'high', 'critical'];
      expect(riskOrder.indexOf(lowTrustRisk)).toBeGreaterThanOrEqual(
        riskOrder.indexOf(highTrustRisk)
      );
    });

    it('should detect shell category in tool name', () => {
      const tool = createMockTool('shell_exec', { riskLevel: 'low' });
      const server = createServer(60);

      const risk = calculateToolRisk(tool, server, {});

      expect(['high', 'critical']).toContain(risk);
    });

    it('should detect write category in tool name', () => {
      const tool = createMockTool('write_data', { riskLevel: 'low' });
      const server = createServer(70);

      const risk = calculateToolRisk(tool, server, {});

      expect(['medium', 'high']).toContain(risk);
    });

    it('should detect .ssh path in args', () => {
      const tool = createMockTool('read_file', { riskLevel: 'low' });
      const server = createServer(80, true);

      const risk = calculateToolRisk(tool, server, { path: '/home/user/.ssh/id_rsa' });

      expect(['medium', 'high', 'critical']).toContain(risk);
    });
  });

  describe('createToolCall', () => {
    it('should create a tool call with all required fields', async () => {
      const toolCall = await createToolCall(
        'server-1',
        'read_file',
        { path: '/tmp/test.txt' },
        'claude_desktop'
      );

      expect(toolCall).toMatchObject({
        serverId: 'server-1',
        serverName: 'Test Server',
        tool: 'read_file',
        arguments: { path: '/tmp/test.txt' },
        source: 'claude_desktop',
        status: 'pending',
      });
      expect(toolCall.id).toBeDefined();
      expect(toolCall.timestamp).toBeGreaterThan(0);
      expect(toolCall.thspResult).toBeDefined();
      expect(toolCall.riskLevel).toBeDefined();
    });

    it('should throw error for unknown server', async () => {
      mockRegistry.getMCPServer.mockResolvedValueOnce(undefined);

      await expect(
        createToolCall('unknown', 'read_file', {}, 'claude_desktop')
      ).rejects.toThrow('Server unknown not found');
    });

    it('should throw error for unknown tool', async () => {
      await expect(
        createToolCall('server-1', 'unknown_tool', {}, 'claude_desktop')
      ).rejects.toThrow('Tool unknown_tool not found on server server-1');
    });

    it('should accept different MCP client sources', async () => {
      const sources: Array<'claude_desktop' | 'cursor' | 'custom'> = ['claude_desktop', 'cursor', 'custom'];

      for (const source of sources) {
        const toolCall = await createToolCall('server-1', 'read_file', {}, source);
        expect(toolCall.source).toBe(source);
      }
    });
  });

  describe('interceptToolCall', () => {
    it('should intercept and auto-approve safe tool call', async () => {
      const result = await interceptToolCall(
        'server-1',
        'read_file',
        { path: '/tmp/test.txt' },
        'claude_desktop'
      );

      expect(result.decision).toBe('approved');
      expect(result.toolCall.status).toBe('approved');
      expect(mockRegistry.recordApprovedCall).toHaveBeenCalledWith('server-1');
    });

    it('should immediately reject invalid tool call', async () => {
      mockToolValidator.validateTool.mockResolvedValueOnce({
        safe: false,
        reason: 'Invalid arguments',
      });

      const result = await interceptToolCall(
        'server-1',
        'write_file',
        { content: null },
        'claude_desktop'
      );

      expect(result.decision).toBe('rejected');
      expect(result.reason).toBe('Invalid arguments');
      expect(mockRegistry.recordRejectedCall).toHaveBeenCalledWith('server-1');
    });

    it('should auto-approve trusted server without approval requirement', async () => {
      const trustedServer = {
        ...mockServer,
        isTrusted: true,
      };
      mockRegistry.getMCPServer.mockResolvedValue(trustedServer);

      const result = await interceptToolCall(
        'server-1',
        'get_info',
        {},
        'claude_desktop'
      );

      expect(result.decision).toBe('approved');
      expect(result.reason).toBe('Trusted server, no approval required');
    });

    it('should handle auto-rejection from approval engine', async () => {
      mockApprovalEngine.processAction.mockResolvedValueOnce({
        decision: {
          action: 'reject',
          method: 'auto',
          reason: 'High risk operation',
          timestamp: Date.now(),
        },
      });

      const result = await interceptToolCall(
        'server-1',
        'execute_command',
        { command: 'rm -rf /' },
        'claude_desktop'
      );

      expect(result.decision).toBe('rejected');
      expect(result.reason).toBe('High risk operation');
    });

    it('should handle pending approval', async () => {
      mockApprovalEngine.processAction.mockResolvedValueOnce({
        decision: null,
        pending: {
          id: 'pending-1',
          source: 'mcp_gateway',
          action: {},
          queuedAt: Date.now(),
          expiresAt: Date.now() + 300000,
          viewCount: 0,
        },
      });

      const result = await interceptToolCall(
        'server-1',
        'write_file',
        { path: '/important.txt', content: 'data' },
        'claude_desktop'
      );

      expect(result.decision).toBe('pending');
      expect(result.reason).toBe('Manual approval required');
      expect(mockApprovalQueue.updateBadge).toHaveBeenCalled();
    });

    it('should show notification for pending approval by default', async () => {
      const pending = {
        id: 'pending-1',
        source: 'mcp_gateway',
        action: {},
        queuedAt: Date.now(),
        expiresAt: Date.now() + 300000,
        viewCount: 0,
      };
      mockApprovalEngine.processAction.mockResolvedValueOnce({
        decision: null,
        pending,
      });

      await interceptToolCall('server-1', 'write_file', {}, 'claude_desktop');

      expect(mockApprovalQueue.showApprovalNotification).toHaveBeenCalledWith(
        pending,
        { show: true }
      );
    });

    it('should not show notification when disabled', async () => {
      mockApprovalEngine.processAction.mockResolvedValueOnce({
        decision: null,
        pending: {
          id: 'pending-1',
          source: 'mcp_gateway',
          action: {},
          queuedAt: Date.now(),
          expiresAt: Date.now() + 300000,
          viewCount: 0,
        },
      });

      await interceptToolCall('server-1', 'write_file', {}, 'claude_desktop', {
        showNotification: false,
      });

      expect(mockApprovalQueue.showApprovalNotification).not.toHaveBeenCalled();
    });

    it('should throw error for unknown server', async () => {
      mockRegistry.getMCPServer.mockResolvedValueOnce(undefined);

      await expect(
        interceptToolCall('unknown', 'read_file', {}, 'claude_desktop')
      ).rejects.toThrow('Server unknown not found');
    });

    it('should pass custom timeout to approval engine', async () => {
      await interceptToolCall('server-1', 'read_file', {}, 'claude_desktop', {
        autoRejectTimeoutMs: 60000,
      });

      expect(mockApprovalEngine.processAction).toHaveBeenCalledWith(
        expect.anything(),
        60000
      );
    });
  });

  describe('interceptBatch', () => {
    it('should process multiple tool calls', async () => {
      const calls = [
        { serverId: 'server-1', toolName: 'read_file', args: { path: '/a' }, source: 'claude_desktop' as const },
        { serverId: 'server-1', toolName: 'read_file', args: { path: '/b' }, source: 'claude_desktop' as const },
        { serverId: 'server-1', toolName: 'get_info', args: {}, source: 'cursor' as const },
      ];

      const results = await interceptBatch(calls);

      expect(results).toHaveLength(3);
    });

    it('should update badge once after batch', async () => {
      const calls = [
        { serverId: 'server-1', toolName: 'read_file', args: {}, source: 'claude_desktop' as const },
        { serverId: 'server-1', toolName: 'get_info', args: {}, source: 'claude_desktop' as const },
      ];

      await interceptBatch(calls);

      // Badge should be updated once at end
      expect(mockApprovalQueue.updateBadge).toHaveBeenCalledTimes(1);
    });

    it('should return empty array for empty input', async () => {
      const results = await interceptBatch([]);

      expect(results).toEqual([]);
      expect(mockApprovalQueue.updateBadge).toHaveBeenCalledTimes(1);
    });

    it('should handle mixed approval results', async () => {
      mockApprovalEngine.processAction
        .mockResolvedValueOnce({
          decision: { action: 'approve', method: 'auto', reason: 'OK', timestamp: Date.now() },
        })
        .mockResolvedValueOnce({
          decision: { action: 'reject', method: 'auto', reason: 'Denied', timestamp: Date.now() },
        });

      const calls = [
        { serverId: 'server-1', toolName: 'read_file', args: {}, source: 'claude_desktop' as const },
        { serverId: 'server-1', toolName: 'execute_command', args: {}, source: 'claude_desktop' as const },
      ];

      const results = await interceptBatch(calls);

      expect(results[0].decision).toBe('approved');
      expect(results[1].decision).toBe('rejected');
    });
  });
});
