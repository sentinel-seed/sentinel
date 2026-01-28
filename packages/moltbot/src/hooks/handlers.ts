/**
 * @sentinelseed/moltbot - Core Hook Handlers
 *
 * This module contains the core hook handler implementations.
 * These are pure functions that:
 * - Take typed events as input
 * - Use validators from validators/
 * - Update session state
 * - Return typed results
 *
 * Design Principles:
 * - Pure functions (no external side effects)
 * - Framework-agnostic (no Moltbot dependencies)
 * - Fully testable without mocks
 * - Consistent error handling (fail open)
 *
 * @module hooks/handlers
 */

import type { LevelConfig, SentinelMoltbotConfig, DetectedIssue } from '../types';
import { analyzeInput, validateOutput, validateTool } from '../validators';
import type {
  MessageReceivedEvent,
  MessageReceivedResult,
  BeforeAgentStartEvent,
  BeforeAgentStartResult,
  MessageSendingEvent,
  MessageSendingResult,
  BeforeToolCallEvent,
  BeforeToolCallResult,
  AgentEndEvent,
  AgentEndResult,
  SessionState,
  SessionSummary,
} from './types';
import {
  recordMessageReceived,
  recordOutputValidation,
  recordToolCall,
  recordAlert,
  detectAnomalies,
  createSessionSummary,
} from './state';
import { getSeedForLevel, hasSeed } from './seeds';

// =============================================================================
// Handler Context
// =============================================================================

/**
 * Context passed to all handlers.
 *
 * Contains configuration and state needed for processing.
 */
export interface HandlerContext {
  /** Parsed plugin configuration */
  readonly config: SentinelMoltbotConfig;
  /** Resolved level configuration */
  readonly levelConfig: LevelConfig;
  /** Session state for tracking (optional, for stateful handlers) */
  sessionState?: SessionState;
}

// =============================================================================
// Message Received Handler
// =============================================================================

/**
 * Handle a received message event.
 *
 * This handler:
 * 1. Analyzes the input for threats using validators
 * 2. Updates session state with threat level
 * 3. Determines if an alert should be sent
 * 4. Returns detailed analysis result
 *
 * Note: This is a fire-and-forget hook - it cannot block messages.
 * Use it for threat analysis, logging, and alerting.
 *
 * @param event - The message received event
 * @param context - Handler context with config and state
 * @returns Analysis result with threat assessment
 *
 * @example
 * ```typescript
 * const result = await handleMessageReceived(
 *   { content: 'Hello', sessionId: 'sess-1', timestamp: Date.now() },
 *   { config, levelConfig }
 * );
 *
 * if (result.shouldAlert) {
 *   sendAlert(result);
 * }
 * ```
 */
export async function handleMessageReceived(
  event: MessageReceivedEvent,
  context: HandlerContext
): Promise<MessageReceivedResult> {
  const startTime = Date.now();

  // Skip analysis if level is off
  if (context.levelConfig.level === 'off') {
    return createEmptyMessageReceivedResult(startTime);
  }

  try {
    // Analyze input for threats
    const analysis = await analyzeInput(event.content, context.levelConfig);

    // Update session state if available
    if (context.sessionState) {
      recordMessageReceived(context.sessionState, analysis.threatLevel);

      // Record alert if warranted
      if (shouldAlertForInput(analysis, context.levelConfig)) {
        recordAlert(context.sessionState);
      }
    }

    // Determine if we should alert
    const shouldAlert = shouldAlertForInput(analysis, context.levelConfig);

    return {
      analyzed: true,
      threatLevel: analysis.threatLevel,
      isPromptInjection: analysis.isPromptInjection,
      isJailbreakAttempt: analysis.isJailbreakAttempt,
      issues: analysis.issues,
      shouldAlert,
      durationMs: Date.now() - startTime,
    };
  } catch (error) {
    // Fail open - return safe result on error
    return createEmptyMessageReceivedResult(startTime);
  }
}

/**
 * Determine if an alert should be sent based on analysis and config.
 *
 * @param analysis - Input analysis result
 * @param levelConfig - Level configuration
 * @returns True if alert should be sent
 */
