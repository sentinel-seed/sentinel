/**
 * Hook Types Tests
 *
 * Tests for type guards and factory functions in hooks/types.ts
 */

import { describe, it, expect } from 'vitest';
import {
  isMessageReceivedEvent,
  isBeforeAgentStartEvent,
  isMessageSendingEvent,
  isBeforeToolCallEvent,
  isAgentEndEvent,
  createSessionState,
  createSessionSummary,
  type MessageReceivedEvent,
  type BeforeAgentStartEvent,
  type MessageSendingEvent,
  type BeforeToolCallEvent,
  type AgentEndEvent,
  type SessionState,
} from '../hooks/types';

// =============================================================================
// Type Guard Tests
// =============================================================================

describe('Type Guards', () => {
  describe('isMessageReceivedEvent', () => {
    it('should return true for valid event', () => {
      const event: MessageReceivedEvent = {
        content: 'Hello',
        sessionId: 'session-123',
        timestamp: Date.now(),
      };
      expect(isMessageReceivedEvent(event)).toBe(true);
    });

    it('should return false for missing content', () => {
      expect(isMessageReceivedEvent({
        sessionId: 'session-123',
        timestamp: Date.now(),
      })).toBe(false);
    });

    it('should return false for missing sessionId', () => {
      expect(isMessageReceivedEvent({
        content: 'Hello',
        timestamp: Date.now(),
      })).toBe(false);
    });

    it('should return false for missing timestamp', () => {
      expect(isMessageReceivedEvent({
        content: 'Hello',
        sessionId: 'session-123',
      })).toBe(false);
    });

    it('should return false for wrong types', () => {
      expect(isMessageReceivedEvent({
        content: 123,
        sessionId: 'session-123',
        timestamp: Date.now(),
      })).toBe(false);
    });

    it('should return false for null', () => {
      expect(isMessageReceivedEvent(null)).toBe(false);
    });

    it('should return false for undefined', () => {
      expect(isMessageReceivedEvent(undefined)).toBe(false);
    });

    it('should return false for primitives', () => {
      expect(isMessageReceivedEvent('string')).toBe(false);
      expect(isMessageReceivedEvent(123)).toBe(false);
      expect(isMessageReceivedEvent(true)).toBe(false);
    });
  });

  describe('isBeforeAgentStartEvent', () => {
    it('should return true for valid event with systemPrompt', () => {
      const event: BeforeAgentStartEvent = {
        sessionId: 'session-123',
        systemPrompt: 'You are a helpful assistant',
      };
      expect(isBeforeAgentStartEvent(event)).toBe(true);
    });

    it('should return true for valid event without systemPrompt', () => {
      const event: BeforeAgentStartEvent = {
        sessionId: 'session-123',
      };
      expect(isBeforeAgentStartEvent(event)).toBe(true);
    });

    it('should return false for missing sessionId', () => {
      expect(isBeforeAgentStartEvent({
        systemPrompt: 'You are helpful',
      })).toBe(false);
    });

    it('should return false for wrong systemPrompt type', () => {
      expect(isBeforeAgentStartEvent({
        sessionId: 'session-123',
        systemPrompt: 123,
      })).toBe(false);
    });

    it('should return false for null', () => {
      expect(isBeforeAgentStartEvent(null)).toBe(false);
    });
  });

  describe('isMessageSendingEvent', () => {
    it('should return true for valid event', () => {
      const event: MessageSendingEvent = {
        content: 'Response message',
        sessionId: 'session-123',
      };
      expect(isMessageSendingEvent(event)).toBe(true);
    });

    it('should return false for missing content', () => {
      expect(isMessageSendingEvent({
        sessionId: 'session-123',
      })).toBe(false);
    });

    it('should return false for missing sessionId', () => {
      expect(isMessageSendingEvent({
        content: 'Response',
      })).toBe(false);
    });

    it('should return false for null', () => {
      expect(isMessageSendingEvent(null)).toBe(false);
    });
  });

  describe('isBeforeToolCallEvent', () => {
    it('should return true for valid event', () => {
      const event: BeforeToolCallEvent = {
        toolName: 'read_file',
        params: { path: '/home/user/file.txt' },
        sessionId: 'session-123',
      };
      expect(isBeforeToolCallEvent(event)).toBe(true);
    });

    it('should return true for empty params', () => {
      const event: BeforeToolCallEvent = {
        toolName: 'get_time',
        params: {},
        sessionId: 'session-123',
      };
      expect(isBeforeToolCallEvent(event)).toBe(true);
    });

    it('should return false for missing toolName', () => {
      expect(isBeforeToolCallEvent({
        params: { path: '/file.txt' },
        sessionId: 'session-123',
      })).toBe(false);
    });

    it('should return false for missing params', () => {
      expect(isBeforeToolCallEvent({
        toolName: 'read_file',
        sessionId: 'session-123',
      })).toBe(false);
    });

    it('should return false for null params', () => {
      expect(isBeforeToolCallEvent({
        toolName: 'read_file',
        params: null,
        sessionId: 'session-123',
      })).toBe(false);
    });

    it('should return false for missing sessionId', () => {
      expect(isBeforeToolCallEvent({
        toolName: 'read_file',
        params: {},
      })).toBe(false);
    });

    it('should return false for null', () => {
      expect(isBeforeToolCallEvent(null)).toBe(false);
    });
  });

  describe('isAgentEndEvent', () => {
    it('should return true for successful session', () => {
      const event: AgentEndEvent = {
        sessionId: 'session-123',
        success: true,
      };
      expect(isAgentEndEvent(event)).toBe(true);
    });

    it('should return true for failed session with error', () => {
      const event: AgentEndEvent = {
        sessionId: 'session-123',
        success: false,
        error: new Error('Something went wrong'),
      };
      expect(isAgentEndEvent(event)).toBe(true);
    });

    it('should return true for session with duration', () => {
      const event: AgentEndEvent = {
        sessionId: 'session-123',
        success: true,
        durationMs: 5000,
      };
      expect(isAgentEndEvent(event)).toBe(true);
    });

    it('should return false for missing sessionId', () => {
      expect(isAgentEndEvent({
        success: true,
      })).toBe(false);
    });

    it('should return false for missing success', () => {
      expect(isAgentEndEvent({
        sessionId: 'session-123',
      })).toBe(false);
    });

    it('should return false for wrong success type', () => {
      expect(isAgentEndEvent({
        sessionId: 'session-123',
        success: 'true',
      })).toBe(false);
    });

    it('should return false for null', () => {
      expect(isAgentEndEvent(null)).toBe(false);
    });
  });
});

