/**
 * @fileoverview Unit tests for badge manager
 *
 * @author Sentinel Team
 * @license MIT
 */

import { badgeManager } from '../badge-manager';

// Mock chrome API
const mockSetBadgeText = jest.fn().mockResolvedValue(undefined);
const mockSetBadgeBackgroundColor = jest.fn().mockResolvedValue(undefined);
const mockSetBadgeTextColor = jest.fn().mockResolvedValue(undefined);

(global as any).chrome = {
  action: {
    setBadgeText: mockSetBadgeText,
    setBadgeBackgroundColor: mockSetBadgeBackgroundColor,
    setBadgeTextColor: mockSetBadgeTextColor,
  },
};

describe('BadgeManager', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    // Reset badge state
    await badgeManager.clear();
    jest.clearAllMocks(); // Clear mocks again after clear()
  });

  describe('initialize', () => {
    it('initializes with pending count', async () => {
      await badgeManager.initialize(5, 0, false);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '5' });
      expect(mockSetBadgeBackgroundColor).toHaveBeenCalled();
    });

    it('initializes with alert count when no pending', async () => {
      await badgeManager.initialize(0, 3, false);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '3' });
    });

    it('initializes disabled state', async () => {
      await badgeManager.initialize(0, 0, true);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: ' ' });
      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({ color: '#6b7280' });
    });

    it('clears badge when active (no pending, no alerts, not disabled)', async () => {
      await badgeManager.initialize(0, 0, false);

      // Active state = no badge (clean icon)
      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '' });
    });
  });

  describe('setPendingCount', () => {
    it('sets pending count', async () => {
      await badgeManager.setPendingCount(3);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '3' });
    });

    it('shows correct color for low count (1-3)', async () => {
      await badgeManager.setPendingCount(2);

      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({
        color: '#6366f1', // Indigo
      });
    });

    it('shows correct color for medium count (4-9)', async () => {
      await badgeManager.setPendingCount(5);

      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({
        color: '#f59e0b', // Amber
      });
    });

    it('shows correct color for high count (10+)', async () => {
      await badgeManager.setPendingCount(15);

      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({
        color: '#ef4444', // Red
      });
    });

    it('shows 99+ for counts over 99', async () => {
      await badgeManager.setPendingCount(150);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '99+' });
    });

    it('clears badge when count is 0', async () => {
      await badgeManager.setPendingCount(-5);

      // No pending = clear badge (active state)
      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '' });
    });
  });

  describe('incrementPending / decrementPending', () => {
    it('increments pending count', async () => {
      await badgeManager.setPendingCount(2);
      jest.clearAllMocks();

      await badgeManager.incrementPending();

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '3' });
    });

    it('decrements pending count', async () => {
      await badgeManager.setPendingCount(3);
      jest.clearAllMocks();

      await badgeManager.decrementPending();

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '2' });
    });

    it('clears badge when decremented to zero', async () => {
      await badgeManager.setPendingCount(0);
      jest.clearAllMocks();

      await badgeManager.decrementPending();

      // pending = 0, badge cleared
      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '' });
    });
  });

  describe('setAlertCount', () => {
    it('sets alert count when no pending approvals', async () => {
      await badgeManager.setAlertCount(2);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '2' });
      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({
        color: '#ef4444', // Red for alerts
      });
    });

    it('shows 9+ for alert counts over 9', async () => {
      await badgeManager.setAlertCount(15);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '9+' });
    });

    it('pending takes priority over alerts', async () => {
      await badgeManager.setPendingCount(3);
      jest.clearAllMocks();

      await badgeManager.setAlertCount(5);

      // Should still show pending count
      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '3' });
    });
  });

  describe('incrementAlerts / decrementAlerts', () => {
    it('increments alert count', async () => {
      await badgeManager.setAlertCount(1);
      jest.clearAllMocks();

      await badgeManager.incrementAlerts();

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '2' });
    });

    it('decrements alert count', async () => {
      await badgeManager.setAlertCount(3);
      jest.clearAllMocks();

      await badgeManager.decrementAlerts();

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '2' });
    });
  });

  describe('setDisabled', () => {
    it('shows gray dot when disabled', async () => {
      await badgeManager.setDisabled(true);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: ' ' });
      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({
        color: '#6b7280', // Gray
      });
    });

    it('disabled takes priority over pending and alerts', async () => {
      await badgeManager.setPendingCount(5);
      await badgeManager.setAlertCount(3);
      jest.clearAllMocks();

      await badgeManager.setDisabled(true);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: ' ' });
    });

    it('shows pending when re-enabled', async () => {
      await badgeManager.setPendingCount(5);
      await badgeManager.setDisabled(true);
      jest.clearAllMocks();

      await badgeManager.setDisabled(false);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '5' });
    });
  });

  describe('showError', () => {
    it('shows error badge', async () => {
      await badgeManager.showError();

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '!' });
      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({
        color: '#ef4444',
      });
    });

    it('restores previous state after timeout', async () => {
      jest.useFakeTimers();
      await badgeManager.setPendingCount(3);
      jest.clearAllMocks();

      await badgeManager.showError(1000);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '!' });

      jest.advanceTimersByTime(1000);

      // Should restore pending count
      expect(mockSetBadgeText).toHaveBeenLastCalledWith({ text: '3' });

      jest.useRealTimers();
    });

    it('does not auto-clear when duration is 0', async () => {
      jest.useFakeTimers();

      await badgeManager.showError(0);

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '!' });

      jest.advanceTimersByTime(10000);

      // Should still show error (only one call)
      expect(mockSetBadgeText).toHaveBeenCalledTimes(1);

      jest.useRealTimers();
    });
  });

  describe('clear', () => {
    it('clears all state and removes badge', async () => {
      await badgeManager.setPendingCount(5);
      await badgeManager.setAlertCount(3);
      await badgeManager.setDisabled(true);
      jest.clearAllMocks();

      await badgeManager.clear();

      // After clear, badge is removed (active state)
      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '' });
    });
  });

  describe('getState', () => {
    it('returns current state', async () => {
      await badgeManager.setPendingCount(5);
      await badgeManager.setAlertCount(2);

      const state = badgeManager.getState();

      expect(state).toEqual({
        state: 'pending',
        pendingCount: 5,
        alertCount: 2,
        isDisabled: false,
      });
    });

    it('returns disabled state', async () => {
      await badgeManager.setDisabled(true);

      const state = badgeManager.getState();

      expect(state.state).toBe('disabled');
      expect(state.isDisabled).toBe(true);
    });

    it('returns active state when nothing blocking', async () => {
      await badgeManager.clear();

      const state = badgeManager.getState();

      expect(state).toEqual({
        state: 'active',
        pendingCount: 0,
        alertCount: 0,
        isDisabled: false,
      });
    });
  });

  describe('priority order', () => {
    it('disabled > pending > alert > active', async () => {
      // Set all states
      await badgeManager.setPendingCount(3);
      await badgeManager.setAlertCount(2);
      await badgeManager.setDisabled(true);

      let state = badgeManager.getState();
      expect(state.state).toBe('disabled');

      // Remove disabled
      await badgeManager.setDisabled(false);
      state = badgeManager.getState();
      expect(state.state).toBe('pending');

      // Remove pending
      await badgeManager.setPendingCount(0);
      state = badgeManager.getState();
      expect(state.state).toBe('alert');

      // Remove alerts - now shows active (protection running)
      await badgeManager.setAlertCount(0);
      state = badgeManager.getState();
      expect(state.state).toBe('active');
    });
  });
});
