/**
 * @sentinelseed/moltbot - Alert Manager
 *
 * Provides alert management and delivery for security events.
 * Supports webhooks, in-memory queue, and rate limiting.
 *
 * @module logging/alerts
 */

import type { SecurityAlert, AlertType, RiskLevel, DetectedIssue } from '../types';
import { formatAlertForWebhook } from './formatters';

// =============================================================================
// Constants
// =============================================================================

/** Default rate limit window in ms (1 minute) */
export const DEFAULT_RATE_LIMIT_WINDOW_MS = 60_000;

/** Default maximum alerts per window */
export const DEFAULT_RATE_LIMIT_MAX = 10;

/** Default webhook timeout in ms */
export const DEFAULT_WEBHOOK_TIMEOUT_MS = 5_000;

/** Default retry count for failed webhooks */
export const DEFAULT_WEBHOOK_RETRIES = 2;

// =============================================================================
// Types
// =============================================================================

/**
 * Options for creating an alert.
 */
export interface CreateAlertOptions {
  /** Alert type */
  type: AlertType;
  /** Severity level */
  severity: RiskLevel;
  /** Alert message */
  message: string;
  /** Related audit entry ID */
  auditEntryId?: string;
  /** Additional context */
  context?: Record<string, unknown>;
}

/**
 * Webhook configuration.
 */
export interface WebhookConfig {
  /** Webhook URL */
  url: string;
  /** HTTP headers to include */
  headers?: Record<string, string>;
  /** Request timeout in ms */
  timeoutMs?: number;
  /** Number of retries on failure */
  retries?: number;
  /** Minimum severity to send (optional filter) */
  minSeverity?: RiskLevel;
}

/**
 * Alert manager options.
 */
export interface AlertManagerOptions {
  /** Webhook configurations */
  webhooks?: WebhookConfig[];
  /** Rate limit window in ms */
  rateLimitWindowMs?: number;
  /** Maximum alerts per rate limit window */
  rateLimitMax?: number;
  /** Maximum alerts to keep in queue */
  maxQueueSize?: number;
  /** Enable/disable alert sending */
  enabled?: boolean;
}

/**
 * Result of sending an alert.
 */
export interface SendAlertResult {
  /** Whether the alert was queued */
  queued: boolean;
  /** Whether the alert was sent to webhooks */
  sent: boolean;
  /** Number of successful webhook deliveries */
  webhookSuccesses: number;
  /** Number of failed webhook deliveries */
  webhookFailures: number;
  /** Whether rate limited */
  rateLimited: boolean;
  /** The alert object */
  alert: SecurityAlert;
}

/**
 * Alert statistics.
 */
export interface AlertStats {
  /** Total alerts created */
  totalAlerts: number;
  /** Alerts by type */
  byType: Record<AlertType, number>;
  /** Alerts by severity */
  bySeverity: Record<RiskLevel, number>;
  /** Alerts rate limited */
  rateLimited: number;
  /** Webhook successes */
  webhookSuccesses: number;
  /** Webhook failures */
  webhookFailures: number;
  /** Current queue size */
  queueSize: number;
}

// =============================================================================
// Severity Order
// =============================================================================

/** Severity levels in order of increasing severity */
const SEVERITY_ORDER: RiskLevel[] = ['none', 'low', 'medium', 'high', 'critical'];

/**
 * Check if a severity meets a minimum threshold.
 */
function severityMeetsThreshold(severity: RiskLevel, minimum: RiskLevel): boolean {
  return SEVERITY_ORDER.indexOf(severity) >= SEVERITY_ORDER.indexOf(minimum);
}

// =============================================================================
// AlertManager
// =============================================================================

/**
 * Manager for security alerts.
 *
 * Provides:
 * - Alert creation with type and severity
 * - In-memory queue
 * - Webhook delivery
 * - Rate limiting
 *
 * @example
 * ```typescript
 * const alerts = new AlertManager({
 *   webhooks: [{
 *     url: 'https://hooks.example.com/sentinel',
 *     minSeverity: 'high',
 *   }],
 * });
 *
 * // Create and send an alert
 * await alerts.send({
 *   type: 'action_blocked',
 *   severity: 'high',
 *   message: 'Tool call blocked: rm -rf / detected',
 * });
 *
 * // Query recent alerts
 * const recent = alerts.getRecent(10);
 * ```
 */
export class AlertManager {
  /** Alert queue */
  private readonly queue: SecurityAlert[] = [];

  /** Alert counter */
  private alertCounter = 0;

  /** Webhook configurations */
  private readonly webhooks: WebhookConfig[];

  /** Rate limit tracking */
  private rateLimitWindow: number[] = [];

  /** Rate limit settings */
  private readonly rateLimitWindowMs: number;
  private readonly rateLimitMax: number;

  /** Maximum queue size */
  private readonly maxQueueSize: number;

  /** Whether alerts are enabled */
  private enabled: boolean;

