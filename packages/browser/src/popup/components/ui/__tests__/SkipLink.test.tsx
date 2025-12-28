/**
 * @fileoverview Unit tests for SkipLink component
 *
 * Tests skip link accessibility functionality:
 * - Visibility on focus
 * - Target navigation
 * - Keyboard activation
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SkipLink } from '../SkipLink';

describe('SkipLink', () => {
  beforeEach(() => {
    // Create target element for skip link
    const target = document.createElement('div');
    target.id = 'main-content';
    document.body.appendChild(target);
  });

  afterEach(() => {
    // Clean up
    const target = document.getElementById('main-content');
    if (target) {
      document.body.removeChild(target);
    }
  });

  describe('rendering', () => {
    it('should render with default text', () => {
      render(<SkipLink targetId="main-content" />);

      const link = screen.getByText('Skip to main content');
      expect(link).toBeInTheDocument();
    });

    it('should render with custom text', () => {
      render(<SkipLink targetId="main-content">Skip navigation</SkipLink>);

      const link = screen.getByText('Skip navigation');
      expect(link).toBeInTheDocument();
    });

    it('should have correct href attribute', () => {
      render(<SkipLink targetId="main-content" />);

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', '#main-content');
    });

    it('should have skip-link class', () => {
      render(<SkipLink targetId="main-content" />);

      const link = screen.getByRole('link');
      expect(link).toHaveClass('skip-link');
    });
  });

  describe('visibility', () => {
    it('should be visually hidden by default', () => {
      render(<SkipLink targetId="main-content" />);

      const link = screen.getByRole('link');
      // Check for off-screen positioning
      expect(link).toHaveStyle({ position: 'absolute' });
      expect(link).toHaveStyle({ left: '-10000px' });
    });

    it('should become visible on focus', () => {
      render(<SkipLink targetId="main-content" />);

      const link = screen.getByRole('link');

      fireEvent.focus(link);

      // Should now be visible (fixed positioning)
      expect(link).toHaveStyle({ position: 'fixed' });
    });

    it('should hide again on blur', () => {
      render(<SkipLink targetId="main-content" />);

      const link = screen.getByRole('link');

      fireEvent.focus(link);
      fireEvent.blur(link);

      // Should be hidden again
      expect(link).toHaveStyle({ position: 'absolute' });
      expect(link).toHaveStyle({ left: '-10000px' });
    });
  });

  describe('navigation', () => {
    it('should focus target element on click', () => {
      render(<SkipLink targetId="main-content" />);

      const target = document.getElementById('main-content');
      const focusSpy = jest.spyOn(target!, 'focus');

      const link = screen.getByRole('link');
      fireEvent.click(link);

      expect(focusSpy).toHaveBeenCalled();
      focusSpy.mockRestore();
    });

    it('should prevent default link behavior on click', () => {
      render(<SkipLink targetId="main-content" />);

      const link = screen.getByRole('link');

      const event = new MouseEvent('click', { bubbles: true, cancelable: true });
      const preventDefaultSpy = jest.spyOn(event, 'preventDefault');

      link.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('should focus target on Enter key', () => {
      render(<SkipLink targetId="main-content" />);

      const target = document.getElementById('main-content');
      const focusSpy = jest.spyOn(target!, 'focus');

      const link = screen.getByRole('link');
      fireEvent.keyDown(link, { key: 'Enter' });

      expect(focusSpy).toHaveBeenCalled();
      focusSpy.mockRestore();
    });

    it('should focus target on Space key', () => {
      render(<SkipLink targetId="main-content" />);

      const target = document.getElementById('main-content');
      const focusSpy = jest.spyOn(target!, 'focus');

      const link = screen.getByRole('link');
      fireEvent.keyDown(link, { key: ' ' });

      expect(focusSpy).toHaveBeenCalled();
      focusSpy.mockRestore();
    });

    it('should not activate on other keys', () => {
      render(<SkipLink targetId="main-content" />);

      const target = document.getElementById('main-content');
      const focusSpy = jest.spyOn(target!, 'focus');

      const link = screen.getByRole('link');
      fireEvent.keyDown(link, { key: 'Tab' });

      expect(focusSpy).not.toHaveBeenCalled();
      focusSpy.mockRestore();
    });

    it('should handle missing target gracefully', () => {
      // Remove target
      const target = document.getElementById('main-content');
      if (target) {
        document.body.removeChild(target);
      }

      render(<SkipLink targetId="nonexistent" />);

      const link = screen.getByRole('link');

      // Should not throw
      expect(() => {
        fireEvent.click(link);
      }).not.toThrow();
    });
  });

  describe('accessibility', () => {
    it('should be focusable', () => {
      render(<SkipLink targetId="main-content" />);

      const link = screen.getByRole('link');
      link.focus();

      expect(document.activeElement).toBe(link);
    });

    it('should set tabindex on target temporarily', () => {
      render(<SkipLink targetId="main-content" />);

      const target = document.getElementById('main-content');
      const setAttributeSpy = jest.spyOn(target!, 'setAttribute');
      const removeAttributeSpy = jest.spyOn(target!, 'removeAttribute');

      const link = screen.getByRole('link');
      fireEvent.click(link);

      expect(setAttributeSpy).toHaveBeenCalledWith('tabindex', '-1');
      expect(removeAttributeSpy).toHaveBeenCalledWith('tabindex');

      setAttributeSpy.mockRestore();
      removeAttributeSpy.mockRestore();
    });
  });
});
