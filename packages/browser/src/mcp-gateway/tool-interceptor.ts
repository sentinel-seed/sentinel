/**
 * @fileoverview Tool Interceptor - Intercepts and validates MCP tool calls
 *
 * This module handles interception of MCP tool calls and routes them
 * through the approval system.
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  MCPToolCall,
  MCPServer,
  MCPTool,
  MCPClientSource,
  RiskLevel,
} from '../types';
import { validateTHSP } from '../lib/thsp';
import { processAction, EvaluationContext } from '../approval/approval-engine';
import { updateBadge, showApprovalNotification } from '../approval/approval-queue';
import * as registry from './server-registry';
import { validateTool } from './tool-validator';

// =============================================================================
// RISK CALCULATION
// =============================================================================

/** Risk score adjustments by tool category */
const TOOL_CATEGORY_RISK: Record<string, number> = {
  // High risk operations
  execute: 80,
  shell: 85,
  code: 75,
  write: 65,
  delete: 75,
  send: 70,

  // Medium risk operations
  read: 40,
  fetch: 45,
  list: 30,
  search: 35,

  // Low risk operations
  get: 20,
  info: 15,
  help: 10,
};

/**
 * Calculates the risk level for a tool call.
 *
 * @param tool - The tool being called
 * @param server - The server providing the tool
 * @param args - The call arguments
 * @returns The calculated risk level
 */
export function calculateToolRisk(
  tool: MCPTool,
  server: MCPServer,
  args: Record<string, unknown>
): RiskLevel {
  let riskScore = 0;

  // Base risk from tool's assigned risk level
  const riskLevelScore: Record<RiskLevel, number> = {
    low: 20,
    medium: 50,
    high: 75,
    critical: 95,
  };
  riskScore += riskLevelScore[tool.riskLevel];

  // Adjust for tool category
  const toolNameLower = tool.name.toLowerCase();
  for (const [category, score] of Object.entries(TOOL_CATEGORY_RISK)) {
    if (toolNameLower.includes(category)) {
      riskScore = Math.max(riskScore, score);
      break;
    }
  }

  // Adjust for server trust level (inverse relationship)
  const trustModifier = (100 - server.trustLevel) / 100;
  riskScore += trustModifier * 15;

  // Trusted servers get a bonus
  if (server.isTrusted) {
    riskScore -= 20;
  }

  // Check arguments for risky patterns
  const argsStr = JSON.stringify(args).toLowerCase();

  // Check for sensitive paths
  if (
    argsStr.includes('/etc/') ||
    argsStr.includes('/root/') ||
    argsStr.includes('system32') ||
    argsStr.includes('.ssh')
  ) {
    riskScore += 20;
  }

  // Check for network operations with external hosts
  if (argsStr.includes('http://') || argsStr.includes('https://')) {
    riskScore += 10;
  }

  // Check for potential code execution
  if (
    argsStr.includes('eval') ||
    argsStr.includes('exec') ||
    argsStr.includes('subprocess')
  ) {
    riskScore += 25;
  }

  // Clamp to 0-100
  riskScore = Math.max(0, Math.min(100, riskScore));

  // Convert score to level
  if (riskScore >= 85) {
    return 'critical';
  } else if (riskScore >= 65) {
    return 'high';
  } else if (riskScore >= 40) {
    return 'medium';
  }
  return 'low';
}

// =============================================================================
// TOOL CALL CREATION
// =============================================================================

/**
 * Creates an MCPToolCall object from raw call data.
 *
 * @param serverId - The ID of the server
 * @param toolName - The name of the tool
 * @param args - The call arguments
 * @param source - The client source
 * @returns Promise resolving to the created tool call
 */
export async function createToolCall(
  serverId: string,
  toolName: string,
  args: Record<string, unknown>,
  source: MCPClientSource
): Promise<MCPToolCall> {
  // Get server info
  const server = await registry.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  // Get tool info
  const tool = server.tools.find((t) => t.name === toolName);
  if (!tool) {
    throw new Error(`Tool ${toolName} not found on server ${serverId}`);
  }

  // Perform THSP validation on the call description
  const callDescription = `${server.name}/${toolName}: ${JSON.stringify(args)}`;
  const thspResult = validateTHSP(callDescription, {
    source: 'extension',
    platform: `mcp:${server.name}`,
    action: 'send',
  });

  // Calculate risk level
  const riskLevel = calculateToolRisk(tool, server, args);

  const toolCall: MCPToolCall = {
    id: crypto.randomUUID(),
    serverId,
    serverName: server.name,
    tool: toolName,
    arguments: args,
    source,
    thspResult,
    riskLevel,
    timestamp: Date.now(),
    status: 'pending',
  };

  return toolCall;
}

