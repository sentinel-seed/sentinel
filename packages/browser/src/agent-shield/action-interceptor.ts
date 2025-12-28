/**
 * @fileoverview Action Interceptor - Intercepts and validates agent actions
 *
 * This module handles interception of actions from AI agents and routes them
 * through the approval system.
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  AgentAction,
  AgentActionType,
  AgentConnection,
  RiskLevel,
  MemoryContext,
} from '../types';
import { validateTHSP } from '../lib/thsp';
import { processAction, EvaluationContext } from '../approval/approval-engine';
import { updateBadge, showApprovalNotification } from '../approval/approval-queue';
import * as registry from './agent-registry';
import { scanMemory } from './memory-scanner';

// =============================================================================
// RISK CALCULATION
// =============================================================================

/** Base risk scores by action type */
const ACTION_TYPE_RISK: Record<AgentActionType, number> = {
  transfer: 70,
  swap: 60,
  approval: 80,
  sign: 50,
  execute: 75,
  deploy: 85,
  stake: 55,
  unstake: 45,
  bridge: 70,
  mint: 65,
  burn: 75,
  message: 20,
  api_call: 40,
  file_access: 60,
  mcp_tool: 50,
};

/** Risk level thresholds */
const RISK_THRESHOLDS = {
  low: 30,
  medium: 50,
  high: 70,
  critical: 85,
};

/**
 * Calculates the risk level for an action.
 *
 * @param action - The action to evaluate
 * @param agent - The agent that initiated the action
 * @param memoryContext - Memory context for the action
 * @returns The calculated risk level
 */
export function calculateRiskLevel(
  action: Partial<AgentAction>,
  agent: AgentConnection,
  memoryContext?: MemoryContext
): RiskLevel {
  let riskScore = 0;

  // Base risk from action type
  const actionType = action.type || 'execute';
  riskScore += ACTION_TYPE_RISK[actionType] || 50;

  // Adjust for agent trust level (inverse relationship)
  const trustModifier = (100 - agent.trustLevel) / 100;
  riskScore += trustModifier * 20;

  // Adjust for value (if available)
  if (action.estimatedValueUsd) {
    if (action.estimatedValueUsd > 1000) {
      riskScore += 20;
    } else if (action.estimatedValueUsd > 100) {
      riskScore += 10;
    } else if (action.estimatedValueUsd > 10) {
      riskScore += 5;
    }
  }

  // Significant penalty for memory compromise
  if (memoryContext?.isCompromised) {
    riskScore += 40;
  }

  // Adjust for suspicious entries
  if (memoryContext?.suspiciousEntries.length) {
    riskScore += memoryContext.suspiciousEntries.length * 5;
  }

  // Clamp to 0-100
  riskScore = Math.max(0, Math.min(100, riskScore));

  // Convert score to level
  if (riskScore >= RISK_THRESHOLDS.critical) {
    return 'critical';
  } else if (riskScore >= RISK_THRESHOLDS.high) {
    return 'high';
  } else if (riskScore >= RISK_THRESHOLDS.medium) {
    return 'medium';
  }
  return 'low';
}

// =============================================================================
// ACTION CREATION
// =============================================================================

/**
 * Creates an AgentAction object from raw action data.
 *
 * @param agentId - The ID of the agent
 * @param type - The type of action
 * @param description - Human-readable description
 * @param params - Action parameters
 * @param options - Additional options
 * @returns The created AgentAction
 */
