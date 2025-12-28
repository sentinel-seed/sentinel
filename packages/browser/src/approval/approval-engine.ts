/**
 * @fileoverview Approval Engine - Rule matching and decision logic
 *
 * This module implements the core approval decision engine that:
 * - Evaluates actions against approval rules
 * - Matches conditions using various operators
 * - Determines whether to auto-approve, auto-reject, or require manual approval
 * - Provides default behavior based on risk levels
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  ApprovalRule,
  ApprovalAction,
  ApprovalDecision,
  RuleCondition,
  RuleConditionField,
  RuleConditionOperator,
  RiskLevel,
  AgentAction,
  MCPToolCall,
  PendingApproval,
  ActionHistoryEntry,
} from '../types';
import * as store from './approval-store';

// =============================================================================
// TYPES
// =============================================================================

/** Context for evaluating an action */
export interface EvaluationContext {
  /** Source of the action */
  source: 'agent_shield' | 'mcp_gateway';
  /** The action to evaluate */
  action: AgentAction | MCPToolCall;
}

/** Result of rule evaluation */
export interface EvaluationResult {
  /** The action to take */
  action: ApprovalAction;
  /** The rule that matched (if any) */
  matchedRule?: ApprovalRule;
  /** Reason for the decision */
  reason: string;
  /** Whether this was a default decision */
  isDefault: boolean;
}

// =============================================================================
// DEFAULT BEHAVIOR
// =============================================================================

/**
 * Default actions based on risk level.
 * Used when no rule matches.
 */
const DEFAULT_ACTIONS_BY_RISK: Record<RiskLevel, ApprovalAction> = {
  low: 'auto_approve',
  medium: 'require_approval',
  high: 'require_approval',
  critical: 'auto_reject',
};

/**
 * Default reasons for each action type.
 */
const DEFAULT_REASONS: Record<ApprovalAction, string> = {
  auto_approve: 'Low risk action automatically approved',
  auto_reject: 'Critical risk action automatically rejected',
  require_approval: 'Action requires manual approval',
};

// =============================================================================
// CONDITION EVALUATION
// =============================================================================

/**
 * Extracts the value of a field from an evaluation context.
 *
 * @param context - The evaluation context
 * @param field - The field to extract
 * @returns The field value, or undefined if not found
 */
function getFieldValue(
  context: EvaluationContext,
  field: RuleConditionField
): unknown {
  const { source, action } = context;

  switch (field) {
    // Common fields
    case 'source':
      return source;
    case 'riskLevel':
      return action.riskLevel;
    case 'estimatedValueUsd':
      if ('estimatedValueUsd' in action) {
        return action.estimatedValueUsd;
      }
      return undefined;

    // Agent Shield fields
    case 'agentType':
      if (source === 'agent_shield' && 'agentId' in action) {
        // Would need to look up agent type from registry
        // For now, return from action params if available
        return (action as AgentAction).params?.agentType;
      }
      return undefined;
    case 'agentTrustLevel':
      if (source === 'agent_shield' && 'agentId' in action) {
        return (action as AgentAction).params?.trustLevel;
      }
      return undefined;
    case 'actionType':
      if (source === 'agent_shield') {
        return (action as AgentAction).type;
      }
      return undefined;
    case 'memoryCompromised':
      if (source === 'agent_shield') {
        return (action as AgentAction).memoryContext?.isCompromised;
      }
      return undefined;

    // MCP Gateway fields
    case 'mcpServerTrusted':
      if (source === 'mcp_gateway') {
        return (action as MCPToolCall).arguments?.serverTrusted;
      }
      return undefined;
    case 'mcpToolName':
      if (source === 'mcp_gateway') {
        return (action as MCPToolCall).tool;
      }
      return undefined;
    case 'mcpSource':
      if (source === 'mcp_gateway') {
        return (action as MCPToolCall).source;
      }
      return undefined;

    default:
      return undefined;
  }
}

/**
 * Evaluates a single condition against a context.
 *
 * @param condition - The condition to evaluate
 * @param context - The evaluation context
 * @returns True if the condition is satisfied
 */
