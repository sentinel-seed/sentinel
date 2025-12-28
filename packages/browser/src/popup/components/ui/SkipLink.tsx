/**
 * @fileoverview Skip link component for keyboard accessibility
 *
 * Provides a skip link that appears on focus, allowing keyboard users
 * to skip repetitive navigation and jump directly to main content.
 *
 * @author Sentinel Team
 * @license MIT
 */

import React from 'react';

interface SkipLinkProps {
  /** Target element ID to skip to */
  targetId: string;
  /** Link text (default: "Skip to main content") */
  children?: React.ReactNode;
}

const styles: Record<string, React.CSSProperties> = {
  skipLink: {
    position: 'absolute',
    left: '-10000px',
    top: 'auto',
    width: '1px',
    height: '1px',
    overflow: 'hidden',
    zIndex: 9999,
  },
  skipLinkFocused: {
    position: 'fixed',
    left: '50%',
    top: 8,
    transform: 'translateX(-50%)',
    width: 'auto',
    height: 'auto',
    overflow: 'visible',
    padding: '8px 16px',
    background: '#6366f1',
    color: '#ffffff',
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 600,
    textDecoration: 'none',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
  },
};

/**
 * SkipLink component
 *
 * Renders a link that is visually hidden until focused via keyboard.
 * When activated, it moves focus to the specified target element.
 */
export const SkipLink: React.FC<SkipLinkProps> = ({
  targetId,
  children = 'Skip to main content',
}) => {
  const [isFocused, setIsFocused] = React.useState(false);

  const handleClick = (e: React.MouseEvent | React.KeyboardEvent) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.setAttribute('tabindex', '-1');
      target.focus();
      target.removeAttribute('tabindex');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick(e);
    }
  };

  return (
    <a
      href={`#${targetId}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      style={isFocused ? styles.skipLinkFocused : styles.skipLink}
      className="skip-link"
    >
      {children}
    </a>
  );
};

export default SkipLink;
