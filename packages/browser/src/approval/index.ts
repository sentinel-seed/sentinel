/**
 * @fileoverview Approval Module - Entry point
 *
 * This module provides the approval system for the Sentinel Guard extension.
 * It handles rule-based approval decisions for agent actions and MCP tool calls.
 *
 * @author Sentinel Team
 * @license MIT
 */

// Re-export all types
export type {
  ApprovalRule,
  ApprovalAction,
  ApprovalDecision,
  RuleCondition,
  RuleConditionField,
  RuleConditionOperator,
  PendingApproval,
  ActionHistoryEntry,
} from '../types';

// Export store functions
export * as store from './approval-store';

// Export engine functions
export * as engine from './approval-engine';

// Export queue functions
export * as queue from './approval-queue';

// Re-export commonly used functions at top level
export {
  getDatabase,
  closeDatabase,
  getAllRules,
  getEnabledRules,
  getRule,
  createRule as storeCreateRule,
  updateRule,
  deleteRule,
  getPendingApprovals,
  getPendingApproval,
  addPendingApproval,
  removePendingApproval,
  getActionHistory,
  addHistoryEntry,
  clearActionHistory,
} from './approval-store';

export {
  evaluateAction,
  processAction,
  decidePending,
  processExpiredApprovals,
  createRule,
  createDefaultRules,
} from './approval-engine';

export type { EvaluationContext, EvaluationResult } from './approval-engine';