function shouldAlertForInput(
  analysis: { threatLevel: number; isPromptInjection: boolean },
  levelConfig: LevelConfig
): boolean {
  const { alerting } = levelConfig;

  // Alert on high threat if configured
  if (alerting.highThreatInput && analysis.threatLevel >= 4) {
    return true;
  }

  // Alert on prompt injection if configured
  if (alerting.promptInjection && analysis.isPromptInjection) {
    return true;
  }

  return false;
}

/**
 * Create an empty result for skipped analysis.
 *
 * @param startTime - When processing started
 * @returns Empty result indicating no analysis
 */
function createEmptyMessageReceivedResult(startTime: number): MessageReceivedResult {
  return {
    analyzed: true,
    threatLevel: 0,
    isPromptInjection: false,
    isJailbreakAttempt: false,
    issues: [],
    shouldAlert: false,
    durationMs: Date.now() - startTime,
  };
}

// =============================================================================
// Before Agent Start Handler
// =============================================================================

/**
 * Handle the before-agent-start event.
 *
 * This handler:
 * 1. Determines if a safety seed should be injected
 * 2. Gets the appropriate seed for the protection level
 * 3. Returns the seed as additional context
 *
 * The seed is prepended to the conversation to provide safety guidance
 * to the AI agent throughout the session.
 *
 * @param event - The before-agent-start event
 * @param context - Handler context with config and state
 * @returns Result with seed context to inject
 *
 * @example
 * ```typescript
 * const result = handleBeforeAgentStart(
 *   { sessionId: 'sess-1' },
 *   { config, levelConfig }
 * );
 *
 * if (result.seedInjected && result.additionalContext) {
 *   prependToConversation(result.additionalContext);
 * }
 * ```
 */
export function handleBeforeAgentStart(
  _event: BeforeAgentStartEvent,
  context: HandlerContext
): BeforeAgentStartResult {
  const { levelConfig } = context;

  // No seed if level is off or seedTemplate is none
  if (levelConfig.level === 'off' || !hasSeed(levelConfig)) {
    return {
      seedInjected: false,
      seedTemplate: levelConfig.seedTemplate,
      additionalContext: undefined,
    };
  }

  // Get the seed content
  const seedContent = getSeedForLevel(levelConfig);

  return {
    seedInjected: true,
    seedTemplate: levelConfig.seedTemplate,
    additionalContext: seedContent,
  };
}

// =============================================================================
// Message Sending Handler
// =============================================================================

/**
 * Handle the message-sending event.
 *
 * This handler:
 * 1. Validates the output content for safety issues
 * 2. Determines if the message should be blocked based on level
 * 3. Updates session state with validation results
 * 4. Returns detailed validation result
 *
 * This hook CAN block messages. When shouldBlock is true, the adapter
 * should cancel the message and optionally show the cancelReason.
 *
 * @param event - The message sending event
 * @param context - Handler context with config and state
 * @returns Validation result with blocking decision
 *
 * @example
 * ```typescript
 * const result = await handleMessageSending(
 *   { content: 'Here is your API key: sk-...', sessionId: 'sess-1' },
 *   { config, levelConfig }
 * );
 *
 * if (result.shouldBlock) {
 *   cancelMessage(result.cancelReason);
 * }
 * ```
 */
export async function handleMessageSending(
  event: MessageSendingEvent,
  context: HandlerContext
): Promise<MessageSendingResult> {
  const startTime = Date.now();

  // Skip validation if level is off
  if (context.levelConfig.level === 'off') {
    return createEmptyMessageSendingResult(startTime);
  }

  try {
    // Validate output content
    const validation = await validateOutput(
      event.content,
      context.levelConfig,
      { ignorePatterns: context.config.ignorePatterns }
    );

    // Update session state if available
    if (context.sessionState) {
      recordOutputValidation(
        context.sessionState,
        validation.shouldBlock,
        validation.issues.length
      );

      // Record alert if blocked and alerting is enabled
      if (validation.shouldBlock && context.levelConfig.alerting.blockedActions) {
        recordAlert(context.sessionState);
      }
    }

    // Format cancel reason if blocking
    const cancelReason = validation.shouldBlock
      ? formatCancelReason(validation.issues)
      : undefined;

    return {
      validated: true,
      safe: validation.safe,
      shouldBlock: validation.shouldBlock,
      cancelReason,
      issues: validation.issues,
      riskLevel: validation.riskLevel,
      durationMs: Date.now() - startTime,
    };
  } catch (error) {
    // Fail open - allow message on error
    return createEmptyMessageSendingResult(startTime);
  }
}

