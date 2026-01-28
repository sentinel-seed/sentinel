/**
 * Basic Usage Example
 *
 * Shows how to use @sentinelseed/moltbot with Moltbot.
 */

import { createSentinelHooks } from '@sentinelseed/moltbot';

// Create hooks with guard level protection
const hooks = createSentinelHooks({
  level: 'guard',
});

// Export for Moltbot plugin registration
export const moltbot_hooks = {
  message_received: hooks.messageReceived,
  before_agent_start: hooks.beforeAgentStart,
  message_sending: hooks.messageSending,
  before_tool_call: hooks.beforeToolCall,
  agent_end: hooks.agentEnd,
};

// That's it! Sentinel is now protecting your agent.
