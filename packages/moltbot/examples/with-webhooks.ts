/**
 * Webhook Alerts Example
 *
 * Shows how to configure webhook alerts for security events.
 */

import { createSentinelHooks, AlertManager } from '@sentinelseed/moltbot';

// Create hooks with alert configuration
const hooks = createSentinelHooks({
  level: 'guard',
  alerts: {
    enabled: true,
    webhook: 'https://your-webhook.com/sentinel',
    minSeverity: 'high',
  },
});

// Or use AlertManager directly for more control
const alertManager = new AlertManager({
  webhooks: [
    {
      url: 'https://slack.webhook.com/sentinel',
      minSeverity: 'high',
      headers: {
        'X-Custom-Header': 'value',
      },
    },
    {
      url: 'https://pagerduty.webhook.com/sentinel',
      minSeverity: 'critical',
    },
  ],
  rateLimitWindowMs: 60000,
  rateLimitMax: 10,
});

// Send custom alerts
async function alertOnCustomEvent(sessionId: string) {
  await alertManager.alertActionBlocked(
    'output',
    'Custom security event detected',
    sessionId
  );
}

export { hooks, alertManager, alertOnCustomEvent };