export async function createAgentAction(
  agentId: string,
  type: AgentActionType,
  description: string,
  params: Record<string, unknown>,
  options: {
    estimatedValueUsd?: number;
    memoryEntries?: string[];
  } = {}
): Promise<AgentAction> {
  // Get agent info
  const agent = await registry.getAgentConnection(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  // Scan memory if entries provided
  let memoryContext: MemoryContext | undefined;
  if (options.memoryEntries) {
    memoryContext = await scanMemory(options.memoryEntries);
  }

  // Perform THSP validation
  const thspResult = validateTHSP(description, {
    source: 'extension',
    platform: `agent:${agent.type}`,
    action: 'send',
  });

  // Calculate risk level
  const riskLevel = calculateRiskLevel(
    { type, estimatedValueUsd: options.estimatedValueUsd },
    agent,
    memoryContext
  );

  const action: AgentAction = {
    id: crypto.randomUUID(),
    agentId,
    agentName: agent.name,
    type,
    description,
    params,
    thspResult,
    riskLevel,
    estimatedValueUsd: options.estimatedValueUsd,
    timestamp: Date.now(),
    status: 'pending',
    memoryContext,
  };

  return action;
}

// =============================================================================
// INTERCEPTION
// =============================================================================

/**
 * Intercepts an action from an agent and processes it through the approval system.
 *
 * @param agentId - The ID of the agent
 * @param type - The type of action
 * @param description - Human-readable description
 * @param params - Action parameters
 * @param options - Additional options
 * @returns Promise resolving to the processed action with decision
 */
export async function interceptAction(
  agentId: string,
  type: AgentActionType,
  description: string,
  params: Record<string, unknown>,
  options: {
    estimatedValueUsd?: number;
    memoryEntries?: string[];
    showNotification?: boolean;
    autoRejectTimeoutMs?: number;
  } = {}
): Promise<{
  action: AgentAction;
  decision: 'approved' | 'rejected' | 'pending';
  reason?: string;
}> {
  // Create the action
  const action = await createAgentAction(agentId, type, description, params, {
    estimatedValueUsd: options.estimatedValueUsd,
    memoryEntries: options.memoryEntries,
  });

  // Update agent stats
  await registry.incrementAgentStat(agentId, 'actionsTotal');

  // Check if memory is compromised
  if (action.memoryContext?.isCompromised) {
    // Immediately reject
    action.status = 'rejected';
    action.decision = {
      action: 'reject',
      method: 'auto',
      reason: 'Memory injection detected',
      timestamp: Date.now(),
    };

    await registry.recordRejectedAction(agentId, true);

    return {
      action,
      decision: 'rejected',
      reason: 'Memory injection detected',
    };
  }

  // Process through approval engine
  const context: EvaluationContext = {
    source: 'agent_shield',
    action,
  };

  const result = await processAction(
    context,
    options.autoRejectTimeoutMs ?? 300000
  );

  if (result.decision) {
    // Auto-approved or auto-rejected
    action.status = result.decision.action === 'approve' ? 'approved' : 'rejected';
    action.decision = result.decision;

    if (result.decision.action === 'approve') {
      await registry.recordApprovedAction(agentId);
    } else {
      await registry.recordRejectedAction(agentId, false);
    }

    return {
      action,
      decision: result.decision.action === 'approve' ? 'approved' : 'rejected',
      reason: result.decision.reason,
    };
  }

  // Requires manual approval
  action.status = 'pending';
  await registry.incrementAgentStat(agentId, 'actionsPending');
  await updateBadge();

  // Show notification if enabled
  if (options.showNotification !== false && result.pending) {
    await showApprovalNotification(result.pending, { show: true });
  }

  return {
    action,
    decision: 'pending',
    reason: 'Manual approval required',
  };
}

// =============================================================================
// BATCH OPERATIONS
// =============================================================================

/**
 * Intercepts multiple actions at once.
 *
 * @param agentId - The ID of the agent
 * @param actions - Array of actions to intercept
 * @returns Promise resolving to array of results
 */
export async function interceptBatch(
  agentId: string,
  actions: Array<{
    type: AgentActionType;
    description: string;
    params: Record<string, unknown>;
    estimatedValueUsd?: number;
  }>
): Promise<
  Array<{
    action: AgentAction;
    decision: 'approved' | 'rejected' | 'pending';
    reason?: string;
  }>
> {
  const results = [];

  for (const actionData of actions) {
    const result = await interceptAction(
      agentId,
      actionData.type,
      actionData.description,
      actionData.params,
      {
        estimatedValueUsd: actionData.estimatedValueUsd,
        showNotification: false, // Don't spam notifications for batch
      }
    );
    results.push(result);
  }

  // Update badge once after all actions
  await updateBadge();

  return results;
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
  calculateRiskLevel,
  createAgentAction,
  interceptAction,
  interceptBatch,
};