// =============================================================================
// INTERCEPTION
// =============================================================================

/**
 * Intercepts a tool call and processes it through the approval system.
 *
 * @param serverId - The ID of the server
 * @param toolName - The name of the tool
 * @param args - The call arguments
 * @param source - The client source
 * @param options - Additional options
 * @returns Promise resolving to the processed tool call with decision
 */
export async function interceptToolCall(
  serverId: string,
  toolName: string,
  args: Record<string, unknown>,
  source: MCPClientSource,
  options: {
    showNotification?: boolean;
    autoRejectTimeoutMs?: number;
  } = {}
): Promise<{
  toolCall: MCPToolCall;
  decision: 'approved' | 'rejected' | 'pending';
  reason?: string;
}> {
  // Get server info
  const server = await registry.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  // Create the tool call
  const toolCall = await createToolCall(serverId, toolName, args, source);

  // Get tool info
  const tool = server.tools.find((t) => t.name === toolName);

  // Validate the tool call
  const validation = await validateTool(toolName, args, server);
  if (!validation.safe) {
    // Immediately reject unsafe calls
    toolCall.status = 'rejected';
    toolCall.decision = {
      action: 'reject',
      method: 'auto',
      reason: validation.reason || 'Tool call failed validation',
      timestamp: Date.now(),
    };
    toolCall.error = validation.reason;

    await registry.recordRejectedCall(serverId);

    return {
      toolCall,
      decision: 'rejected',
      reason: validation.reason,
    };
  }

  // Check if tool requires approval
  if (tool && !tool.requiresApproval && server.isTrusted) {
    // Auto-approve trusted server calls that don't require approval
    toolCall.status = 'approved';
    toolCall.decision = {
      action: 'approve',
      method: 'auto',
      reason: 'Trusted server, no approval required',
      timestamp: Date.now(),
    };

    await registry.recordApprovedCall(serverId);

    return {
      toolCall,
      decision: 'approved',
      reason: 'Trusted server, no approval required',
    };
  }

  // Process through approval engine
  const context: EvaluationContext = {
    source: 'mcp_gateway',
    action: toolCall,
  };

  const result = await processAction(
    context,
    options.autoRejectTimeoutMs ?? 300000
  );

  if (result.decision) {
    // Auto-approved or auto-rejected
    toolCall.status = result.decision.action === 'approve' ? 'approved' : 'rejected';
    toolCall.decision = result.decision;

    if (result.decision.action === 'approve') {
      await registry.recordApprovedCall(serverId);
    } else {
      await registry.recordRejectedCall(serverId);
    }

    return {
      toolCall,
      decision: result.decision.action === 'approve' ? 'approved' : 'rejected',
      reason: result.decision.reason,
    };
  }

  // Requires manual approval
  toolCall.status = 'pending';
  await updateBadge();

  // Show notification if enabled
  if (options.showNotification !== false && result.pending) {
    await showApprovalNotification(result.pending, { show: true });
  }

  return {
    toolCall,
    decision: 'pending',
    reason: 'Manual approval required',
  };
}

// =============================================================================
// BATCH OPERATIONS
// =============================================================================

/**
 * Intercepts multiple tool calls at once.
 *
 * @param calls - Array of tool calls to intercept
 * @returns Promise resolving to array of results
 */
export async function interceptBatch(
  calls: Array<{
    serverId: string;
    toolName: string;
    args: Record<string, unknown>;
    source: MCPClientSource;
  }>
): Promise<
  Array<{
    toolCall: MCPToolCall;
    decision: 'approved' | 'rejected' | 'pending';
    reason?: string;
  }>
> {
  const results = [];

  for (const call of calls) {
    const result = await interceptToolCall(
      call.serverId,
      call.toolName,
      call.args,
      call.source,
      { showNotification: false }
    );
    results.push(result);
  }

  // Update badge once after all calls
  await updateBadge();

  return results;
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
  calculateToolRisk,
  createToolCall,
  interceptToolCall,
  interceptBatch,
};