/**
 * Create an empty result for skipped validation.
 *
 * @param startTime - When processing started
 * @returns Empty result indicating no validation
 */
function createEmptyMessageSendingResult(startTime: number): MessageSendingResult {
  return {
    validated: true,
    safe: true,
    shouldBlock: false,
    cancelReason: undefined,
    issues: [],
    riskLevel: 'none',
    durationMs: Date.now() - startTime,
  };
}

/**
 * Format a human-readable cancel reason from issues.
 *
 * @param issues - Detected issues
 * @returns Formatted cancel reason
 */
function formatCancelReason(issues: readonly DetectedIssue[]): string {
  if (issues.length === 0) {
    return 'Blocked by Sentinel safety validation';
  }

  // Group by issue type for cleaner message
  const types = new Set(issues.map(i => i.type));
  const firstIssue = issues[0];

  if (types.size === 1 && firstIssue) {
    return `Blocked: ${firstIssue.description}`;
  }

  // Multiple types - summarize
  const descriptions = issues
    .slice(0, 3) // Limit to first 3
    .map(i => i.description)
    .join('; ');

  const suffix = issues.length > 3 ? ` (+${issues.length - 3} more)` : '';

  return `Blocked: ${descriptions}${suffix}`;
}

// =============================================================================
// Before Tool Call Handler
// =============================================================================

/**
 * Handle the before-tool-call event.
 *
 * This handler:
 * 1. Validates the tool call for safety issues
 * 2. Determines if the tool call should be blocked based on level
 * 3. Updates session state with validation results
 * 4. Returns detailed validation result
 *
 * This hook CAN block tool calls. When shouldBlock is true, the adapter
 * should prevent the tool execution and optionally show the blockReason.
 *
 * @param event - The before tool call event
 * @param context - Handler context with config and state
 * @returns Validation result with blocking decision
 *
 * @example
 * ```typescript
 * const result = await handleBeforeToolCall(
 *   { toolName: 'bash', params: { command: 'rm -rf /' }, sessionId: 'sess-1' },
 *   { config, levelConfig }
 * );
 *
 * if (result.shouldBlock) {
 *   blockToolCall(result.blockReason);
 * }
 * ```
 */
export async function handleBeforeToolCall(
  event: BeforeToolCallEvent,
  context: HandlerContext
): Promise<BeforeToolCallResult> {
  const startTime = Date.now();

  // Skip validation if level is off
  if (context.levelConfig.level === 'off') {
    return createEmptyToolCallResult(startTime);
  }

  try {
    // Validate tool call
    const validation = await validateTool(
      event.toolName,
      event.params as Record<string, unknown>,
      context.levelConfig,
      {
        trustedTools: context.config.trustedTools,
        dangerousTools: context.config.dangerousTools,
      }
    );

    // Update session state if available
    if (context.sessionState) {
      recordToolCall(
        context.sessionState,
        validation.shouldBlock,
        validation.issues.length
      );

      // Record alert if blocked and alerting is enabled
      if (validation.shouldBlock && context.levelConfig.alerting.blockedActions) {
        recordAlert(context.sessionState);
      }
    }

    // Format block reason if blocking
    const blockReason = validation.shouldBlock
      ? formatToolBlockReason(event.toolName, validation.issues, validation.reason)
      : undefined;

    return {
      validated: true,
      safe: validation.safe,
      shouldBlock: validation.shouldBlock,
      blockReason,
      issues: validation.issues,
      riskLevel: validation.riskLevel,
      durationMs: Date.now() - startTime,
    };
  } catch (error) {
    // Fail open - allow tool call on error
    return createEmptyToolCallResult(startTime);
  }
}

/**
 * Create an empty result for skipped validation.
 *
 * @param startTime - When processing started
 * @returns Empty result indicating no validation
 */
