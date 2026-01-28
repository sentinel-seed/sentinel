/**
 * CLI Module Tests
 *
 * Tests for:
 * - CLI Formatters
 * - CLI Commands
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  // Formatters
  formatLevel,
  formatLevelFull,
  formatLevelList,
  formatStatus,
  formatBlockMessage,
  formatEscapeHint,
  formatAlertNotification,
  formatHelp,
  formatHeader,
  formatSuccess,
  formatError,
  formatInfo,
  formatWarning,
  // Commands
  registerCommand,
  getCommand,
  getAllCommands,
  executeCommand,
  type CommandContext,
} from '../cli';
import { EscapeManager } from '../escapes';
import { AuditLog } from '../logging/audit';
import { stripColors } from '../logging/formatters';

// =============================================================================
// Formatter Tests
// =============================================================================

describe('CLI Formatters', () => {
  describe('formatLevel', () => {
    it('should format level with color', () => {
      const result = formatLevel('guard');

      expect(result).toContain('🛡');
      expect(result).toContain('GUARD');
    });

    it('should format level without color', () => {
      const result = formatLevel('guard', false);

      expect(result).toBe('🛡 GUARD');
    });
  });

  describe('formatLevelFull', () => {
    it('should include description', () => {
      const result = formatLevelFull('guard', false);

      expect(result).toContain('GUARD');
      expect(result).toContain('Block critical threats');
    });
  });

  describe('formatLevelList', () => {
    it('should list all levels', () => {
      const result = formatLevelList(undefined, false);

      expect(result).toContain('OFF');
      expect(result).toContain('WATCH');
      expect(result).toContain('GUARD');
      expect(result).toContain('SHIELD');
    });

    it('should highlight current level', () => {
      const result = formatLevelList('guard', false);

      // Current level should have > marker
      expect(result).toMatch(/> .+GUARD/);
    });
  });

  describe('formatStatus', () => {
    it('should format basic status', () => {
      const result = formatStatus(
        { level: 'guard', active: true },
        false
      );

      expect(result).toContain('Sentinel Status');
      expect(result).toContain('Level');
      expect(result).toContain('GUARD');
      expect(result).toContain('Active');
    });

    it('should show paused state', () => {
      const result = formatStatus(
        { level: 'guard', active: true, paused: true, pauseReason: 'Testing' },
        false
      );

      expect(result).toContain('PAUSED');
      expect(result).toContain('Testing');
    });

    it('should show statistics', () => {
      const result = formatStatus(
        {
          level: 'guard',
          active: true,
          activeSessions: 5,
          messagesProcessed: 100,
          actionsBlocked: 3,
        },
        false
      );

      expect(result).toContain('Sessions: 5');
      expect(result).toContain('Messages: 100');
      expect(result).toContain('Blocked: 3');
    });
  });

  describe('formatBlockMessage', () => {
    it('should format output block', () => {
      const result = formatBlockMessage('output', 'API key detected', false);

      expect(result).toContain('Message Blocked');
      expect(result).toContain('API key detected');
      expect(result).toContain('allow-once');
    });

    it('should format tool block', () => {
      const result = formatBlockMessage('tool', 'Dangerous command', false);

      expect(result).toContain('Tool Call Blocked');
      expect(result).toContain('Dangerous command');
    });
  });

  describe('formatEscapeHint', () => {
    it('should show allow-once hint', () => {
      const result = formatEscapeHint(false);

      expect(result).toContain('allow-once');
    });
  });

  describe('formatAlertNotification', () => {
    it('should format alert', () => {
      const result = formatAlertNotification(
        'action_blocked',
        'Tool blocked',
        'high',
        false
      );

      expect(result).toContain('ALERT');
      expect(result).toContain('ACTION BLOCKED');
      expect(result).toContain('HIGH');
      expect(result).toContain('Tool blocked');
    });
  });

  describe('formatHelp', () => {
    it('should format command list', () => {
      const commands = [
        { name: 'status', description: 'Show status' },
        { name: 'level', description: 'Change level', usage: '/sentinel level [name]' },
      ];

      const result = formatHelp(commands, false);

      expect(result).toContain('Sentinel Commands');
      expect(result).toContain('status');
      expect(result).toContain('Show status');
      expect(result).toContain('level');
      expect(result).toContain('Usage:');
    });

    it('should show examples', () => {
      const commands = [
        {
          name: 'test',
          description: 'Test command',
          examples: ['/sentinel test 1', '/sentinel test 2'],
        },
      ];

      const result = formatHelp(commands, false);

      expect(result).toContain('Examples:');
      expect(result).toContain('/sentinel test 1');
      expect(result).toContain('/sentinel test 2');
    });
  });

  describe('formatHeader', () => {
    it('should create box header', () => {
      const result = formatHeader('Test', false);

      expect(result).toContain('╭');
      expect(result).toContain('╮');
      expect(result).toContain('╰');
      expect(result).toContain('╯');
      expect(result).toContain('Test');
    });
  });

  describe('Message formatters', () => {
    it('formatSuccess should show checkmark', () => {
      const result = formatSuccess('Done', false);
      expect(result).toBe('✓ Done');
    });

    it('formatError should show X', () => {
      const result = formatError('Failed', false);
      expect(result).toBe('✗ Failed');
    });

    it('formatInfo should show info icon', () => {
      const result = formatInfo('Note', false);
      expect(result).toBe('ℹ Note');
    });

    it('formatWarning should show warning icon', () => {
      const result = formatWarning('Careful', false);
      expect(result).toBe('⚠ Careful');
    });
  });
});

// =============================================================================
// Command Tests
// =============================================================================

describe('CLI Commands', () => {
  let escapes: EscapeManager;
  let audit: AuditLog;
  let context: CommandContext;

  beforeEach(() => {
    vi.useFakeTimers();
    escapes = new EscapeManager();
    audit = new AuditLog({ entryTtlMs: 0 });

    context = {
      sessionId: 'test-session',
      currentLevel: 'guard',
      escapes,
      audit,
      useColor: false,
    };
  });

  afterEach(() => {
    escapes.destroy();
    audit.destroy();
    vi.useRealTimers();
  });

  describe('Command Registry', () => {
    it('should have built-in commands', () => {
      expect(getCommand('status')).toBeDefined();
      expect(getCommand('level')).toBeDefined();
      expect(getCommand('allow-once')).toBeDefined();
      expect(getCommand('pause')).toBeDefined();
      expect(getCommand('resume')).toBeDefined();
      expect(getCommand('trust')).toBeDefined();
      expect(getCommand('untrust')).toBeDefined();
      expect(getCommand('log')).toBeDefined();
      expect(getCommand('help')).toBeDefined();
    });

    it('should support aliases', () => {
      expect(getCommand('s')).toBe(getCommand('status'));
      expect(getCommand('l')).toBe(getCommand('level'));
      expect(getCommand('ao')).toBe(getCommand('allow-once'));
      expect(getCommand('p')).toBe(getCommand('pause'));
      expect(getCommand('r')).toBe(getCommand('resume'));
      expect(getCommand('t')).toBe(getCommand('trust'));
      expect(getCommand('h')).toBe(getCommand('help'));
    });

    it('should get all unique commands', () => {
      const commands = getAllCommands();

      // Should be unique (no duplicates from aliases)
      const names = commands.map(c => c.name);
      expect(new Set(names).size).toBe(names.length);

      // Should have minimum expected commands
      expect(commands.length).toBeGreaterThanOrEqual(9);
    });

    it('should register custom commands', () => {
      registerCommand({
        name: 'custom-test',
        description: 'Test command',
        handler: () => ({ success: true, message: 'Custom!' }),
      });

      expect(getCommand('custom-test')).toBeDefined();
    });
  });

  describe('executeCommand', () => {
    it('should execute valid commands', async () => {
      const result = await executeCommand('status', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('Status');
    });

    it('should handle unknown commands', async () => {
      const result = await executeCommand('unknown-cmd', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('Unknown command');
    });

    it('should parse arguments', async () => {
      const result = await executeCommand('level watch', context);

      expect(result.success).toBe(true);
    });
  });

  describe('status command', () => {
    it('should show current status', async () => {
      const result = await executeCommand('status', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('GUARD');
      expect(result.message).toContain('Active');
    });

    it('should show paused status', async () => {
      escapes.pauseProtection('test-session');

      const result = await executeCommand('status', context);

      expect(result.message).toContain('PAUSED');
    });
  });

  describe('level command', () => {
    it('should show levels when no arg', async () => {
      const result = await executeCommand('level', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('Protection Levels');
      expect(result.message).toContain('OFF');
      expect(result.message).toContain('WATCH');
      expect(result.message).toContain('GUARD');
      expect(result.message).toContain('SHIELD');
    });

    it('should change level', async () => {
      let newLevel: string | undefined;
      context.onLevelChange = (level) => { newLevel = level; };

      const result = await executeCommand('level shield', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('changed');
      expect(newLevel).toBe('shield');
    });

    it('should reject invalid level', async () => {
      const result = await executeCommand('level invalid', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('Invalid level');
    });

    it('should handle same level', async () => {
      const result = await executeCommand('level guard', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('already set');
    });
  });

  describe('allow-once command', () => {
    it('should grant allow-once token', async () => {
      const result = await executeCommand('allow-once', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('Allow-once granted');
    });

    it('should accept scope argument', async () => {
      const result = await executeCommand('allow-once tool', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('scope: tool');
    });

    it('should reject invalid scope', async () => {
      const result = await executeCommand('allow-once invalid', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('Invalid scope');
    });

    it('should fail without escape manager', async () => {
      context.escapes = undefined;

      const result = await executeCommand('allow-once', context);

      expect(result.success).toBe(false);
    });
  });

  describe('pause command', () => {
    it('should pause protection', async () => {
      const result = await executeCommand('pause', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('paused');
      expect(escapes.pause.isPaused('test-session')).toBe(true);
    });

    it('should accept duration', async () => {
      const result = await executeCommand('pause 10m', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('10 minutes');
    });

    it('should reject invalid duration', async () => {
      const result = await executeCommand('pause xyz', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('Invalid duration');
    });

    it('should handle already paused', async () => {
      escapes.pauseProtection('test-session');

      const result = await executeCommand('pause', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('Already paused');
    });
  });

  describe('resume command', () => {
    it('should resume protection', async () => {
      escapes.pauseProtection('test-session');

      const result = await executeCommand('resume', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('resumed');
      expect(escapes.pause.isPaused('test-session')).toBe(false);
    });

    it('should handle not paused', async () => {
      const result = await executeCommand('resume', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('Not currently paused');
    });
  });

  describe('trust command', () => {
    it('should show trusted tools when no arg', async () => {
      const result = await executeCommand('trust', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('No tools currently trusted');
    });

    it('should trust a tool', async () => {
      const result = await executeCommand('trust bash', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain("'bash' trusted");
    });

    it('should list trusted tools', async () => {
      escapes.trustTool('test-session', 'bash');
      escapes.trustTool('test-session', 'git');

      const result = await executeCommand('trust', context);

      expect(result.message).toContain('bash');
      expect(result.message).toContain('git');
    });

    it('should handle already trusted', async () => {
      escapes.trustTool('test-session', 'bash');

      const result = await executeCommand('trust bash', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('already trusted');
    });
  });

  describe('untrust command', () => {
    it('should untrust a tool', async () => {
      escapes.trustTool('test-session', 'bash');

      const result = await executeCommand('untrust bash', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('Trust revoked');
    });

    it('should require tool name', async () => {
      const result = await executeCommand('untrust', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('specify a tool');
    });

    it('should handle not trusted', async () => {
      const result = await executeCommand('untrust unknown', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('was not trusted');
    });
  });

  describe('log command', () => {
    it('should show empty log message', async () => {
      const result = await executeCommand('log', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('No audit entries');
    });

    it('should show audit entries', async () => {
      audit.log({ event: 'input_analyzed', outcome: 'allowed', sessionId: 'test' });
      audit.log({ event: 'output_blocked', outcome: 'blocked', sessionId: 'test' });

      const result = await executeCommand('log', context);

      expect(result.message).toContain('Audit Entries');
      expect(result.message).toContain('input analyzed');
      expect(result.message).toContain('output blocked');
    });

    it('should accept count argument', async () => {
      for (let i = 0; i < 10; i++) {
        audit.log({ event: 'input_analyzed', outcome: 'allowed' });
      }

      const result = await executeCommand('log 5', context);

      expect(result.message).toContain('Last 5');
    });

    it('should reject invalid count', async () => {
      const result = await executeCommand('log abc', context);

      expect(result.success).toBe(false);
      expect(result.message).toContain('Invalid count');
    });
  });

  describe('help command', () => {
    it('should list all commands', async () => {
      const result = await executeCommand('help', context);

      expect(result.success).toBe(true);
      expect(result.message).toContain('Sentinel Commands');
      expect(result.message).toContain('status');
      expect(result.message).toContain('level');
      expect(result.message).toContain('allow-once');
      expect(result.message).toContain('pause');
      expect(result.message).toContain('resume');
      expect(result.message).toContain('trust');
      expect(result.message).toContain('log');
      expect(result.message).toContain('help');
    });
  });
});
