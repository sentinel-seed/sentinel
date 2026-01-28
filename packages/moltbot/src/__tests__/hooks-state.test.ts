/**
 * Session State Management Tests
 *
 * Tests for state management, anomaly detection, and session tracking.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  createSessionState,
  createSessionSummary,
  recordMessageReceived,
  recordToolCall,
  recordOutputValidation,
  recordAlert,
  detectAnomalies,
  SessionStateManager,
  getSessionDuration,
  isSessionActive,
  getSessionRiskLevel,
  DEFAULT_ANOMALY_CONFIG,
  type SessionState,
  type AnomalyDetectionConfig,
} from '../hooks/state';

// =============================================================================
// State Creation Tests
// =============================================================================

describe('State Creation', () => {
  describe('createSessionState', () => {
    it('should create state with correct sessionId', () => {
      const state = createSessionState('session-123');
      expect(state.sessionId).toBe('session-123');
    });

    it('should initialize all counters to zero', () => {
      const state = createSessionState('test');
      expect(state.messageCount).toBe(0);
      expect(state.toolCallCount).toBe(0);
      expect(state.issuesDetected).toBe(0);
      expect(state.actionsBlocked).toBe(0);
      expect(state.alertsTriggered).toBe(0);
      expect(state.maxThreatLevel).toBe(0);
    });

    it('should initialize empty threat levels array', () => {
      const state = createSessionState('test');
      expect(state.recentThreatLevels).toEqual([]);
    });

    it('should set startedAt to current time', () => {
      const before = Date.now();
      const state = createSessionState('test');
      const after = Date.now();

      expect(state.startedAt).toBeGreaterThanOrEqual(before);
      expect(state.startedAt).toBeLessThanOrEqual(after);
    });
  });

  describe('createSessionSummary', () => {
    it('should create summary from state', () => {
      const state = createSessionState('session-123');
      state.messageCount = 10;
      state.toolCallCount = 5;
      state.issuesDetected = 3;
      state.actionsBlocked = 2;
      state.alertsTriggered = 1;
      state.maxThreatLevel = 4;

      const summary = createSessionSummary(state, true);

      expect(summary.sessionId).toBe('session-123');
      expect(summary.success).toBe(true);
      expect(summary.messageCount).toBe(10);
      expect(summary.toolCallCount).toBe(5);
      expect(summary.issuesDetected).toBe(3);
      expect(summary.actionsBlocked).toBe(2);
      expect(summary.alertsTriggered).toBe(1);
      expect(summary.maxThreatLevel).toBe(4);
    });

    it('should calculate duration', () => {
      const state = createSessionState('test');
      // Simulate 100ms elapsed
      state.startedAt = Date.now() - 100;

      const summary = createSessionSummary(state, true);

      expect(summary.durationMs).toBeGreaterThanOrEqual(100);
      expect(summary.durationMs).toBeLessThan(200);
    });
  });
});

// =============================================================================
// State Update Tests
// =============================================================================

describe('State Updates', () => {
  let state: SessionState;

  beforeEach(() => {
    state = createSessionState('test');
  });

  describe('recordMessageReceived', () => {
    it('should increment message count', () => {
      recordMessageReceived(state, 0);
      expect(state.messageCount).toBe(1);

      recordMessageReceived(state, 0);
      expect(state.messageCount).toBe(2);
    });

    it('should update max threat level', () => {
      recordMessageReceived(state, 2);
      expect(state.maxThreatLevel).toBe(2);

      recordMessageReceived(state, 5);
      expect(state.maxThreatLevel).toBe(5);

      recordMessageReceived(state, 3);
      expect(state.maxThreatLevel).toBe(5); // Should not decrease
    });

    it('should track recent threat levels', () => {
      recordMessageReceived(state, 1);
      recordMessageReceived(state, 3);
      recordMessageReceived(state, 2);

      expect(state.recentThreatLevels).toEqual([1, 3, 2]);
    });

    it('should bound threat levels array size', () => {
      // Add many messages
      for (let i = 0; i < 20; i++) {
        recordMessageReceived(state, i % 5);
      }

      // Should not exceed 2x window size
      expect(state.recentThreatLevels.length).toBeLessThanOrEqual(
        DEFAULT_ANOMALY_CONFIG.recentThreatWindowSize * 2
      );
    });
  });

  describe('recordToolCall', () => {
    it('should increment tool call count', () => {
      recordToolCall(state, false, 0);
      expect(state.toolCallCount).toBe(1);
    });

    it('should add issues detected', () => {
      recordToolCall(state, false, 3);
      expect(state.issuesDetected).toBe(3);

      recordToolCall(state, false, 2);
      expect(state.issuesDetected).toBe(5);
    });

    it('should increment actions blocked when blocked', () => {
      recordToolCall(state, true, 1);
      expect(state.actionsBlocked).toBe(1);

      recordToolCall(state, false, 0);
      expect(state.actionsBlocked).toBe(1);

      recordToolCall(state, true, 2);
      expect(state.actionsBlocked).toBe(2);
    });
  });

  describe('recordOutputValidation', () => {
    it('should add issues detected', () => {
      recordOutputValidation(state, false, 2);
      expect(state.issuesDetected).toBe(2);
    });

    it('should increment actions blocked when blocked', () => {
      recordOutputValidation(state, true, 1);
      expect(state.actionsBlocked).toBe(1);
    });
  });

  describe('recordAlert', () => {
    it('should increment alerts triggered', () => {
      recordAlert(state);
      expect(state.alertsTriggered).toBe(1);

      recordAlert(state);
      expect(state.alertsTriggered).toBe(2);
    });
  });
});

// =============================================================================
// Anomaly Detection Tests
// =============================================================================

describe('Anomaly Detection', () => {
  describe('detectAnomalies', () => {
    it('should return no anomaly with insufficient data', () => {
      const state = createSessionState('test');
      state.messageCount = 2;

      const result = detectAnomalies(state);

      expect(result.detected).toBe(false);
      expect(result.confidence).toBe(0);
    });

    it('should detect high threat rate', () => {
      const state = createSessionState('test');

      // Add high-threat messages
      for (let i = 0; i < 10; i++) {
        recordMessageReceived(state, 4); // All high threat
      }

      const result = detectAnomalies(state);

      expect(result.detected).toBe(true);
      expect(result.type).toBe('high_threat_rate');
      expect(result.confidence).toBeGreaterThan(0);
      expect(result.description).toContain('High threat rate');
    });

    it('should detect high block rate', () => {
      const state = createSessionState('test');
      state.messageCount = 10;
      state.toolCallCount = 10;
      state.actionsBlocked = 15; // 75% blocked

      // Add threat levels to pass minimum check
      for (let i = 0; i < 5; i++) {
        state.recentThreatLevels.push(1); // Low threat
      }

      const result = detectAnomalies(state);

      expect(result.detected).toBe(true);
      expect(result.type).toBe('high_block_rate');
    });

    it('should detect escalation pattern', () => {
      const state = createSessionState('test');
      state.messageCount = 10;

      // Start with low threats, escalate to moderate (not high enough to trigger high_threat_rate)
      // Use custom config to avoid triggering high_threat_rate first
      const config: AnomalyDetectionConfig = {
        ...DEFAULT_ANOMALY_CONFIG,
        highThreatRateThreshold: 0.9, // Very high threshold so it doesn't trigger
        escalationThreshold: 1.5, // Lower threshold for this test
      };

      state.recentThreatLevels = [0, 0, 1, 1, 1, 2, 3, 3, 3, 3];

      const result = detectAnomalies(state, config);

      expect(result.detected).toBe(true);
      expect(result.type).toBe('escalation_pattern');
    });

    it('should detect repeated attacks', () => {
      const state = createSessionState('test');
      state.messageCount = 10;

      // Consecutive high-threat messages (but not enough to trigger high_threat_rate)
      // high_threat_rate triggers at 30% of recent threats being >= 4
      // With 10 messages, we need < 3 high threats to avoid high_threat_rate
      // But repeated_attacks needs 3+ consecutive high threats
      // Use custom config to test this scenario
      const config: AnomalyDetectionConfig = {
        ...DEFAULT_ANOMALY_CONFIG,
        highThreatRateThreshold: 0.9, // Very high threshold so it doesn't trigger
      };

      state.recentThreatLevels = [1, 2, 4, 4, 4, 4, 1, 2];

      const result = detectAnomalies(state, config);

      expect(result.detected).toBe(true);
      expect(result.type).toBe('repeated_attacks');
    });

    it('should return no anomaly for normal session', () => {
      const state = createSessionState('test');
      state.messageCount = 10;
      state.toolCallCount = 5;
      state.actionsBlocked = 0;

      // Normal threat levels
      state.recentThreatLevels = [0, 1, 0, 2, 1, 0, 1, 0];

      const result = detectAnomalies(state);

      expect(result.detected).toBe(false);
    });

    it('should use custom config', () => {
      const state = createSessionState('test');
      state.messageCount = 10;
      state.recentThreatLevels = [3, 3, 3, 3, 3]; // All level 3

      const strictConfig: AnomalyDetectionConfig = {
        ...DEFAULT_ANOMALY_CONFIG,
        highThreatThreshold: 3, // Lower threshold
        highThreatRateThreshold: 0.5,
      };

      const result = detectAnomalies(state, strictConfig);

      expect(result.detected).toBe(true);
      expect(result.type).toBe('high_threat_rate');
    });
  });
});

// =============================================================================
// Session State Manager Tests
// =============================================================================

describe('SessionStateManager', () => {
  let manager: SessionStateManager;

  beforeEach(() => {
    manager = new SessionStateManager();
  });

  describe('getOrCreate', () => {
    it('should create new session if not exists', () => {
      const state = manager.getOrCreate('session-1');

      expect(state.sessionId).toBe('session-1');
      expect(manager.size).toBe(1);
    });

    it('should return existing session', () => {
      const state1 = manager.getOrCreate('session-1');
      state1.messageCount = 5;

      const state2 = manager.getOrCreate('session-1');

      expect(state2.messageCount).toBe(5);
      expect(manager.size).toBe(1);
    });

    it('should create multiple sessions', () => {
      manager.getOrCreate('session-1');
      manager.getOrCreate('session-2');
      manager.getOrCreate('session-3');

      expect(manager.size).toBe(3);
    });
  });

  describe('get', () => {
    it('should return session if exists', () => {
      manager.getOrCreate('session-1');

      const state = manager.get('session-1');
      expect(state).toBeDefined();
      expect(state?.sessionId).toBe('session-1');
    });

    it('should return undefined if not exists', () => {
      const state = manager.get('nonexistent');
      expect(state).toBeUndefined();
    });
  });

  describe('has', () => {
    it('should return true if session exists', () => {
      manager.getOrCreate('session-1');
      expect(manager.has('session-1')).toBe(true);
    });

    it('should return false if session not exists', () => {
      expect(manager.has('nonexistent')).toBe(false);
    });
  });

  describe('endSession', () => {
    it('should return summary and remove session', () => {
      const state = manager.getOrCreate('session-1');
      state.messageCount = 10;

      const summary = manager.endSession('session-1', true);

      expect(summary).toBeDefined();
      expect(summary?.sessionId).toBe('session-1');
      expect(summary?.success).toBe(true);
      expect(summary?.messageCount).toBe(10);
      expect(manager.has('session-1')).toBe(false);
    });

    it('should return undefined for nonexistent session', () => {
      const summary = manager.endSession('nonexistent', true);
      expect(summary).toBeUndefined();
    });
  });

  describe('remove', () => {
    it('should remove session and return true', () => {
      manager.getOrCreate('session-1');

      const removed = manager.remove('session-1');

      expect(removed).toBe(true);
      expect(manager.has('session-1')).toBe(false);
    });

    it('should return false for nonexistent session', () => {
      const removed = manager.remove('nonexistent');
      expect(removed).toBe(false);
    });
  });

  describe('sessionIds', () => {
    it('should return all session IDs', () => {
      manager.getOrCreate('session-1');
      manager.getOrCreate('session-2');
      manager.getOrCreate('session-3');

      const ids = manager.sessionIds;

      expect(ids).toHaveLength(3);
      expect(ids).toContain('session-1');
      expect(ids).toContain('session-2');
      expect(ids).toContain('session-3');
    });
  });

  describe('clear', () => {
    it('should remove all sessions', () => {
      manager.getOrCreate('session-1');
      manager.getOrCreate('session-2');

      manager.clear();

      expect(manager.size).toBe(0);
    });
  });

  describe('cleanup', () => {
    it('should remove old sessions', () => {
      // Create sessions with old timestamps
      const state1 = manager.getOrCreate('old-session');
      state1.startedAt = Date.now() - 2 * 60 * 60 * 1000; // 2 hours ago

      const state2 = manager.getOrCreate('new-session');
      // state2 is current

      const removed = manager.cleanup();

      expect(removed).toBe(1);
      expect(manager.has('old-session')).toBe(false);
      expect(manager.has('new-session')).toBe(true);
    });
  });

  describe('getAggregateStats', () => {
    it('should aggregate stats from all sessions', () => {
      const state1 = manager.getOrCreate('session-1');
      state1.messageCount = 10;
      state1.toolCallCount = 5;
      state1.issuesDetected = 3;
      state1.actionsBlocked = 2;
      state1.alertsTriggered = 1;
      state1.maxThreatLevel = 3;

      const state2 = manager.getOrCreate('session-2');
      state2.messageCount = 5;
      state2.toolCallCount = 2;
      state2.issuesDetected = 1;
      state2.actionsBlocked = 1;
      state2.alertsTriggered = 0;
      state2.maxThreatLevel = 4;

      const stats = manager.getAggregateStats();

      expect(stats.activeSessions).toBe(2);
      expect(stats.totalMessages).toBe(15);
      expect(stats.totalToolCalls).toBe(7);
      expect(stats.totalIssues).toBe(4);
      expect(stats.totalBlocked).toBe(3);
      expect(stats.totalAlerts).toBe(1);
      expect(stats.maxThreatLevel).toBe(4);
    });
  });

  describe('maxSessions option', () => {
    it('should cleanup when at capacity', () => {
      const smallManager = new SessionStateManager({ maxSessions: 3 });

      // Create old session
      const oldState = smallManager.getOrCreate('old');
      oldState.startedAt = Date.now() - 60 * 60 * 1000; // 1 hour ago

      // Fill to capacity
      smallManager.getOrCreate('session-1');
      smallManager.getOrCreate('session-2');

      // This should trigger cleanup
      smallManager.getOrCreate('session-3');

      // Old session should be removed
      expect(smallManager.has('old')).toBe(false);
    });
  });
});

// =============================================================================
// Utility Functions Tests
// =============================================================================

describe('Utility Functions', () => {
  describe('getSessionDuration', () => {
    it('should format seconds', () => {
      const state = createSessionState('test');
      state.startedAt = Date.now() - 30 * 1000; // 30 seconds ago

      const duration = getSessionDuration(state);

      expect(duration).toMatch(/^\d+s$/);
    });

    it('should format minutes and seconds', () => {
      const state = createSessionState('test');
      state.startedAt = Date.now() - 90 * 1000; // 90 seconds ago

      const duration = getSessionDuration(state);

      expect(duration).toMatch(/^\d+m \d+s$/);
    });

    it('should format hours and minutes', () => {
      const state = createSessionState('test');
      state.startedAt = Date.now() - 90 * 60 * 1000; // 90 minutes ago

      const duration = getSessionDuration(state);

      expect(duration).toMatch(/^\d+h \d+m$/);
    });
  });

  describe('isSessionActive', () => {
    it('should return true for active session', () => {
      const state = createSessionState('test');

      expect(isSessionActive(state)).toBe(true);
    });

    it('should return false for timed out session', () => {
      const state = createSessionState('test');
      state.startedAt = Date.now() - 60 * 60 * 1000; // 1 hour ago

      expect(isSessionActive(state)).toBe(false);
    });

    it('should use custom timeout', () => {
      const state = createSessionState('test');
      state.startedAt = Date.now() - 10 * 1000; // 10 seconds ago

      expect(isSessionActive(state, 5000)).toBe(false); // 5 second timeout
      expect(isSessionActive(state, 60000)).toBe(true); // 60 second timeout
    });
  });

  describe('getSessionRiskLevel', () => {
    it('should return low for safe session', () => {
      const state = createSessionState('test');
      state.maxThreatLevel = 1;
      state.issuesDetected = 2;
      state.actionsBlocked = 0;

      expect(getSessionRiskLevel(state)).toBe('low');
    });

    it('should return medium for moderate issues', () => {
      const state = createSessionState('test');
      state.maxThreatLevel = 3;
      state.issuesDetected = 5;

      expect(getSessionRiskLevel(state)).toBe('medium');
    });

    it('should return high for elevated threat', () => {
      const state = createSessionState('test');
      state.maxThreatLevel = 4;

      expect(getSessionRiskLevel(state)).toBe('high');
    });

    it('should return critical for max threat', () => {
      const state = createSessionState('test');
      state.maxThreatLevel = 5;

      expect(getSessionRiskLevel(state)).toBe('critical');
    });

    it('should return critical for many blocks', () => {
      const state = createSessionState('test');
      state.actionsBlocked = 5;

      expect(getSessionRiskLevel(state)).toBe('critical');
    });
  });
});

// =============================================================================
// Default Config Tests
// =============================================================================

describe('Default Configuration', () => {
  it('should have sensible defaults', () => {
    expect(DEFAULT_ANOMALY_CONFIG.highThreatThreshold).toBe(4);
    expect(DEFAULT_ANOMALY_CONFIG.highThreatRateThreshold).toBe(0.3);
    expect(DEFAULT_ANOMALY_CONFIG.highBlockRateThreshold).toBe(0.5);
    expect(DEFAULT_ANOMALY_CONFIG.minMessagesForRateCheck).toBe(5);
    expect(DEFAULT_ANOMALY_CONFIG.recentThreatWindowSize).toBe(5);
    expect(DEFAULT_ANOMALY_CONFIG.escalationThreshold).toBe(2);
  });
});
