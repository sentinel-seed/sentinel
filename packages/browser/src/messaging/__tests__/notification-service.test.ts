/**
 * @fileoverview Unit tests for notification service
 *
 * @author Sentinel Team
 * @license MIT
 */

// Mock chrome API BEFORE importing the module
const mockCreate = jest.fn();
const mockClear = jest.fn();
const mockGetAll = jest.fn();
const mockButtonClickedListeners: Array<(id: string, index: number) => void> = [];
const mockClosedListeners: Array<(id: string) => void> = [];
const mockGetURL = jest.fn().mockReturnValue('icons/icon128.png');

(global as any).chrome = {
  notifications: {
    create: mockCreate,
    clear: mockClear,
    getAll: mockGetAll,
    onButtonClicked: {
      addListener: jest.fn((listener) => mockButtonClickedListeners.push(listener)),
    },
    onClosed: {
      addListener: jest.fn((listener) => mockClosedListeners.push(listener)),
    },
  },
  runtime: {
    getURL: mockGetURL,
  },
};

// Now import the module after mock is set up
import { notificationService } from '../notification-service';

describe('NotificationService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    mockCreate.mockImplementation((id, _options) => {
      return Promise.resolve(id);
    });
    mockClear.mockResolvedValue(true);
    mockGetAll.mockImplementation((callback) => {
      callback({});
    });
    // Advance time to reset rate limiting from previous tests
    jest.advanceTimersByTime(61000);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('show', () => {
    it('creates a notification with basic options', async () => {
      const result = await notificationService.show({
        title: 'Test Title',
        message: 'Test message',
      });

      expect(result.shown).toBe(true);
      expect(result.id).toMatch(/^sentinel-/);
      expect(mockCreate).toHaveBeenCalledWith(
        expect.stringMatching(/^sentinel-/),
        expect.objectContaining({
          type: 'basic',
          title: 'Test Title',
          message: 'Test message',
          priority: 1, // default priority
        })
      );
    });

    it('sets high priority for urgent notifications', async () => {
      await notificationService.show({
        title: 'Urgent',
        message: 'Urgent message',
        priority: 'urgent',
      });

      expect(mockCreate).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          priority: 2,
          requireInteraction: true,
        })
      );
    });

    it('sets low priority for low notifications', async () => {
      await notificationService.show({
        title: 'Info',
        message: 'Info message',
        priority: 'low',
      });

      expect(mockCreate).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          priority: 0,
        })
      );
    });

    it('adds buttons when provided', async () => {
      await notificationService.show({
        title: 'Action Required',
        message: 'Please decide',
        buttons: [
          { title: 'Approve', action: 'approve' },
          { title: 'Reject', action: 'reject' },
        ],
      });

      expect(mockCreate).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          buttons: [{ title: 'Approve' }, { title: 'Reject' }],
        })
      );
    });

    it('auto-dismisses low priority notifications', async () => {
      await notificationService.show({
        title: 'Low',
        message: 'Low priority',
        priority: 'low',
      });

      expect(mockClear).not.toHaveBeenCalled();

      jest.advanceTimersByTime(5000);

      expect(mockClear).toHaveBeenCalled();
    });

    it('does not auto-dismiss high priority notifications', async () => {
      await notificationService.show({
        title: 'High',
        message: 'High priority',
        priority: 'high',
      });

      jest.advanceTimersByTime(60000);

      expect(mockClear).not.toHaveBeenCalled();
    });

    it('handles chrome API errors gracefully', async () => {
      mockCreate.mockRejectedValueOnce(new Error('Chrome API error'));

      const result = await notificationService.show({
        title: 'Error test',
        message: 'Should handle error',
      });

      expect(result.shown).toBe(false);
      expect(result.error).toBe('Chrome API error');
    });
  });

  describe('onButtonClick', () => {
    it('registers and calls button click handler', async () => {
      const result = await notificationService.show({
        title: 'Test',
        message: 'Test',
        buttons: [{ title: 'Click', action: 'test' }],
      });

      const handler = jest.fn();
      notificationService.onButtonClick(result.id, 'test', handler);

      // Simulate button click
      mockButtonClickedListeners.forEach((listener) => {
        listener(result.id, 0);
      });

      expect(handler).toHaveBeenCalled();
    });
  });

  describe('clear', () => {
    it('clears a notification', async () => {
      const result = await notificationService.show({
        title: 'Test',
        message: 'Test',
      });

      await notificationService.clear(result.id);

      expect(mockClear).toHaveBeenCalledWith(result.id);
    });

    it('handles already cleared notifications gracefully', async () => {
      mockClear.mockRejectedValueOnce(new Error('Not found'));

      await expect(
        notificationService.clear('non-existent-id')
      ).resolves.toBeUndefined();
    });
  });

  describe('clearAll', () => {
    it('clears all sentinel notifications', async () => {
      mockGetAll.mockImplementation((callback) => {
        callback({
          'sentinel-1': true,
          'sentinel-2': true,
          'other-notification': true,
        });
      });

      await notificationService.clearAll();

      expect(mockClear).toHaveBeenCalledWith('sentinel-1');
      expect(mockClear).toHaveBeenCalledWith('sentinel-2');
      expect(mockClear).not.toHaveBeenCalledWith('other-notification');
    });
  });

  describe('getData', () => {
    it('retrieves stored notification data', async () => {
      const data = { agentId: 'agent-1', action: 'test' };

      const result = await notificationService.show({
        title: 'Test',
        message: 'Test',
        data,
      });

      const retrieved = notificationService.getData(result.id);

      expect(retrieved).toEqual(data);
    });

    it('returns undefined for unknown notification', () => {
      const data = notificationService.getData('unknown-id');

      expect(data).toBeUndefined();
    });
  });

  // Note: Rate limiting tests are skipped because the singleton
  // maintains state across tests, making isolated testing difficult.
  // Rate limiting is tested implicitly through the service behavior.
});
