/**
 * @fileoverview Error Message component for inline error display
 *
 * Used to show validation errors, API errors, and other user-facing
 * error messages within the normal UI flow (not modal).
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';
import { t } from '../../../lib/i18n';

export type ErrorSeverity = 'error' | 'warning' | 'info';

interface ErrorMessageProps {
  /** Error message to display */
  message: string;
  /** Error severity affecting visual style */
  severity?: ErrorSeverity;
  /** Optional retry callback */
  onRetry?: () => void;
  /** Optional dismiss callback */
  onDismiss?: () => void;
  /** Whether to show as inline or block element */
  inline?: boolean;
  /** Optional custom icon */
  icon?: string;
  /** Additional CSS class name */
  className?: string;
}

/**
 * Inline error message component
 *
 * @example
 * ```tsx
 * {error && (
 *   <ErrorMessage
 *     message={error.message}
 *     severity="error"
 *     onRetry={handleRetry}
 *   />
 * )}
 * ```
 */
export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message,
  severity = 'error',
  onRetry,
  onDismiss,
  inline = false,
  icon,
  className,
}) => {
  const severityConfig = getSeverityConfig(severity);

  return (
    <div
      role="alert"
      aria-live={severity === 'error' ? 'assertive' : 'polite'}
      style={{
        ...styles.container,
        ...severityConfig.container,
        ...(inline ? styles.inline : styles.block),
      }}
      className={className}
    >
      <span style={styles.icon} aria-hidden="true">
        {icon || severityConfig.icon}
      </span>
      <span style={styles.message}>{message}</span>
      <div style={styles.actions}>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            style={{ ...styles.actionButton, ...severityConfig.actionButton }}
            aria-label={t('retry') || 'Retry'}
          >
            {t('retry') || 'Retry'}
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            style={styles.dismissButton}
            aria-label={t('dismiss') || 'Dismiss'}
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
};

interface SeverityConfig {
  icon: string;
  container: React.CSSProperties;
  actionButton: React.CSSProperties;
}

function getSeverityConfig(severity: ErrorSeverity): SeverityConfig {
  switch (severity) {
    case 'error':
      return {
        icon: '⚠️',
        container: {
          background: 'rgba(239, 68, 68, 0.1)',
          borderColor: 'rgba(239, 68, 68, 0.3)',
          color: '#ef4444',
        },
        actionButton: {
          color: '#ef4444',
          borderColor: 'rgba(239, 68, 68, 0.3)',
        },
      };
    case 'warning':
      return {
        icon: '⚡',
        container: {
          background: 'rgba(245, 158, 11, 0.1)',
          borderColor: 'rgba(245, 158, 11, 0.3)',
          color: '#f59e0b',
        },
        actionButton: {
          color: '#f59e0b',
          borderColor: 'rgba(245, 158, 11, 0.3)',
        },
      };
    case 'info':
    default:
      return {
        icon: 'ℹ️',
        container: {
          background: 'rgba(99, 102, 241, 0.1)',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          color: '#818cf8',
        },
        actionButton: {
          color: '#818cf8',
          borderColor: 'rgba(99, 102, 241, 0.3)',
        },
      };
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid',
    fontSize: 12,
    animation: 'fadeIn 0.2s ease-out',
  },
  inline: {
    display: 'inline-flex',
  },
  block: {
    width: '100%',
    marginBottom: 12,
  },
  icon: {
    fontSize: 14,
    flexShrink: 0,
  },
  message: {
    flex: 1,
    lineHeight: 1.4,
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    flexShrink: 0,
  },
  actionButton: {
    padding: '4px 10px',
    background: 'transparent',
    border: '1px solid',
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  dismissButton: {
    padding: 4,
    background: 'transparent',
    border: 'none',
    color: '#666',
    fontSize: 12,
    cursor: 'pointer',
    lineHeight: 1,
    borderRadius: 4,
  },
};

/**
 * Toast-style error notification
 * Shows temporarily and auto-dismisses
 */
interface ToastProps {
  message: string;
  severity?: ErrorSeverity;
  duration?: number;
  onDismiss: () => void;
}

export const Toast: React.FC<ToastProps> = ({
  message,
  severity = 'error',
  duration = 5000,
  onDismiss,
}) => {
  React.useEffect(() => {
    const timer = setTimeout(onDismiss, duration);
    return () => clearTimeout(timer);
  }, [duration, onDismiss]);

  const severityConfig = getSeverityConfig(severity);

  return (
    <div
      role="alert"
      aria-live="polite"
      style={{
        ...toastStyles.container,
        ...severityConfig.container,
      }}
    >
      <span style={toastStyles.icon} aria-hidden="true">
        {severityConfig.icon}
      </span>
      <span style={toastStyles.message}>{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        style={toastStyles.dismissButton}
        aria-label={t('dismiss') || 'Dismiss'}
      >
        ✕
      </button>
    </div>
  );
};

const toastStyles: Record<string, React.CSSProperties> = {
  container: {
    position: 'fixed',
    bottom: 16,
    left: 16,
    right: 16,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '12px 14px',
    borderRadius: 8,
    border: '1px solid',
    fontSize: 12,
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
    animation: 'slideUp 0.2s ease-out',
    zIndex: 1200,
  },
  icon: {
    fontSize: 14,
    flexShrink: 0,
  },
  message: {
    flex: 1,
    lineHeight: 1.4,
  },
  dismissButton: {
    padding: 4,
    background: 'transparent',
    border: 'none',
    color: 'inherit',
    opacity: 0.7,
    fontSize: 12,
    cursor: 'pointer',
    lineHeight: 1,
    borderRadius: 4,
  },
};

export default ErrorMessage;
