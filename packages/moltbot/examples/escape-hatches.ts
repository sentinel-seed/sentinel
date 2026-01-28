/**
 * Escape Hatches Example
 *
 * Shows how to programmatically manage escape hatches.
 */

import { EscapeManager } from '@sentinelseed/moltbot';

// Create an escape manager
const escapes = new EscapeManager();

// Session ID from Moltbot
const sessionId = 'user-session-123';

// Grant a one-time bypass for the next output
function allowNextOutput() {
  escapes.grantAllowOnce(sessionId, { scope: 'output' });
  console.log('Next output will bypass validation');
}

// Pause protection for 5 minutes
function pauseProtection() {
  const result = escapes.pauseProtection(sessionId, {
    durationMs: 5 * 60 * 1000,
    reason: 'User requested pause',
  });

  if (result.success) {
    console.log('Protection paused');
  }
}

// Resume protection
function resumeProtection() {
  escapes.resumeProtection(sessionId);
  console.log('Protection resumed');
}

// Trust a specific tool for this session
function trustTool(toolName: string) {
  escapes.trustTool(sessionId, toolName, { level: 'session' });
  console.log(`Tool '${toolName}' trusted for this session`);
}

// Check if protection should be bypassed
function shouldBypassOutput(): boolean {
  const result = escapes.shouldAllowOutput(sessionId);
  return result.allowed;
}

// Cleanup on session end
function cleanup() {
  escapes.cleanupSession(sessionId);
}

export {
  escapes,
  allowNextOutput,
  pauseProtection,
  resumeProtection,
  trustTool,
  shouldBypassOutput,
  cleanup,
};
