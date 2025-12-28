/**
 * @fileoverview Skeleton Loader components for loading states
 *
 * Provides various skeleton shapes that animate while content loads,
 * preventing layout shift and improving perceived performance.
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';

interface SkeletonProps {
  /** Width of the skeleton (CSS value) */
  width?: string | number;
  /** Height of the skeleton (CSS value) */
  height?: string | number;
  /** Border radius (CSS value) */
  borderRadius?: string | number;
  /** Whether to animate the skeleton */
  animate?: boolean;
  /** Additional inline styles */
  style?: React.CSSProperties;
  /** Accessible label for screen readers */
  label?: string;
}

/**
 * Base skeleton component
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = 16,
  borderRadius = 4,
  animate = true,
  style,
  label = 'Loading...',
}) => (
  <div
    role="status"
    aria-label={label}
    style={{
      ...styles.base,
      width,
      height,
      borderRadius,
      ...(animate ? styles.animated : {}),
      ...style,
    }}
  >
    <span style={styles.srOnly}>{label}</span>
  </div>
);

/**
 * Circular skeleton (for avatars/icons)
 */
export const SkeletonCircle: React.FC<Omit<SkeletonProps, 'borderRadius'>> = ({
  width = 40,
  height,
  ...props
}) => (
  <Skeleton
    width={width}
    height={height || width}
    borderRadius="50%"
    {...props}
  />
);

/**
 * Text line skeleton
 */
export const SkeletonText: React.FC<{
  lines?: number;
  lineHeight?: number;
  gap?: number;
  lastLineWidth?: string;
  label?: string;
}> = ({
  lines = 3,
  lineHeight = 14,
  gap = 8,
  lastLineWidth = '70%',
  label = 'Loading text...',
}) => (
  <div role="status" aria-label={label}>
    <span style={styles.srOnly}>{label}</span>
    {Array.from({ length: lines }).map((_, index) => (
      <Skeleton
        key={index}
        height={lineHeight}
        width={index === lines - 1 ? lastLineWidth : '100%'}
        style={{ marginBottom: index < lines - 1 ? gap : 0 }}
        label=""
      />
    ))}
  </div>
);

/**
 * Card skeleton for agent/server cards
 */
export const SkeletonCard: React.FC<{
  showStats?: boolean;
  showActions?: boolean;
  label?: string;
}> = ({
  showStats = true,
  showActions = true,
  label = 'Loading card...',
}) => (
  <div
    role="status"
    aria-label={label}
    style={cardStyles.container}
  >
    <span style={styles.srOnly}>{label}</span>

    {/* Header */}
    <div style={cardStyles.header}>
      <div style={cardStyles.headerLeft}>
        <SkeletonCircle width={40} label="" />
        <div style={cardStyles.headerText}>
          <Skeleton width={120} height={14} label="" />
          <Skeleton width={80} height={10} style={{ marginTop: 6 }} label="" />
        </div>
      </div>
      <Skeleton width={60} height={24} borderRadius={4} label="" />
    </div>

    {/* Stats */}
    {showStats && (
      <div style={cardStyles.stats}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={cardStyles.stat}>
            <Skeleton width={50} height={10} label="" />
            <Skeleton width={30} height={16} style={{ marginTop: 4 }} label="" />
          </div>
        ))}
      </div>
    )}

    {/* Actions */}
    {showActions && (
      <div style={cardStyles.actions}>
        <Skeleton width={80} height={28} borderRadius={6} label="" />
      </div>
    )}
  </div>
);

/**
 * List skeleton for history/tools list
 */
export const SkeletonList: React.FC<{
  items?: number;
  itemHeight?: number;
  label?: string;
}> = ({
  items = 5,
  itemHeight = 48,
  label = 'Loading list...',
}) => (
  <div role="status" aria-label={label}>
    <span style={styles.srOnly}>{label}</span>
    {Array.from({ length: items }).map((_, index) => (
      <div key={index} style={{ ...listStyles.item, height: itemHeight }}>
        <SkeletonCircle width={28} label="" />
        <div style={listStyles.content}>
          <Skeleton width="60%" height={12} label="" />
          <Skeleton width="40%" height={10} style={{ marginTop: 6 }} label="" />
        </div>
        <Skeleton width={40} height={10} label="" />
      </div>
    ))}
  </div>
);

/**
 * Tab navigation skeleton
 */
export const SkeletonTabs: React.FC<{
  tabs?: number;
  label?: string;
}> = ({
  tabs = 3,
  label = 'Loading navigation...',
}) => (
  <div role="status" aria-label={label} style={tabStyles.container}>
    <span style={styles.srOnly}>{label}</span>
    {Array.from({ length: tabs }).map((_, index) => (
      <Skeleton
        key={index}
        width={80}
        height={32}
        borderRadius={6}
        label=""
      />
    ))}
  </div>
);

/**
 * Stats grid skeleton
 */
export const SkeletonStatsGrid: React.FC<{
  items?: number;
  label?: string;
}> = ({
  items = 3,
  label = 'Loading statistics...',
}) => (
  <div role="status" aria-label={label} style={statsStyles.grid}>
    <span style={styles.srOnly}>{label}</span>
    {Array.from({ length: items }).map((_, index) => (
      <div key={index} style={statsStyles.item}>
        <SkeletonCircle width={32} label="" />
        <Skeleton width={40} height={20} style={{ marginTop: 6 }} label="" />
        <Skeleton width={60} height={10} style={{ marginTop: 4 }} label="" />
      </div>
    ))}
  </div>
);

// Base styles
const styles: Record<string, React.CSSProperties> = {
  base: {
    background: 'rgba(255, 255, 255, 0.05)',
    display: 'block',
  },
  animated: {
    background: 'linear-gradient(90deg, rgba(255, 255, 255, 0.05) 25%, rgba(255, 255, 255, 0.1) 50%, rgba(255, 255, 255, 0.05) 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s infinite linear',
  },
  srOnly: {
    position: 'absolute',
    width: 1,
    height: 1,
    padding: 0,
    margin: -1,
    overflow: 'hidden',
    clip: 'rect(0, 0, 0, 0)',
    whiteSpace: 'nowrap',
    border: 0,
  },
};

// Card skeleton styles
const cardStyles: Record<string, React.CSSProperties> = {
  container: {
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    marginBottom: 8,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  headerText: {
    display: 'flex',
    flexDirection: 'column',
  },
  stats: {
    display: 'flex',
    gap: 16,
    padding: '8px 0',
    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    marginBottom: 8,
  },
  stat: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
  },
};

// List skeleton styles
const listStyles: Record<string, React.CSSProperties> = {
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: 10,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 6,
    marginBottom: 6,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  content: {
    flex: 1,
  },
};

// Tab skeleton styles
const tabStyles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    gap: 4,
    marginBottom: 16,
    paddingBottom: 8,
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
  },
};

// Stats grid skeleton styles
const statsStyles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 8,
    marginBottom: 20,
  },
  item: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 12,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
};

export default Skeleton;
