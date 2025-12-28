/**
 * @fileoverview Accessibility hook for managing a11y features
 *
 * Provides:
 * - Screen reader announcements
 * - Reduced motion detection
 * - High contrast detection
 * - Keyboard navigation helpers
 *
 * @author Sentinel Team
 * @license MIT
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/** Announcement priority levels */
export type AnnouncementPriority = 'polite' | 'assertive';

/** Accessibility preferences state */
export interface AccessibilityPreferences {
  prefersReducedMotion: boolean;
  prefersHighContrast: boolean;
}

/**
 * Hook to detect user accessibility preferences
 */
export function useAccessibilityPreferences(): AccessibilityPreferences {
  const [preferences, setPreferences] = useState<AccessibilityPreferences>({
    prefersReducedMotion: false,
    prefersHighContrast: false,
  });

  useEffect(() => {
    // Check reduced motion preference
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const contrastQuery = window.matchMedia('(prefers-contrast: more)');

    const updatePreferences = () => {
      setPreferences({
        prefersReducedMotion: motionQuery.matches,
        prefersHighContrast: contrastQuery.matches,
      });
    };

    // Initial check
    updatePreferences();

    // Listen for changes
    motionQuery.addEventListener('change', updatePreferences);
    contrastQuery.addEventListener('change', updatePreferences);

    return () => {
      motionQuery.removeEventListener('change', updatePreferences);
      contrastQuery.removeEventListener('change', updatePreferences);
    };
  }, []);

  return preferences;
}

/**
 * Hook for screen reader announcements using aria-live regions
 */
export function useAnnouncer() {
  const politeRef = useRef<HTMLDivElement | null>(null);
  const assertiveRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Create live regions if they don't exist
    if (!politeRef.current) {
      politeRef.current = createLiveRegion('polite');
    }
    if (!assertiveRef.current) {
      assertiveRef.current = createLiveRegion('assertive');
    }

    return () => {
      politeRef.current?.remove();
      assertiveRef.current?.remove();
    };
  }, []);

  const announce = useCallback(
    (message: string, priority: AnnouncementPriority = 'polite') => {
      const region = priority === 'assertive' ? assertiveRef.current : politeRef.current;
      if (region) {
        // Clear and set to trigger announcement
        region.textContent = '';
        // Use setTimeout to ensure the clear is processed first
        setTimeout(() => {
          region.textContent = message;
        }, 50);
      }
    },
    []
  );

  return { announce };
}

/**
 * Create an aria-live region element
 */
function createLiveRegion(priority: AnnouncementPriority): HTMLDivElement {
  const region = document.createElement('div');
  region.setAttribute('aria-live', priority);
  region.setAttribute('aria-atomic', 'true');
  region.setAttribute('role', 'status');
  region.className = 'live-region';
  region.style.cssText = `
    position: absolute;
    left: -10000px;
    width: 1px;
    height: 1px;
    overflow: hidden;
  `;
  document.body.appendChild(region);
  return region;
}

/**
 * Hook for roving tabindex navigation in lists
 */
export function useRovingTabindex<T extends HTMLElement>(
  itemCount: number,
  orientation: 'horizontal' | 'vertical' = 'vertical'
) {
  const [activeIndex, setActiveIndex] = useState(0);
  const itemRefs = useRef<(T | null)[]>([]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      const prevKey = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft';
      const nextKey = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight';

      let newIndex = activeIndex;

      switch (event.key) {
        case prevKey:
          event.preventDefault();
          newIndex = activeIndex > 0 ? activeIndex - 1 : itemCount - 1;
          break;
        case nextKey:
          event.preventDefault();
          newIndex = activeIndex < itemCount - 1 ? activeIndex + 1 : 0;
          break;
        case 'Home':
          event.preventDefault();
          newIndex = 0;
          break;
        case 'End':
          event.preventDefault();
          newIndex = itemCount - 1;
          break;
        default:
          return;
      }

      setActiveIndex(newIndex);
      itemRefs.current[newIndex]?.focus();
    },
    [activeIndex, itemCount, orientation]
  );

  const getItemProps = useCallback(
    (index: number) => ({
      ref: (el: T | null) => {
        itemRefs.current[index] = el;
      },
      tabIndex: index === activeIndex ? 0 : -1,
      onKeyDown: handleKeyDown,
      onFocus: () => setActiveIndex(index),
    }),
    [activeIndex, handleKeyDown]
  );

  return { activeIndex, setActiveIndex, getItemProps };
}

/**
 * Hook to manage skip link functionality
 */
export function useSkipLink(targetId: string) {
  const skipToContent = useCallback(() => {
    const target = document.getElementById(targetId);
    if (target) {
      target.focus();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  }, [targetId]);

  return { skipToContent };
}

/**
 * Hook to detect if user is using keyboard navigation
 */
export function useKeyboardNavigation() {
  const [isKeyboardUser, setIsKeyboardUser] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        setIsKeyboardUser(true);
      }
    };

    const handleMouseDown = () => {
      setIsKeyboardUser(false);
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('mousedown', handleMouseDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('mousedown', handleMouseDown);
    };
  }, []);

  return isKeyboardUser;
}
