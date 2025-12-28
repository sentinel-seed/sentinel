/**
 * @fileoverview Component exports for popup
 *
 * @author Sentinel Team
 * @license MIT
 */

// Main tab components
export { AgentsTab } from './AgentsTab';
export { MCPTab } from './MCPTab';
export { ApprovalModal } from './ApprovalModal';

// Shared styles
export { styles, agentStyles, mcpStyles, modalStyles } from './styles';

// UI components
export {
  ErrorBoundary,
  ConfirmDialog,
  ErrorMessage,
  Toast,
  Skeleton,
  SkeletonCircle,
  SkeletonText,
  SkeletonCard,
  SkeletonList,
  SkeletonTabs,
  SkeletonStatsGrid,
} from './ui';

export type { ConfirmDialogVariant, ErrorSeverity } from './ui';