  /** Statistics */
  private stats: AlertStats = {
    totalAlerts: 0,
    byType: {} as Record<AlertType, number>,
    bySeverity: {} as Record<RiskLevel, number>,
    rateLimited: 0,
    webhookSuccesses: 0,
    webhookFailures: 0,
    queueSize: 0,
  };

  /**
   * Create a new AlertManager.
   *
   * @param options - Manager options
   */
  constructor(options: AlertManagerOptions = {}) {
    this.webhooks = options.webhooks ?? [];
    this.rateLimitWindowMs = options.rateLimitWindowMs ?? DEFAULT_RATE_LIMIT_WINDOW_MS;
    this.rateLimitMax = options.rateLimitMax ?? DEFAULT_RATE_LIMIT_MAX;
    this.maxQueueSize = options.maxQueueSize ?? 100;
    this.enabled = options.enabled ?? true;
  }

  /**
   * Send an alert.
   *
   * @param options - Alert options
   * @returns Send result
   */
  async send(options: CreateAlertOptions): Promise<SendAlertResult> {
    const alert = this.createAlert(options);

    // Check if rate limited
    if (this.isRateLimited()) {
      this.stats.rateLimited++;
      return {
        queued: false,
        sent: false,
        webhookSuccesses: 0,
        webhookFailures: 0,
        rateLimited: true,
        alert,
      };
    }

    // Track rate limit
    this.trackRateLimit();

    // Add to queue
    this.addToQueue(alert);

    // Update stats
    this.stats.totalAlerts++;
    this.stats.byType[alert.type] = (this.stats.byType[alert.type] ?? 0) + 1;
    this.stats.bySeverity[alert.severity] = (this.stats.bySeverity[alert.severity] ?? 0) + 1;

    // Send to webhooks if enabled
    let webhookSuccesses = 0;
    let webhookFailures = 0;

    if (this.enabled && this.webhooks.length > 0) {
      const results = await this.sendToWebhooks(alert);
      webhookSuccesses = results.successes;
      webhookFailures = results.failures;
    }

    return {
      queued: true,
      sent: webhookSuccesses > 0,
      webhookSuccesses,
      webhookFailures,
      rateLimited: false,
      alert,
    };
  }

  /**
   * Send a high threat input alert.
   */
  async alertHighThreatInput(
    threatLevel: number,
    issues: readonly DetectedIssue[],
    sessionId?: string
  ): Promise<SendAlertResult> {
    const issueTypes = [...new Set(issues.map(i => i.type))].join(', ');

    return this.send({
      type: 'high_threat_input',
      severity: threatLevel >= 5 ? 'critical' : 'high',
      message: `High threat input detected (level ${threatLevel}): ${issueTypes}`,
      context: { threatLevel, issueCount: issues.length, sessionId },
    });
  }

  /**
   * Send an action blocked alert.
   */
  async alertActionBlocked(
    actionType: 'output' | 'tool',
    reason: string,
    sessionId?: string
  ): Promise<SendAlertResult> {
    return this.send({
      type: 'action_blocked',
      severity: 'high',
      message: `${actionType === 'output' ? 'Output' : 'Tool call'} blocked: ${reason}`,
      context: { actionType, sessionId },
    });
  }

  /**
   * Send a prompt injection alert.
   */
  async alertPromptInjection(
    content: string,
    sessionId?: string
  ): Promise<SendAlertResult> {
    return this.send({
      type: 'prompt_injection',
      severity: 'critical',
      message: 'Prompt injection attempt detected',
      context: {
        contentPreview: content.slice(0, 100),
        sessionId,
      },
    });
  }

  /**
   * Send a session anomaly alert.
   */
  async alertSessionAnomaly(
    anomalyType: string,
    details: Record<string, unknown>,
    sessionId?: string
  ): Promise<SendAlertResult> {
    return this.send({
      type: 'session_anomaly',
      severity: 'medium',
      message: `Session anomaly detected: ${anomalyType}`,
      context: { anomalyType, ...details, sessionId },
    });
  }

  /**
   * Send an error alert.
   */
  async alertError(
    error: Error,
    context?: Record<string, unknown>
  ): Promise<SendAlertResult> {
    return this.send({
      type: 'error',
      severity: 'medium',
      message: `Error: ${error.message}`,
      context: {
        errorName: error.name,
        ...context,
      },
    });
  }

  /**
   * Get recent alerts.
   *
   * @param count - Number of alerts
   * @returns Recent alerts (newest first)
   */
  getRecent(count = 10): SecurityAlert[] {
    return this.queue.slice(-count).reverse();
  }

  /**
   * Get alerts by type.
   *
   * @param type - Alert type
   * @param limit - Maximum to return
   * @returns Matching alerts
   */
  getByType(type: AlertType, limit?: number): SecurityAlert[] {
    const results = this.queue.filter(a => a.type === type).reverse();
    return limit ? results.slice(0, limit) : results;
  }

