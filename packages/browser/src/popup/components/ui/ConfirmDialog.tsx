/**
 * @fileoverview Confirm Dialog component for destructive action confirmation
 *
 * Accessible modal dialog that prompts users to confirm or cancel
 * potentially destructive actions like disconnect or unregister.
 *
 * @author Sentinel Team
 * @license MIT
 */

import React, { useRef, useEffect } from 'react';
import { useFocusTrap, useAnnounce } from '../../hooks';
import { t } from '../../../lib/i18n';

export type ConfirmDialogVariant = 'danger' | 'warning' | 'info';

interface ConfirmDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Dialog title */
  title: string;
  /** Dialog message/description */
  message: string;
  /** Confirm button text */
  confirmText?: string;
  /** Cancel button text */
  cancelText?: string;
  /** Visual variant affecting button colors */
  variant?: ConfirmDialogVariant;
  /** Callback when confirmed */
  onConfirm: () => void;
  /** Callback when cancelled or closed */
  onCancel: () => void;
  /** Whether confirm action is loading */
  isLoading?: boolean;
  /** Optional icon to display */
  icon?: string;
}

/**
 * Accessible confirmation dialog component
 *
 * @example
 * ```tsx
 * <ConfirmDialog
 *   isOpen={showConfirm}
 *   title="Disconnect Agent"
 *   message="Are you sure you want to disconnect this agent?"
 *   variant="danger"
 *   onConfirm={handleDisconnect}
 *   onCancel={() => setShowConfirm(false)}
 * />
 * ```
 */
export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmText,
  cancelText,
  variant = 'danger',
  onConfirm,
  onCancel,
  isLoading = false,
  icon,
}) => {
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const announce = useAnnounce();

  const containerRef = useFocusTrap<HTMLDivElement>({
    isActive: isOpen,
    onEscape: onCancel,
    restoreFocus: true,
  });

  // Announce dialog to screen readers when opened
  useEffect(() => {
    if (isOpen) {
      announce(`${title}. ${message}`, 'assertive');
    }
  }, [isOpen, title, message, announce]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (!isLoading) {
      onConfirm();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Enter on confirm button
    if (e.key === 'Enter' && e.target === cancelButtonRef.current) {
      e.preventDefault();
      onCancel();
    }
  };

  const variantStyles = getVariantStyles(variant);

  return (
    <div
      style={styles.overlay}
      onClick={onCancel}
      role="presentation"
    >
      <div
        ref={containerRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        style={styles.dialog}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
        className="confirm-dialog-enter"
      >
        {/* Icon */}
        {icon && (
          <div style={styles.iconContainer} aria-hidden="true">
            <span style={{ ...styles.icon, ...variantStyles.icon }}>
              {icon}
            </span>
          </div>
        )}

        {/* Title */}
        <h2 id="confirm-dialog-title" style={styles.title}>
          {title}
        </h2>

        {/* Message */}
        <p id="confirm-dialog-description" style={styles.message}>
          {message}
        </p>

        {/* Actions */}
        <div style={styles.actions}>
          <button
            ref={cancelButtonRef}
            type="button"
            onClick={onCancel}
            style={styles.cancelButton}
            disabled={isLoading}
            aria-label={cancelText || t('cancel') || 'Cancel'}
          >
            {cancelText || t('cancel') || 'Cancel'}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            style={{ ...styles.confirmButton, ...variantStyles.confirmButton }}
            disabled={isLoading}
            aria-label={confirmText || t('confirm') || 'Confirm'}
            aria-busy={isLoading}
          >
            {isLoading ? (
              <span style={styles.loadingSpinner} aria-hidden="true">
                ⏳
              </span>
            ) : null}
            {confirmText || t('confirm') || 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
};

function getVariantStyles(variant: ConfirmDialogVariant): {
  icon: React.CSSProperties;
  confirmButton: React.CSSProperties;
} {
  switch (variant) {
    case 'danger':
      return {
        icon: { color: '#ef4444' },
        confirmButton: {
          background: 'linear-gradient(135deg, #ef4444, #dc2626)',
        },
      };
    case 'warning':
      return {
        icon: { color: '#f59e0b' },
        confirmButton: {
          background: 'linear-gradient(135deg, #f59e0b, #d97706)',
        },
      };
    case 'info':
    default:
      return {
        icon: { color: '#6366f1' },
        confirmButton: {
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        },
      };
  }
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1100,
    padding: 16,
    animation: 'fadeIn 0.15s ease-out',
  },
  dialog: {
    background: '#1a1a2e',
    borderRadius: 12,
    padding: 24,
    maxWidth: 340,
    width: '100%',
    textAlign: 'center',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
    animation: 'slideUp 0.2s ease-out',
  },
  iconContainer: {
    marginBottom: 16,
  },
  icon: {
    fontSize: 48,
    display: 'block',
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
    color: '#fff',
    margin: '0 0 8px 0',
  },
  message: {
    fontSize: 13,
    color: '#888',
    margin: '0 0 20px 0',
    lineHeight: 1.5,
  },
  actions: {
    display: 'flex',
    gap: 12,
    justifyContent: 'center',
  },
  cancelButton: {
    flex: 1,
    padding: '10px 16px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 8,
    color: '#888',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  confirmButton: {
    flex: 1,
    padding: '10px 16px',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  loadingSpinner: {
    animation: 'spin 1s linear infinite',
  },
};

export default ConfirmDialog;
