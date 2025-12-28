/**
 * @fileoverview Unit tests for broadcast service
 *
 * Tests the core broadcasting functionality without requiring
 * complex type structures.
 *
 * @author Sentinel Team
 * @license MIT
 */

import { broadcast } from '../broadcast-service';

// Mock chrome API
const mockSendMessage = jest.fn().mockResolvedValue(undefined);
const mockTabsQuery = jest.fn().mockResolvedValue([]);
const mockTabsSendMessage = jest.fn().mockResolvedValue(undefined);

(global as any).chrome = {
  runtime: {
    sendMessage: mockSendMessage,
    lastError: null,
  },
  tabs: {
    query: mockTabsQuery,
    sendMessage: mockTabsSendMessage,
  },
};

describe('Broadcast Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSendMessage.mockResolvedValue(undefined);
    mockTabsQuery.mockResolvedValue([]);
    mockTabsSendMessage.mockResolvedValue(undefined);
  });

  describe('broadcast', () => {
    it('broadcasts event to extension', async () => {
      await broadcast('APPROVAL_QUEUE_CHANGED', { queueLength: 5, pendingIds: [] });

      expect(mockSendMessage).toHaveBeenCalledTimes(1);
      const message = mockSendMessage.mock.calls[0][0];
      expect(message.isBroadcast).toBe(true);
      expect(message.event.type).toBe('APPROVAL_QUEUE_CHANGED');
      expect(message.event.payload).toEqual({ queueLength: 5, pendingIds: [] });
      expect(message.event.timestamp).toBeDefined();
      expect(message.event.eventId).toBeDefined();
    });

    it('broadcasts event to all tabs', async () => {
      mockTabsQuery.mockResolvedValue([
        { id: 1, url: 'https://example.com' },
        { id: 2, url: 'https://other.com' },
      ]);

      await broadcast('APPROVAL_QUEUE_CHANGED', { queueLength: 3, pendingIds: [] });

      expect(mockTabsQuery).toHaveBeenCalledWith({});
      expect(mockTabsSendMessage).toHaveBeenCalledTimes(2);
      expect(mockTabsSendMessage).toHaveBeenCalledWith(1, expect.any(Object));
      expect(mockTabsSendMessage).toHaveBeenCalledWith(2, expect.any(Object));
    });

    it('handles tabs without IDs gracefully', async () => {
      mockTabsQuery.mockResolvedValue([
        { url: 'https://example.com' }, // No ID
        { id: 1, url: 'https://other.com' },
      ]);

      await broadcast('APPROVAL_QUEUE_CHANGED', { queueLength: 1, pendingIds: [] });

      expect(mockTabsSendMessage).toHaveBeenCalledTimes(1);
      expect(mockTabsSendMessage).toHaveBeenCalledWith(1, expect.any(Object));
    });

    it('handles extension message errors gracefully', async () => {
      mockSendMessage.mockRejectedValue(new Error('No receiving end'));

      await expect(
        broadcast('APPROVAL_QUEUE_CHANGED', { queueLength: 0, pendingIds: [] })
      ).resolves.toBeUndefined();
    });

    it('handles tab message errors gracefully', async () => {
      mockTabsQuery.mockResolvedValue([{ id: 1 }]);
      mockTabsSendMessage.mockRejectedValue(new Error('Tab closed'));

      await expect(
        broadcast('APPROVAL_QUEUE_CHANGED', { queueLength: 0, pendingIds: [] })
      ).resolves.toBeUndefined();
    });

    it('generates unique event IDs', async () => {
      await broadcast('APPROVAL_QUEUE_CHANGED', { queueLength: 1, pendingIds: [] });
      await broadcast('APPROVAL_QUEUE_CHANGED', { queueLength: 2, pendingIds: [] });

      const id1 = mockSendMessage.mock.calls[0][0].event.eventId;
      const id2 = mockSendMessage.mock.calls[1][0].event.eventId;

      expect(id1).not.toBe(id2);
    });

    it('includes timestamp in event', async () => {
      const before = Date.now();
      await broadcast('APPROVAL_QUEUE_CHANGED', { queueLength: 1, pendingIds: [] });
      const after = Date.now();

      const timestamp = mockSendMessage.mock.calls[0][0].event.timestamp;

      expect(timestamp).toBeGreaterThanOrEqual(before);
      expect(timestamp).toBeLessThanOrEqual(after);
    });
  });
});
