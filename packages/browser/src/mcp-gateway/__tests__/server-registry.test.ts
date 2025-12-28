/**
 * @fileoverview Unit tests for Server Registry
 *
 * Tests all MCP server management functionality:
 * - Registration and lifecycle
 * - Trust level management
 * - Tool management
 * - Statistics tracking
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  registerServer,
  unregisterServer,
  getMCPServers,
  getTrustedServers,
  getMCPServer,
  getServerByEndpoint,
  getServerByName,
  updateServerTrust,
  setServerTrusted,
  increaseTrust,
  decreaseTrust,
  addServerTool,
  removeServerTool,
  updateToolRisk,
  getServerTool,
  recordApprovedCall,
  recordRejectedCall,
} from '../server-registry';
import type { MCPServer, MCPTool } from '../../types';

// Mock the approval store
jest.mock('../../approval/approval-store', () => {
  const servers = new Map<string, MCPServer>();

  return {
    getMCPServers: jest.fn(() => Promise.resolve(Array.from(servers.values()))),
    getMCPServer: jest.fn((id: string) => Promise.resolve(servers.get(id))),
    saveMCPServer: jest.fn((server: MCPServer) => {
      servers.set(server.id, server);
      return Promise.resolve();
    }),
    deleteMCPServer: jest.fn((id: string) => {
      const existed = servers.has(id);
      servers.delete(id);
      return Promise.resolve(existed);
    }),
    __reset: () => servers.clear(),
  };
});

const mockStore = jest.requireMock('../../approval/approval-store');

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

describe('Server Registry', () => {
  beforeEach(() => {
    mockStore.__reset();
    jest.clearAllMocks();
  });

  describe('registerServer', () => {
    it('should register a new server with default values', async () => {
      const server = await registerServer('Test Server', 'http://localhost:3000', 'http');

      expect(server).toMatchObject({
        name: 'Test Server',
        endpoint: 'http://localhost:3000',
        transport: 'http',
        trustLevel: 30,
        isTrusted: false,
      });
      expect(server.id).toBeDefined();
      expect(server.registeredAt).toBeGreaterThan(0);
    });

    it('should register server with tools', async () => {
      const tools = [
        createMockTool('read_file'),
        createMockTool('write_file'),
      ];
      const server = await registerServer('Test Server', 'http://localhost:3000', 'http', tools);

      expect(server.tools).toHaveLength(2);
      expect(server.tools[0].name).toBe('read_file');
    });

    it('should calculate default risk for high-risk tools', async () => {
      // Pass tool without riskLevel to test default calculation
      const tools = [{ name: 'execute', description: 'Execute', requiresApproval: true }] as MCPTool[];
      const server = await registerServer('Test Server', 'http://localhost:3000', 'http', tools);

      expect(server.tools[0].riskLevel).toBe('high');
    });

    it('should register with custom trust level', async () => {
      const server = await registerServer(
        'Trusted Server',
        'http://localhost:3000',
        'http',
        [],
        { trustLevel: 80, isTrusted: true }
      );

      expect(server.trustLevel).toBe(80);
      expect(server.isTrusted).toBe(true);
    });

    it('should return existing server if endpoint already registered', async () => {
      const server1 = await registerServer('Server 1', 'http://localhost:3000', 'http');
      const server2 = await registerServer('Server 2', 'http://localhost:3000', 'http');

      expect(server2.id).toBe(server1.id);
    });

    it('should support different transport types', async () => {
      const httpServer = await registerServer('HTTP', 'http://localhost:3000', 'http');
      const stdioServer = await registerServer('STDIO', '/path/to/server', 'stdio');
      const wsServer = await registerServer('WS', 'ws://localhost:3001', 'websocket');

      expect(httpServer.transport).toBe('http');
      expect(stdioServer.transport).toBe('stdio');
      expect(wsServer.transport).toBe('websocket');
    });
  });

  describe('unregisterServer', () => {
    it('should remove server', async () => {
      const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
      const result = await unregisterServer(server.id);

      expect(result).toBe(true);

      const removed = await getMCPServer(server.id);
      expect(removed).toBeUndefined();
    });

    it('should return false for non-existent server', async () => {
      const result = await unregisterServer('non-existent-id');
      expect(result).toBe(false);
    });
  });

  describe('getMCPServers', () => {
    it('should return all servers', async () => {
      await registerServer('Server 1', 'http://localhost:3000', 'http');
      await registerServer('Server 2', 'http://localhost:3001', 'http');
      await registerServer('Server 3', 'http://localhost:3002', 'websocket');

      const servers = await getMCPServers();
      expect(servers).toHaveLength(3);
    });

    it('should return empty array when no servers', async () => {
      const servers = await getMCPServers();
      expect(servers).toEqual([]);
    });
  });

  describe('getTrustedServers', () => {
    it('should return only trusted servers', async () => {
      await registerServer('Untrusted', 'http://localhost:3000', 'http');
      await registerServer('Trusted', 'http://localhost:3001', 'http', [], { isTrusted: true });

      const trusted = await getTrustedServers();
      expect(trusted).toHaveLength(1);
      expect(trusted[0].name).toBe('Trusted');
    });
  });

  describe('getServerByEndpoint', () => {
    it('should find server by endpoint', async () => {
      await registerServer('Test Server', 'http://localhost:3000', 'http');

      const found = await getServerByEndpoint('http://localhost:3000');
      expect(found?.name).toBe('Test Server');
    });

    it('should return undefined for unknown endpoint', async () => {
      const found = await getServerByEndpoint('http://unknown:9999');
      expect(found).toBeUndefined();
    });
  });

  describe('getServerByName', () => {
    it('should find server by name (case insensitive)', async () => {
      await registerServer('Test Server', 'http://localhost:3000', 'http');

      const found = await getServerByName('TEST SERVER');
      expect(found?.endpoint).toBe('http://localhost:3000');
    });
  });

  describe('Trust Management', () => {
    describe('updateServerTrust', () => {
      it('should update trust level', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const updated = await updateServerTrust(server.id, 75);

        expect(updated.trustLevel).toBe(75);
      });

      it('should clamp trust level to 0-100', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');

        const tooHigh = await updateServerTrust(server.id, 150);
        expect(tooHigh.trustLevel).toBe(100);

        const tooLow = await updateServerTrust(server.id, -50);
        expect(tooLow.trustLevel).toBe(0);
      });

      it('should throw for non-existent server', async () => {
        await expect(updateServerTrust('non-existent', 50)).rejects.toThrow(
          'Server non-existent not found'
        );
      });
    });

    describe('setServerTrusted', () => {
      it('should mark server as trusted', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const updated = await setServerTrusted(server.id, true);

        expect(updated.isTrusted).toBe(true);
      });

      it('should increase trust level to 70 when marking trusted', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        expect(server.trustLevel).toBe(30);

        const updated = await setServerTrusted(server.id, true);
        expect(updated.trustLevel).toBe(70);
      });

      it('should not decrease trust level when already above 70', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http', [], {
          trustLevel: 90,
        });

        const updated = await setServerTrusted(server.id, true);
        expect(updated.trustLevel).toBe(90);
      });
    });

    describe('increaseTrust', () => {
      it('should increase trust by default amount', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const updated = await increaseTrust(server.id);

        expect(updated.trustLevel).toBe(31);
      });

      it('should increase trust by custom amount', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const updated = await increaseTrust(server.id, 20);

        expect(updated.trustLevel).toBe(50);
      });
    });

    describe('decreaseTrust', () => {
      it('should decrease trust by default amount', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const updated = await decreaseTrust(server.id);

        expect(updated.trustLevel).toBe(25);
      });

      it('should decrease trust by custom amount', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const updated = await decreaseTrust(server.id, 10);

        expect(updated.trustLevel).toBe(20);
      });
    });
  });

  describe('Tool Management', () => {
    describe('addServerTool', () => {
      it('should add tool to server', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const tool = createMockTool('new_tool');
        const updated = await addServerTool(server.id, tool);

        expect(updated.tools).toHaveLength(1);
        expect(updated.tools[0].name).toBe('new_tool');
      });

      it('should not add duplicate tool', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http', [
          createMockTool('existing_tool'),
        ]);
        const tool = createMockTool('existing_tool');
        const updated = await addServerTool(server.id, tool);

        expect(updated.tools).toHaveLength(1);
      });
    });

    describe('removeServerTool', () => {
      it('should remove tool from server', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http', [
          createMockTool('tool1'),
          createMockTool('tool2'),
        ]);
        const updated = await removeServerTool(server.id, 'tool1');

        expect(updated.tools).toHaveLength(1);
        expect(updated.tools[0].name).toBe('tool2');
      });
    });

    describe('updateToolRisk', () => {
      it('should update tool risk level', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http', [
          createMockTool('my_tool', { riskLevel: 'low' }),
        ]);
        const updated = await updateToolRisk(server.id, 'my_tool', 'high');

        expect(updated.tools[0].riskLevel).toBe('high');
      });
    });

    describe('getServerTool', () => {
      it('should return tool by name', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http', [
          createMockTool('tool1'),
          createMockTool('tool2'),
        ]);

        const tool = await getServerTool(server.id, 'tool1');
        expect(tool?.name).toBe('tool1');
      });

      it('should return undefined for unknown tool', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');

        const tool = await getServerTool(server.id, 'unknown');
        expect(tool).toBeUndefined();
      });
    });
  });

  describe('Statistics', () => {
    describe('recordApprovedCall', () => {
      it('should increment approved count and increase trust', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const updated = await recordApprovedCall(server.id);

        expect(updated.stats.toolCallsTotal).toBe(1);
        expect(updated.stats.toolCallsApproved).toBe(1);
        expect(updated.trustLevel).toBe(31);
      });
    });

    describe('recordRejectedCall', () => {
      it('should increment rejected count and decrease trust', async () => {
        const server = await registerServer('Test Server', 'http://localhost:3000', 'http');
        const updated = await recordRejectedCall(server.id);

        expect(updated.stats.toolCallsTotal).toBe(1);
        expect(updated.stats.toolCallsRejected).toBe(1);
        expect(updated.trustLevel).toBe(25);
      });
    });
  });

  describe('Tool Risk Calculation', () => {
    it('should assign high risk to dangerous tools', async () => {
      // Use tools without pre-set riskLevel to test default calculation
      const tools = [
        { name: 'execute', description: 'Execute command', requiresApproval: true },
        { name: 'shell_command', description: 'Shell command', requiresApproval: true },
        { name: 'run_bash', description: 'Run bash', requiresApproval: true },
      ] as MCPTool[];
      const server = await registerServer('Test', 'http://localhost:3000', 'http', tools);

      expect(server.tools.every((t) => t.riskLevel === 'high')).toBe(true);
    });

    it('should assign medium risk to file operations', async () => {
      const tools = [
        { name: 'read_config', description: 'Read config file', requiresApproval: true },
      ] as MCPTool[];
      const server = await registerServer('Test', 'http://localhost:3000', 'http', tools);

      // 'read' in name -> medium
      expect(server.tools[0].riskLevel).toBe('medium');
    });

    it('should assign low risk to safe tools', async () => {
      const tools = [
        { name: 'get_time', description: 'Get time', requiresApproval: true },
      ] as MCPTool[];
      const server = await registerServer('Test', 'http://localhost:3000', 'http', tools);

      expect(server.tools[0].riskLevel).toBe('low');
    });
  });
});