function createEmptyToolCallResult(startTime: number): BeforeToolCallResult {
  return {
    validated: true,
    safe: true,
    shouldBlock: false,
    blockReason: undefined,
    issues: [],
    riskLevel: 'none',
    durationMs: Date.now() - startTime,
  };
}

/**
 * Format a human-readable block reason for tool calls.
 *
 * @param toolName - Name of the tool
 * @param issues - Detected issues
 * @param validatorReason - Reason from validator (if any)
 * @returns Formatted block reason
 */
function formatToolBlockReason(
  toolName: string,
  issues: readonly DetectedIssue[],
  _validatorReason?: string
): string {
  // Always use rich formatting with tool name for better UX
  // (ignore generic validator reason in favor of specific messages)

  const firstIssue = issues[0];

  if (!firstIssue) {
    return `Tool '${toolName}' blocked by Sentinel safety validation`;
  }

  // Format based on issue type
  if (firstIssue.type === 'destructive_command') {
    return `Tool '${toolName}' blocked: potentially destructive operation`;
  }

  if (firstIssue.type === 'system_path') {
    return `Tool '${toolName}' blocked: access to restricted path`;
  }

  if (firstIssue.type === 'suspicious_url') {
    return `Tool '${toolName}' blocked: suspicious URL detected`;
  }

  // Default format
  return `Tool '${toolName}' blocked: ${firstIssue.description}`;
}

// =============================================================================
// Agent End Handler
// =============================================================================

/**
 * Handle the agent-end event.
 *
 * This handler:
 * 1. Analyzes the completed session for anomalies
 * 2. Creates a session summary with statistics
 * 3. Returns analysis result for logging/alerting
 *
 * Note: This is a fire-and-forget hook - it returns analysis but
 * cannot affect the completed session. Use it for session analytics,
 * anomaly detection, and audit logging.
 *
 * @param event - The agent end event
 * @param context - Handler context with config and state
 * @returns Session analysis result
 *
 * @example
 * ```typescript
 * const result = handleAgentEnd(
 *   { sessionId: 'sess-1', success: true, durationMs: 5000 },
 *   { config, levelConfig, sessionState }
 * );
 *
 * if (result.anomalyDetected) {
 *   logAnomaly(result.anomalyType, result.sessionSummary);
 * }
 * ```
 */
export function handleAgentEnd(
  event: AgentEndEvent,
  context: HandlerContext
): AgentEndResult {
  // If no session state, create a minimal summary
  if (!context.sessionState) {
    const minimalSummary = createMinimalSummary(event);
    return {
      logged: true,
      sessionSummary: minimalSummary,
      anomalyDetected: false,
    };
  }

  // Create session summary from state
  const sessionSummary = createSessionSummary(context.sessionState, event.success);

  // Skip anomaly detection if level is off
  if (context.levelConfig.level === 'off') {
    return {
      logged: true,
      sessionSummary,
      anomalyDetected: false,
    };
  }

  // Detect anomalies in the session
  const anomalyResult = detectAnomalies(context.sessionState);

  if (anomalyResult.detected && anomalyResult.type) {
    return {
      logged: true,
      sessionSummary,
      anomalyDetected: true,
      anomalyType: anomalyResult.type,
    };
  }

  return {
    logged: true,
    sessionSummary,
    anomalyDetected: false,
  };
}

/**
 * Create a minimal session summary when no state is available.
 *
 * @param event - The agent end event
 * @returns Minimal session summary
 */
function createMinimalSummary(event: AgentEndEvent): SessionSummary {
  return {
    sessionId: event.sessionId,
    success: event.success,
    durationMs: event.durationMs ?? 0,
    messageCount: 0,
    toolCallCount: 0,
    issuesDetected: 0,
    actionsBlocked: 0,
    maxThreatLevel: 0,
    alertsTriggered: 0,
  };
}

// =============================================================================
// Handler Aliases (for backward compatibility)
// =============================================================================

export { handleMessageReceived as messageReceivedHandler };
export { handleBeforeAgentStart as beforeAgentStartHandler };
export { handleMessageSending as messageSendingHandler };
export { handleBeforeToolCall as beforeToolCallHandler };
export { handleAgentEnd as agentEndHandler };
