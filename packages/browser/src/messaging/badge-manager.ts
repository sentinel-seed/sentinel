/**
 * @fileoverview Badge Manager for extension icon badge
 *
 * Manages the badge displayed on the extension icon to show:
 * - Pending approval count
 * - Alert notifications
 * - Error states
 * - Extension status
 *
 * The badge provides at-a-glance status information to users
 * without requiring them to open the popup.
 *
 * @author Sentinel Team
 * @license MIT
 */

import type { BadgeState, BadgeConfig } from './types';

// =============================================================================
// BADGE CONFIGURATION
// =============================================================================

/**
 * Predefined badge configurations for each state
 */
const BADGE_CONFIGS: Record<BadgeState, BadgeConfig | null> = {
  clear: null,
  active: {
    text: ' ',  // Single space creates small colored dot
    backgroundColor: '#10b981', // Green - protection active
  },
  pending: {
    text: '',
    backgroundColor: '#6366f1', // Indigo
  },
  alert: {
    text: '!',
    backgroundColor: '#ef4444', // Red
  },
  error: {
    text: '!',
    backgroundColor: '#ef4444', // Red
  },
  disabled: {
    text: ' ',  // Single space creates small colored dot
    backgroundColor: '#6b7280', // Gray - protection disabled
  },
};

/**
 * Color for pending count based on urgency
 */
const PENDING_COLORS = {
  low: '#6366f1',     // Indigo - 1-3 pending
  medium: '#f59e0b',  // Amber - 4-9 pending
  high: '#ef4444',    // Red - 10+ pending
};

// =============================================================================
// BADGE MANAGER CLASS
// =============================================================================

/**
 * Manages the extension icon badge
 */
class BadgeManager {
  private currentState: BadgeState = 'clear';
  private pendingCount = 0;
  private alertCount = 0;
  private isDisabled = false;

  /**
   * Updates the badge based on current state
   */
  private async updateBadge(): Promise<void> {
    // Priority order: disabled > pending > alert > clear (no badge when active)
    // Badge only shows when user attention is needed
    let config: BadgeConfig | null = null;

    if (this.isDisabled) {
      config = BADGE_CONFIGS.disabled;
      this.currentState = 'disabled';
    } else if (this.pendingCount > 0) {
      config = this.getPendingBadgeConfig();
      this.currentState = 'pending';
    } else if (this.alertCount > 0) {
      config = {
        ...BADGE_CONFIGS.alert!,
        text: this.alertCount > 9 ? '9+' : String(this.alertCount),
      };
      this.currentState = 'alert';
    } else {
      // Protection active - no badge needed (clean icon = all good)
      config = null;
      this.currentState = 'active';
    }

    await this.applyBadgeConfig(config);
  }

  /**
   * Gets the badge config for pending approvals
   */
  private getPendingBadgeConfig(): BadgeConfig {
    const text = this.pendingCount > 99 ? '99+' : String(this.pendingCount);
    let backgroundColor = PENDING_COLORS.low;

    if (this.pendingCount >= 10) {
      backgroundColor = PENDING_COLORS.high;
    } else if (this.pendingCount >= 4) {
      backgroundColor = PENDING_COLORS.medium;
    }

    return { text, backgroundColor };
  }

  /**
   * Applies a badge configuration to the extension icon
   */
  private async applyBadgeConfig(config: BadgeConfig | null): Promise<void> {
    try {
      if (!config) {
        // Clear the badge
        await chrome.action.setBadgeText({ text: '' });
        return;
      }

      // Set badge text
      await chrome.action.setBadgeText({ text: config.text });

      // Set background color
      await chrome.action.setBadgeBackgroundColor({
        color: config.backgroundColor,
      });

      // Set text color (Chrome 110+)
      if (config.textColor && chrome.action.setBadgeTextColor) {
        await chrome.action.setBadgeTextColor({ color: config.textColor });
      }
    } catch (error) {
      console.warn('[BadgeManager] Failed to update badge:', error);
    }
  }

  // ===========================================================================
  // PUBLIC API
  // ===========================================================================

  /**
   * Sets the pending approval count
   *
   * @param count - Number of pending approvals
   */
  async setPendingCount(count: number): Promise<void> {
    this.pendingCount = Math.max(0, count);
    await this.updateBadge();
  }

  /**
   * Increments the pending approval count
   */
  async incrementPending(): Promise<void> {
    this.pendingCount++;
    await this.updateBadge();
  }

  /**
   * Decrements the pending approval count
   */
  async decrementPending(): Promise<void> {
    this.pendingCount = Math.max(0, this.pendingCount - 1);
    await this.updateBadge();
  }

  /**
   * Sets the unacknowledged alert count
   *
   * @param count - Number of unacknowledged alerts
   */
  async setAlertCount(count: number): Promise<void> {
    this.alertCount = Math.max(0, count);
    await this.updateBadge();
  }

  /**
   * Increments the alert count
   */
  async incrementAlerts(): Promise<void> {
    this.alertCount++;
    await this.updateBadge();
  }

  /**
   * Decrements the alert count
   */
  async decrementAlerts(): Promise<void> {
    this.alertCount = Math.max(0, this.alertCount - 1);
    await this.updateBadge();
  }

  /**
   * Sets the extension disabled state
   *
   * @param disabled - Whether the extension is disabled
   */
  async setDisabled(disabled: boolean): Promise<void> {
    this.isDisabled = disabled;
    await this.updateBadge();
  }

  /**
   * Shows an error badge temporarily
   *
   * @param durationMs - How long to show the error badge
   */
  async showError(durationMs = 5000): Promise<void> {
    await this.applyBadgeConfig(BADGE_CONFIGS.error);

    if (durationMs > 0) {
      setTimeout(() => {
        this.updateBadge();
      }, durationMs);
    }
  }

  /**
   * Clears all badge state
   */
  async clear(): Promise<void> {
    this.pendingCount = 0;
    this.alertCount = 0;
    this.isDisabled = false;
    await this.updateBadge();
  }

  /**
   * Gets the current badge state
   */
  getState(): {
    state: BadgeState;
    pendingCount: number;
    alertCount: number;
    isDisabled: boolean;
  } {
    return {
      state: this.currentState,
      pendingCount: this.pendingCount,
      alertCount: this.alertCount,
      isDisabled: this.isDisabled,
    };
  }

  /**
   * Initializes the badge manager with current state
   * Should be called on extension startup
   *
   * @param pendingCount - Initial pending count
   * @param alertCount - Initial alert count
   * @param isDisabled - Initial disabled state
   */
  async initialize(
    pendingCount = 0,
    alertCount = 0,
    isDisabled = false
  ): Promise<void> {
    this.pendingCount = pendingCount;
    this.alertCount = alertCount;
    this.isDisabled = isDisabled;
    await this.updateBadge();
  }
}

// =============================================================================
// SINGLETON INSTANCE
// =============================================================================

/**
 * Singleton instance of BadgeManager
 */
export const badgeManager = new BadgeManager();

export default badgeManager;