function evaluateCondition(
  condition: RuleCondition,
  context: EvaluationContext
): boolean {
  const fieldValue = getFieldValue(context, condition.field);
  const { operator, value } = condition;

  // Handle undefined field values
  if (fieldValue === undefined) {
    return false;
  }

  switch (operator) {
    case 'equals':
      return fieldValue === value;

    case 'not_equals':
      return fieldValue !== value;

    case 'greater_than':
      return typeof fieldValue === 'number' &&
        typeof value === 'number' &&
        fieldValue > value;

    case 'less_than':
      return typeof fieldValue === 'number' &&
        typeof value === 'number' &&
        fieldValue < value;

    case 'greater_than_or_equals':
      return typeof fieldValue === 'number' &&
        typeof value === 'number' &&
        fieldValue >= value;

    case 'less_than_or_equals':
      return typeof fieldValue === 'number' &&
        typeof value === 'number' &&
        fieldValue <= value;

    case 'contains':
      if (typeof fieldValue === 'string' && typeof value === 'string') {
        return fieldValue.toLowerCase().includes(value.toLowerCase());
      }
      if (Array.isArray(fieldValue) && typeof value === 'string') {
        return fieldValue.includes(value);
      }
      return false;

    case 'not_contains':
      if (typeof fieldValue === 'string' && typeof value === 'string') {
        return !fieldValue.toLowerCase().includes(value.toLowerCase());
      }
      if (Array.isArray(fieldValue) && typeof value === 'string') {
        return !fieldValue.includes(value);
      }
      return true;

    case 'in':
      if (Array.isArray(value)) {
        return (value as Array<string | number | boolean>).includes(
          fieldValue as string | number | boolean
        );
      }
      return false;

    case 'not_in':
      if (Array.isArray(value)) {
        return !(value as Array<string | number | boolean>).includes(
          fieldValue as string | number | boolean
        );
      }
      return true;

    case 'matches_regex':
      if (typeof fieldValue === 'string' && typeof value === 'string') {
        try {
          const regex = new RegExp(value, 'i');
          return regex.test(fieldValue);
        } catch {
          return false;
        }
      }
      return false;

    default:
      return false;
  }
}

/**
 * Evaluates all conditions in a rule against a context.
 * All conditions must be satisfied for the rule to match (AND logic).
 *
 * @param rule - The rule to evaluate
 * @param context - The evaluation context
 * @returns True if all conditions are satisfied
 */
function evaluateRule(rule: ApprovalRule, context: EvaluationContext): boolean {
  // Empty conditions means the rule always matches
  if (rule.conditions.length === 0) {
    return true;
  }

  // All conditions must be satisfied (AND logic)
  return rule.conditions.every((condition) =>
    evaluateCondition(condition, context)
  );
}

// =============================================================================
// MAIN EVALUATION
// =============================================================================

/**
 * Evaluates an action against all enabled rules and returns the decision.
 *
 * Rules are evaluated in order of priority (highest first).
 * The first matching rule determines the action.
 * If no rule matches, the default action based on risk level is used.
 *
 * @param context - The evaluation context
 * @returns Promise resolving to the evaluation result
 */
export async function evaluateAction(
  context: EvaluationContext
): Promise<EvaluationResult> {
  // Get all enabled rules, sorted by priority (descending)
  const rules = await store.getEnabledRules();

  // Evaluate each rule in order
  for (const rule of rules) {
    if (evaluateRule(rule, context)) {
      return {
        action: rule.action,
        matchedRule: rule,
        reason: rule.reason || DEFAULT_REASONS[rule.action],
        isDefault: false,
      };
    }
  }

  // No rule matched, use default based on risk level
  const riskLevel = context.action.riskLevel;
  const defaultAction = DEFAULT_ACTIONS_BY_RISK[riskLevel];

  return {
    action: defaultAction,
    reason: `Default action for ${riskLevel} risk level`,
    isDefault: true,
  };
}

// =============================================================================
// ACTION PROCESSING
// =============================================================================

/**
 * Processes an action through the approval engine.
 * This is the main entry point for the approval flow.
 *
 * @param context - The evaluation context
 * @param settings - Approval settings (for timeout configuration)
 * @returns Promise resolving to the processing result
 */
export async function processAction(
  context: EvaluationContext,
  autoRejectTimeoutMs: number = 300000
): Promise<{
  decision: ApprovalDecision | null;
  pending: PendingApproval | null;
}> {
  const result = await evaluateAction(context);

  if (result.action === 'auto_approve') {
    const decision: ApprovalDecision = {
      action: 'approve',
      method: 'auto',
      ruleId: result.matchedRule?.id,
      reason: result.reason,
      timestamp: Date.now(),
    };

    // Add to history
    const historyEntry: ActionHistoryEntry = {
      id: crypto.randomUUID(),
      source: context.source,
      action: context.action,
      decision,
      processedAt: Date.now(),
    };
    await store.addHistoryEntry(historyEntry);

    return { decision, pending: null };
  }

  if (result.action === 'auto_reject') {
    const decision: ApprovalDecision = {
      action: 'reject',
      method: 'auto',
      ruleId: result.matchedRule?.id,
      reason: result.reason,
      timestamp: Date.now(),
    };

    // Add to history
    const historyEntry: ActionHistoryEntry = {
      id: crypto.randomUUID(),
      source: context.source,
      action: context.action,
      decision,
      processedAt: Date.now(),
    };
    await store.addHistoryEntry(historyEntry);

    return { decision, pending: null };
  }

  // Requires manual approval
  const pending: PendingApproval = {
    id: crypto.randomUUID(),
    source: context.source,
    action: context.action,
    queuedAt: Date.now(),
    expiresAt: autoRejectTimeoutMs > 0
      ? Date.now() + autoRejectTimeoutMs
      : undefined,
    viewCount: 0,
  };

  await store.addPendingApproval(pending);

  return { decision: null, pending };
}