  /**
   * Get alerts by severity.
   *
   * @param minSeverity - Minimum severity
   * @param limit - Maximum to return
   * @returns Matching alerts
   */
  getBySeverity(minSeverity: RiskLevel, limit?: number): SecurityAlert[] {
    const results = this.queue
      .filter(a => severityMeetsThreshold(a.severity, minSeverity))
      .reverse();
    return limit ? results.slice(0, limit) : results;
  }

  /**
   * Get alert statistics.
   *
   * @returns Statistics
   */
  getStats(): AlertStats {
    return {
      ...this.stats,
      queueSize: this.queue.length,
    };
  }

  /**
   * Enable alert sending.
   */
  enable(): void {
    this.enabled = true;
  }

  /**
   * Disable alert sending.
   */
  disable(): void {
    this.enabled = false;
  }

  /**
   * Check if alerts are enabled.
   */
  isEnabled(): boolean {
    return this.enabled;
  }

  /**
   * Add a webhook configuration.
   *
   * @param config - Webhook configuration
   */
  addWebhook(config: WebhookConfig): void {
    this.webhooks.push(config);
  }

  /**
   * Remove a webhook by URL.
   *
   * @param url - Webhook URL
   * @returns Whether a webhook was removed
   */
  removeWebhook(url: string): boolean {
    const index = this.webhooks.findIndex(w => w.url === url);
    if (index >= 0) {
      this.webhooks.splice(index, 1);
      return true;
    }
    return false;
  }

  /**
   * Get the number of configured webhooks.
   */
  get webhookCount(): number {
    return this.webhooks.length;
  }

  /**
   * Clear the alert queue.
   */
  clear(): void {
    this.queue.length = 0;
    this.stats.queueSize = 0;
  }

  /**
   * Reset statistics.
   */
  resetStats(): void {
    this.stats = {
      totalAlerts: 0,
      byType: {} as Record<AlertType, number>,
      bySeverity: {} as Record<RiskLevel, number>,
      rateLimited: 0,
      webhookSuccesses: 0,
      webhookFailures: 0,
      queueSize: this.queue.length,
    };
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  /**
   * Create an alert object.
   */
  private createAlert(options: CreateAlertOptions): SecurityAlert {
    this.alertCounter++;

    return {
      type: options.type,
      severity: options.severity,
      message: options.message,
      timestamp: Date.now(),
      auditEntryId: options.auditEntryId,
      context: options.context,
    };
  }

  /**
   * Add an alert to the queue.
   */
  private addToQueue(alert: SecurityAlert): void {
    // Enforce queue size limit
    while (this.queue.length >= this.maxQueueSize) {
      this.queue.shift();
    }

    this.queue.push(alert);
  }

  /**
   * Check if currently rate limited.
   */
  private isRateLimited(): boolean {
    const now = Date.now();
    const windowStart = now - this.rateLimitWindowMs;

    // Clean old entries
    this.rateLimitWindow = this.rateLimitWindow.filter(t => t > windowStart);

    return this.rateLimitWindow.length >= this.rateLimitMax;
  }

  /**
   * Track a rate limit entry.
   */
  private trackRateLimit(): void {
    this.rateLimitWindow.push(Date.now());
  }

  /**
   * Send alert to all configured webhooks.
   */
  private async sendToWebhooks(
    alert: SecurityAlert
  ): Promise<{ successes: number; failures: number }> {
    let successes = 0;
    let failures = 0;

    const payload = formatAlertForWebhook(alert);

    const promises = this.webhooks.map(async webhook => {
      // Check severity filter
      if (webhook.minSeverity && !severityMeetsThreshold(alert.severity, webhook.minSeverity)) {
        return; // Skip this webhook
      }

      try {
        await this.sendToWebhook(webhook, payload);
        successes++;
        this.stats.webhookSuccesses++;
      } catch {
        failures++;
        this.stats.webhookFailures++;
      }
    });

    await Promise.all(promises);

    return { successes, failures };
  }

  /**
   * Send to a single webhook with retries.
   */
  private async sendToWebhook(
    webhook: WebhookConfig,
    payload: Record<string, unknown>
  ): Promise<void> {
    const retries = webhook.retries ?? DEFAULT_WEBHOOK_RETRIES;
    const timeout = webhook.timeoutMs ?? DEFAULT_WEBHOOK_TIMEOUT_MS;

    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
          const response = await fetch(webhook.url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...webhook.headers,
            },
            body: JSON.stringify(payload),
            signal: controller.signal,
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          return; // Success
        } finally {
          clearTimeout(timeoutId);
        }
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        // Continue to next retry
      }
    }

    throw lastError ?? new Error('Webhook failed');
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a new AlertManager instance.
 *
 * @param options - Manager options
 * @returns New AlertManager
 */
export function createAlertManager(options?: AlertManagerOptions): AlertManager {
  return new AlertManager(options);
}
