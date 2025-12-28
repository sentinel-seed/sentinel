/**
 * @fileoverview Error Boundary component for graceful error handling
 *
 * Catches JavaScript errors in child component tree and displays
 * a fallback UI instead of crashing the entire application.
 *
 * @author Sentinel Team
 * @license MIT
 */

import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { t } from '../../../lib/i18n';

interface ErrorBoundaryProps {
  /** Child components to wrap */
  children: ReactNode;
  /** Optional custom fallback UI */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** Callback when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Component name for error reporting */
  componentName?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary component that catches errors in its children
 *
 * @example
 * ```tsx
 * <ErrorBoundary componentName="AgentsTab">
 *   <AgentsTab />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const { onError, componentName } = this.props;

    // Log error for debugging
    console.error(
      `[ErrorBoundary${componentName ? `:${componentName}` : ''}]`,
      error,
      errorInfo
    );

    // Call optional error handler
    if (onError) {
      onError(error, errorInfo);
    }
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    const { hasError, error } = this.state;
    const { children, fallback } = this.props;

    if (hasError && error) {
      // Use custom fallback if provided
      if (fallback) {
        if (typeof fallback === 'function') {
          return fallback(error, this.handleReset);
        }
        return fallback;
      }

      // Default fallback UI
      return <DefaultErrorFallback error={error} onReset={this.handleReset} />;
    }

    return children;
  }
}

/**
 * Default error fallback UI
 */
interface DefaultErrorFallbackProps {
  error: Error;
  onReset: () => void;
}

const DefaultErrorFallback: React.FC<DefaultErrorFallbackProps> = ({
  error,
  onReset,
}) => (
  <div
    role="alert"
    aria-live="assertive"
    style={styles.container}
  >
    <div style={styles.iconContainer}>
      <span style={styles.icon} aria-hidden="true">⚠️</span>
    </div>
    <h2 style={styles.title}>{t('errorOccurred') || 'Something went wrong'}</h2>
    <p style={styles.message}>
      {error.message || t('unexpectedError') || 'An unexpected error occurred'}
    </p>
    <div style={styles.actions}>
      <button
        onClick={onReset}
        style={styles.retryButton}
        aria-label={t('tryAgain') || 'Try again'}
      >
        {t('tryAgain') || 'Try Again'}
      </button>
    </div>
    {process.env.NODE_ENV === 'development' && (
      <details style={styles.details}>
        <summary style={styles.summary}>
          {t('errorDetails') || 'Error Details'}
        </summary>
        <pre style={styles.stack}>{error.stack}</pre>
      </details>
    )}
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    textAlign: 'center',
    minHeight: 200,
  },
  iconContainer: {
    marginBottom: 16,
  },
  icon: {
    fontSize: 48,
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
    color: '#ef4444',
    margin: '0 0 8px 0',
  },
  message: {
    fontSize: 13,
    color: '#888',
    margin: '0 0 16px 0',
    maxWidth: 280,
  },
  actions: {
    display: 'flex',
    gap: 8,
  },
  retryButton: {
    padding: '8px 16px',
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    border: 'none',
    borderRadius: 6,
    color: '#fff',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
  },
  details: {
    marginTop: 16,
    width: '100%',
    textAlign: 'left',
  },
  summary: {
    fontSize: 11,
    color: '#666',
    cursor: 'pointer',
    padding: 8,
  },
  stack: {
    fontSize: 10,
    color: '#888',
    background: 'rgba(0, 0, 0, 0.2)',
    padding: 12,
    borderRadius: 4,
    overflow: 'auto',
    maxHeight: 150,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
};

export default ErrorBoundary;