/**
 * Manually approves or rejects a pending action.
 *
 * @param pendingId - ID of the pending approval
 * @param action - The action to take ('approve' or 'reject')
 * @param reason - Reason for the decision
 * @param modifiedParams - Modified parameters (if action is 'modify')
 * @returns Promise resolving to the decision
 */
export async function decidePending(
  pendingId: string,
  action: 'approve' | 'reject' | 'modify',
  reason: string,
  modifiedParams?: Record<string, unknown>
): Promise<ApprovalDecision | null> {
  const pending = await store.getPendingApproval(pendingId);
  if (!pending) {
    return null;
  }

  const decision: ApprovalDecision = {
    action,
    method: 'manual',
    reason,
    timestamp: Date.now(),
    modifiedParams,
  };

  // Remove from pending queue
  await store.removePendingApproval(pendingId);

  // Add to history
  const historyEntry: ActionHistoryEntry = {
    id: crypto.randomUUID(),
    source: pending.source,
    action: pending.action,
    decision,
    processedAt: Date.now(),
  };
  await store.addHistoryEntry(historyEntry);

  return decision;
}

/**
 * Processes expired pending approvals.
 * Should be called periodically (e.g., via alarm).
 *
 * @returns Promise resolving to the number of expired approvals processed
 */
export async function processExpiredApprovals(): Promise<number> {
  const expired = await store.getExpiredApprovals();

  for (const pending of expired) {
    const decision: ApprovalDecision = {
      action: 'reject',
      method: 'auto',
      reason: 'Approval request timed out',
      timestamp: Date.now(),
    };

    // Remove from pending queue
    await store.removePendingApproval(pending.id);

    // Add to history
    const historyEntry: ActionHistoryEntry = {
      id: crypto.randomUUID(),
      source: pending.source,
      action: pending.action,
      decision,
      processedAt: Date.now(),
    };
    await store.addHistoryEntry(historyEntry);
  }

  return expired.length;
}

// =============================================================================
// RULE MANAGEMENT HELPERS
// =============================================================================

/**
 * Creates a new approval rule with defaults.
 *
 * @param name - Rule name
 * @param conditions - Rule conditions
 * @param action - Action to take when rule matches
 * @param options - Additional options
 * @returns The created rule
 */
export async function createRule(
  name: string,
  conditions: RuleCondition[],
  action: ApprovalAction,
  options: {
    description?: string;
    priority?: number;
    reason?: string;
    enabled?: boolean;
  } = {}
): Promise<ApprovalRule> {
  const existingRules = await store.getAllRules();
  const maxPriority = existingRules.reduce(
    (max, rule) => Math.max(max, rule.priority),
    0
  );

  const rule: ApprovalRule = {
    id: crypto.randomUUID(),
    name,
    description: options.description,
    priority: options.priority ?? maxPriority + 1,
    enabled: options.enabled ?? true,
    conditions,
    action,
    reason: options.reason,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };

  return store.createRule(rule);
}

/**
 * Creates default rules for common scenarios.
 * Should be called on first install.
 *
 * @returns Promise resolving when complete
 */
export async function createDefaultRules(): Promise<void> {
  const existingRules = await store.getAllRules();
  if (existingRules.length > 0) {
    // Don't overwrite existing rules
    return;
  }

  // Rule 1: Auto-reject critical risk actions
  await createRule(
    'Auto-reject critical risk',
    [{ field: 'riskLevel', operator: 'equals', value: 'critical' }],
    'auto_reject',
    {
      description: 'Automatically reject actions with critical risk level',
      priority: 100,
      reason: 'Action has critical risk level',
    }
  );

  // Rule 2: Auto-reject compromised memory
  await createRule(
    'Auto-reject compromised memory',
    [{ field: 'memoryCompromised', operator: 'equals', value: true }],
    'auto_reject',
    {
      description: 'Automatically reject actions when memory injection is detected',
      priority: 99,
      reason: 'Memory injection detected',
    }
  );

  // Rule 3: Auto-approve low risk from trusted MCP servers
  await createRule(
    'Auto-approve trusted MCP servers (low risk)',
    [
      { field: 'source', operator: 'equals', value: 'mcp_gateway' },
      { field: 'mcpServerTrusted', operator: 'equals', value: true },
      { field: 'riskLevel', operator: 'equals', value: 'low' },
    ],
    'auto_approve',
    {
      description: 'Automatically approve low-risk actions from trusted MCP servers',
      priority: 50,
      reason: 'Low risk action from trusted MCP server',
    }
  );

  // Rule 4: Require approval for high value transactions
  await createRule(
    'Require approval for high value',
    [
      { field: 'estimatedValueUsd', operator: 'greater_than', value: 100 },
    ],
    'require_approval',
    {
      description: 'Require manual approval for transactions over $100',
      priority: 80,
      reason: 'Transaction value exceeds $100',
    }
  );
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
  evaluateAction,
  processAction,
  decidePending,
  processExpiredApprovals,
  createRule,
  createDefaultRules,
};
