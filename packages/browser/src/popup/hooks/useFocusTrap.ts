/**
 * @fileoverview Custom hook for trapping focus within a container
 *
 * Essential for modal accessibility - ensures keyboard navigation
 * stays within the modal while it's open.
 *
 * @author Sentinel Team
 * @license MIT
 */

import { useEffect, useRef, useCallback } from 'react';

/** Selector for focusable elements */
const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'a[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

interface UseFocusTrapOptions {
  /** Whether the focus trap is active */
  isActive: boolean;
  /** Callback when escape key is pressed */
  onEscape?: () => void;
  /** Whether to restore focus when trap is deactivated */
  restoreFocus?: boolean;
  /** Initial element to focus (selector or ref) */
  initialFocus?: string | React.RefObject<HTMLElement>;
}

/**
 * Hook to trap focus within a container element
 *
 * @param options - Focus trap configuration
 * @returns Ref to attach to the container element
 *
 * @example
 * ```tsx
 * const containerRef = useFocusTrap({
 *   isActive: isOpen,
 *   onEscape: handleClose,
 *   restoreFocus: true,
 * });
 *
 * return <div ref={containerRef}>...</div>;
 * ```
 */
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(
  options: UseFocusTrapOptions
): React.RefObject<T> {
  const { isActive, onEscape, restoreFocus = true, initialFocus } = options;

  const containerRef = useRef<T>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  // Get all focusable elements within container
  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!containerRef.current) return [];
    return Array.from(
      containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
    ).filter((el) => {
      // Filter out hidden elements
      return el.offsetParent !== null;
    });
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!isActive) return;

      // Handle Escape key
      if (event.key === 'Escape' && onEscape) {
        event.preventDefault();
        event.stopPropagation();
        onEscape();
        return;
      }

      // Handle Tab key for focus trapping
      if (event.key === 'Tab') {
        const focusableElements = getFocusableElements();
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        // Shift+Tab on first element -> go to last
        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
          return;
        }

        // Tab on last element -> go to first
        if (!event.shiftKey && document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
          return;
        }

        // If focus is outside container, bring it back
        if (
          containerRef.current &&
          !containerRef.current.contains(document.activeElement)
        ) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    },
    [isActive, onEscape, getFocusableElements]
  );

  // Set up focus trap
  useEffect(() => {
    if (!isActive) return;

    // Store currently focused element
    previouslyFocusedRef.current = document.activeElement as HTMLElement;

    // Add keyboard event listener
    document.addEventListener('keydown', handleKeyDown);

    // Set initial focus
    const setInitialFocus = () => {
      if (initialFocus) {
        if (typeof initialFocus === 'string') {
          const element = containerRef.current?.querySelector<HTMLElement>(
            initialFocus
          );
          if (element) {
            element.focus();
            return;
          }
        } else if (initialFocus.current) {
          initialFocus.current.focus();
          return;
        }
      }

      // Default: focus first focusable element
      const focusableElements = getFocusableElements();
      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      } else if (containerRef.current) {
        // If no focusable elements, make container focusable
        containerRef.current.setAttribute('tabindex', '-1');
        containerRef.current.focus();
      }
    };

    // Delay focus to ensure DOM is ready
    requestAnimationFrame(setInitialFocus);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);

      // Restore focus to previously focused element
      if (restoreFocus && previouslyFocusedRef.current) {
        try {
          previouslyFocusedRef.current.focus();
        } catch {
          // Element may have been removed from DOM
        }
      }
    };
  }, [isActive, handleKeyDown, getFocusableElements, initialFocus, restoreFocus]);

  return containerRef;
}

/**
 * Hook to announce content to screen readers
 *
 * @param message - Message to announce
 * @param priority - 'polite' for non-urgent, 'assertive' for urgent
 */
export function useAnnounce(): (
  message: string,
  priority?: 'polite' | 'assertive'
) => void {
  const announce = useCallback(
    (message: string, priority: 'polite' | 'assertive' = 'polite') => {
      const announcer = document.createElement('div');
      announcer.setAttribute('aria-live', priority);
      announcer.setAttribute('aria-atomic', 'true');
      announcer.setAttribute(
        'style',
        'position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;'
      );
      document.body.appendChild(announcer);

      // Delay to ensure screen reader picks up the change
      requestAnimationFrame(() => {
        announcer.textContent = message;

        // Clean up after announcement
        setTimeout(() => {
          document.body.removeChild(announcer);
        }, 1000);
      });
    },
    []
  );

  return announce;
}

export default useFocusTrap;