// =============================================================================
// Factory Function Tests
// =============================================================================

describe('Factory Functions', () => {
  describe('createSessionState', () => {
    it('should create a valid session state', () => {
      const sessionId = 'session-123';
      const state = createSessionState(sessionId);

      expect(state.sessionId).toBe(sessionId);
      expect(state.startedAt).toBeGreaterThan(0);
      expect(state.messageCount).toBe(0);
      expect(state.toolCallCount).toBe(0);
      expect(state.issuesDetected).toBe(0);
      expect(state.actionsBlocked).toBe(0);
      expect(state.alertsTriggered).toBe(0);
      expect(state.maxThreatLevel).toBe(0);
      expect(state.recentThreatLevels).toEqual([]);
    });

    it('should set startedAt to current time', () => {
      const before = Date.now();
      const state = createSessionState('session-123');
      const after = Date.now();

      expect(state.startedAt).toBeGreaterThanOrEqual(before);
      expect(state.startedAt).toBeLessThanOrEqual(after);
    });

    it('should create independent states for different sessions', () => {
      const state1 = createSessionState('session-1');
      const state2 = createSessionState('session-2');

      expect(state1.sessionId).not.toBe(state2.sessionId);
      expect(state1.recentThreatLevels).not.toBe(state2.recentThreatLevels);

      // Mutating one should not affect the other
      state1.messageCount = 5;
      expect(state2.messageCount).toBe(0);
    });
  });

  describe('createSessionSummary', () => {
    it('should create summary from state', () => {
      const state: SessionState = {
        sessionId: 'session-123',
        startedAt: Date.now() - 5000, // 5 seconds ago
        messageCount: 10,
        toolCallCount: 3,
        issuesDetected: 2,
        actionsBlocked: 1,
        alertsTriggered: 1,
        maxThreatLevel: 4,
        recentThreatLevels: [1, 2, 4],
      };

      const summary = createSessionSummary(state, true);

      expect(summary.sessionId).toBe('session-123');
      expect(summary.success).toBe(true);
      expect(summary.durationMs).toBeGreaterThanOrEqual(5000);
      expect(summary.messageCount).toBe(10);
      expect(summary.toolCallCount).toBe(3);
      expect(summary.issuesDetected).toBe(2);
      expect(summary.actionsBlocked).toBe(1);
      expect(summary.alertsTriggered).toBe(1);
      expect(summary.maxThreatLevel).toBe(4);
    });

    it('should respect success parameter', () => {
      const state = createSessionState('session-123');

      const successSummary = createSessionSummary(state, true);
      expect(successSummary.success).toBe(true);

      const failSummary = createSessionSummary(state, false);
      expect(failSummary.success).toBe(false);
    });

    it('should calculate duration correctly', () => {
      const startTime = Date.now() - 1000; // 1 second ago
      const state: SessionState = {
        sessionId: 'session-123',
        startedAt: startTime,
        messageCount: 0,
        toolCallCount: 0,
        issuesDetected: 0,
        actionsBlocked: 0,
        alertsTriggered: 0,
        maxThreatLevel: 0,
        recentThreatLevels: [],
      };

      const summary = createSessionSummary(state, true);

      // Duration should be at least 1000ms
      expect(summary.durationMs).toBeGreaterThanOrEqual(1000);
      // But not more than 2000ms (allowing for test execution time)
      expect(summary.durationMs).toBeLessThan(2000);
    });

    it('should handle zero-duration sessions', () => {
      const state: SessionState = {
        sessionId: 'session-123',
        startedAt: Date.now(),
        messageCount: 0,
        toolCallCount: 0,
        issuesDetected: 0,
        actionsBlocked: 0,
        alertsTriggered: 0,
        maxThreatLevel: 0,
        recentThreatLevels: [],
      };

      const summary = createSessionSummary(state, true);

      // Duration should be very small (0-10ms)
      expect(summary.durationMs).toBeLessThan(10);
    });
  });
});

