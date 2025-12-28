/**
 * @fileoverview Unit tests for useAccessibility hooks
 *
 * Tests:
 * - useAccessibilityPreferences
 * - useAnnouncer
 * - useRovingTabindex
 * - useKeyboardNavigation
 *
 * @author Sentinel Team
 * @license MIT
 */

import { renderHook, act } from '@testing-library/react';
import {
  useAccessibilityPreferences,
  useAnnouncer,
  useRovingTabindex,
  useKeyboardNavigation,
} from '../useAccessibility';

// Mock matchMedia
const createMatchMediaMock = (matches: boolean) => {
  return jest.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }));
};

describe('useAccessibility hooks', () => {
  const originalMatchMedia = window.matchMedia;

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  describe('useAccessibilityPreferences', () => {
    it('should detect when user prefers reduced motion', () => {
      window.matchMedia = createMatchMediaMock(true);

      const { result } = renderHook(() => useAccessibilityPreferences());

      expect(result.current.prefersReducedMotion).toBe(true);
    });

    it('should detect when user does not prefer reduced motion', () => {
      window.matchMedia = createMatchMediaMock(false);

      const { result } = renderHook(() => useAccessibilityPreferences());

      expect(result.current.prefersReducedMotion).toBe(false);
    });

    it('should return preferences object with correct shape', () => {
      window.matchMedia = createMatchMediaMock(false);

      const { result } = renderHook(() => useAccessibilityPreferences());

      expect(result.current).toHaveProperty('prefersReducedMotion');
      expect(result.current).toHaveProperty('prefersHighContrast');
    });
  });

  describe('useAnnouncer', () => {
    beforeEach(() => {
      // Clean up any existing live regions
      document.querySelectorAll('[aria-live]').forEach((el) => el.remove());
    });

    afterEach(() => {
      // Clean up live regions
      document.querySelectorAll('[aria-live]').forEach((el) => el.remove());
    });

    it('should create live regions on mount', () => {
      renderHook(() => useAnnouncer());

      // Wait for effect to run
      const politeRegion = document.querySelector('[aria-live="polite"]');
      const assertiveRegion = document.querySelector('[aria-live="assertive"]');

      expect(politeRegion).toBeTruthy();
      expect(assertiveRegion).toBeTruthy();
    });

    it('should return announce function', () => {
      const { result } = renderHook(() => useAnnouncer());

      expect(typeof result.current.announce).toBe('function');
    });

    it('should announce message to polite region by default', async () => {
      const { result } = renderHook(() => useAnnouncer());

      act(() => {
        result.current.announce('Test message');
      });

      // Wait for setTimeout in announce
      await new Promise((resolve) => setTimeout(resolve, 100));

      const politeRegion = document.querySelector('[aria-live="polite"]');
      expect(politeRegion?.textContent).toBe('Test message');
    });

    it('should announce message to assertive region when specified', async () => {
      const { result } = renderHook(() => useAnnouncer());

      act(() => {
        result.current.announce('Urgent message', 'assertive');
      });

      // Wait for setTimeout in announce
      await new Promise((resolve) => setTimeout(resolve, 100));

      const assertiveRegion = document.querySelector('[aria-live="assertive"]');
      expect(assertiveRegion?.textContent).toBe('Urgent message');
    });

    it('should clean up live regions on unmount', () => {
      const { unmount } = renderHook(() => useAnnouncer());

      unmount();

      // Regions should be removed
      const regions = document.querySelectorAll('[aria-live]');
      expect(regions.length).toBe(0);
    });
  });

  describe('useRovingTabindex', () => {
    it('should initialize with activeIndex 0', () => {
      const { result } = renderHook(() => useRovingTabindex(5));

      expect(result.current.activeIndex).toBe(0);
    });

    it('should return getItemProps function', () => {
      const { result } = renderHook(() => useRovingTabindex(5));

      expect(typeof result.current.getItemProps).toBe('function');
    });

    it('should return correct tabIndex for active item', () => {
      const { result } = renderHook(() => useRovingTabindex(5));

      const props0 = result.current.getItemProps(0);
      const props1 = result.current.getItemProps(1);

      expect(props0.tabIndex).toBe(0);
      expect(props1.tabIndex).toBe(-1);
    });

    it('should update activeIndex via setActiveIndex', () => {
      const { result } = renderHook(() => useRovingTabindex(5));

      act(() => {
        result.current.setActiveIndex(3);
      });

      expect(result.current.activeIndex).toBe(3);
    });

    it('should handle ArrowDown key for vertical orientation', () => {
      const { result } = renderHook(() => useRovingTabindex(3, 'vertical'));

      const props = result.current.getItemProps(0);
      const event = {
        key: 'ArrowDown',
        preventDefault: jest.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        props.onKeyDown(event);
      });

      expect(event.preventDefault).toHaveBeenCalled();
      expect(result.current.activeIndex).toBe(1);
    });

    it('should handle ArrowUp key for vertical orientation', () => {
      const { result } = renderHook(() => useRovingTabindex(3, 'vertical'));

      // Set to index 1 first
      act(() => {
        result.current.setActiveIndex(1);
      });

      const props = result.current.getItemProps(1);
      const event = {
        key: 'ArrowUp',
        preventDefault: jest.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        props.onKeyDown(event);
      });

      expect(result.current.activeIndex).toBe(0);
    });

    it('should wrap around at boundaries', () => {
      const { result } = renderHook(() => useRovingTabindex(3, 'vertical'));

      // At first item, pressing up should go to last
      const props = result.current.getItemProps(0);
      const event = {
        key: 'ArrowUp',
        preventDefault: jest.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        props.onKeyDown(event);
      });

      expect(result.current.activeIndex).toBe(2);
    });

    it('should handle Home key', () => {
      const { result } = renderHook(() => useRovingTabindex(5));

      act(() => {
        result.current.setActiveIndex(3);
      });

      const props = result.current.getItemProps(3);
      const event = {
        key: 'Home',
        preventDefault: jest.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        props.onKeyDown(event);
      });

      expect(result.current.activeIndex).toBe(0);
    });

    it('should handle End key', () => {
      const { result } = renderHook(() => useRovingTabindex(5));

      const props = result.current.getItemProps(0);
      const event = {
        key: 'End',
        preventDefault: jest.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        props.onKeyDown(event);
      });

      expect(result.current.activeIndex).toBe(4);
    });

    it('should handle horizontal orientation with ArrowLeft/Right', () => {
      const { result } = renderHook(() => useRovingTabindex(3, 'horizontal'));

      const props = result.current.getItemProps(0);

      // ArrowRight should move forward
      const rightEvent = {
        key: 'ArrowRight',
        preventDefault: jest.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        props.onKeyDown(rightEvent);
      });

      expect(result.current.activeIndex).toBe(1);

      // ArrowLeft should move back
      const leftEvent = {
        key: 'ArrowLeft',
        preventDefault: jest.fn(),
      } as unknown as React.KeyboardEvent;

      const props1 = result.current.getItemProps(1);
      act(() => {
        props1.onKeyDown(leftEvent);
      });

      expect(result.current.activeIndex).toBe(0);
    });
  });

  describe('useKeyboardNavigation', () => {
    it('should initialize as false (not keyboard user)', () => {
      const { result } = renderHook(() => useKeyboardNavigation());

      expect(result.current).toBe(false);
    });

    it('should detect keyboard navigation on Tab key', () => {
      const { result } = renderHook(() => useKeyboardNavigation());

      act(() => {
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
      });

      expect(result.current).toBe(true);
    });

    it('should reset on mouse click', () => {
      const { result } = renderHook(() => useKeyboardNavigation());

      // First, simulate Tab
      act(() => {
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
      });

      expect(result.current).toBe(true);

      // Then, simulate mouse click
      act(() => {
        window.dispatchEvent(new MouseEvent('mousedown'));
      });

      expect(result.current).toBe(false);
    });

    it('should clean up event listeners on unmount', () => {
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

      const { unmount } = renderHook(() => useKeyboardNavigation());

      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });
});
