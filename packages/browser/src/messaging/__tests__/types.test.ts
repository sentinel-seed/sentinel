/**
 * @fileoverview Unit tests for messaging type guards
 *
 * @author Sentinel Team
 * @license MIT
 */

import { isBroadcastMessage } from '../types';

describe('Messaging Types', () => {
  describe('isBroadcastMessage', () => {
    it('returns true for valid broadcast message structure', () => {
      const message = {
        isBroadcast: true,
        event: {
          type: 'AGENT_CONNECTED',
          payload: { agent: {} },
          timestamp: Date.now(),
          eventId: 'evt-123',
        },
      };

      expect(isBroadcastMessage(message)).toBe(true);
    });

    it('returns false for null', () => {
      expect(isBroadcastMessage(null)).toBe(false);
    });

    it('returns false for undefined', () => {
      expect(isBroadcastMessage(undefined)).toBe(false);
    });

    it('returns false for primitives', () => {
      expect(isBroadcastMessage('string')).toBe(false);
      expect(isBroadcastMessage(123)).toBe(false);
      expect(isBroadcastMessage(true)).toBe(false);
    });

    it('returns false for object without isBroadcast', () => {
      expect(isBroadcastMessage({ event: {} })).toBe(false);
    });

    it('returns false for object with isBroadcast = false', () => {
      expect(isBroadcastMessage({ isBroadcast: false, event: {} })).toBe(false);
    });

    it('returns false for object without event', () => {
      expect(isBroadcastMessage({ isBroadcast: true })).toBe(false);
    });

    it('returns false for empty object', () => {
      expect(isBroadcastMessage({})).toBe(false);
    });

    it('returns false for array', () => {
      expect(isBroadcastMessage([])).toBe(false);
    });

    it('returns true with minimal valid structure', () => {
      expect(
        isBroadcastMessage({
          isBroadcast: true,
          event: { type: 'TEST', payload: {} },
        })
      ).toBe(true);
    });
  });
});