// =============================================================================
// Type Compatibility Tests
// =============================================================================

describe('Type Compatibility', () => {
  it('should allow readonly access to event properties', () => {
    const event: MessageReceivedEvent = {
      content: 'Hello',
      sessionId: 'session-123',
      timestamp: Date.now(),
    };

    // Should be able to read
    const content: string = event.content;
    const sessionId: string = event.sessionId;
    const timestamp: number = event.timestamp;

    expect(content).toBe('Hello');
    expect(sessionId).toBe('session-123');
    expect(timestamp).toBeGreaterThan(0);
  });

  it('should allow readonly access to result properties', () => {
    // This is a compile-time check - if it compiles, the types are correct
    const result = {
      analyzed: true as const,
      threatLevel: 3,
      isPromptInjection: true,
      isJailbreakAttempt: false,
      issues: [],
      shouldAlert: true,
      durationMs: 25,
    };

    expect(result.analyzed).toBe(true);
    expect(result.threatLevel).toBe(3);
  });

  it('should work with params as Record<string, unknown>', () => {
    const event: BeforeToolCallEvent = {
      toolName: 'complex_tool',
      params: {
        stringParam: 'value',
        numberParam: 123,
        booleanParam: true,
        nestedParam: { key: 'value' },
        arrayParam: [1, 2, 3],
      },
      sessionId: 'session-123',
    };

    expect(isBeforeToolCallEvent(event)).toBe(true);
  });
});
