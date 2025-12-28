/**
 * @fileoverview Formatting utility functions
 *
 * Shared formatting functions for dates, times, numbers, and text.
 *
 * @author Sentinel Team
 * @license MIT
 */

/**
 * Format a timestamp to a localized time string
 *
 * @param timestamp - Unix timestamp in milliseconds
 * @returns Formatted time string (e.g., "14:30")
 */
export function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format a timestamp to a localized date string
 *
 * @param timestamp - Unix timestamp in milliseconds
 * @returns Formatted date string (e.g., "Dec 28, 2025")
 */
export function formatDate(timestamp: number): string {
  return new Date(timestamp).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format a timestamp to a relative time string
 *
 * @param timestamp - Unix timestamp in milliseconds
 * @returns Relative time string (e.g., "2 minutes ago")
 */
export function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'Just now';
}

/**
 * Format remaining time until expiry
 *
 * @param expiresAt - Expiry timestamp in milliseconds
 * @returns Formatted remaining time (e.g., "2m 30s") or "Expired"
 */
export function formatTimeRemaining(expiresAt: number): string {
  const remaining = expiresAt - Date.now();

  if (remaining <= 0) return 'Expired';

  const minutes = Math.floor(remaining / 60000);
  const seconds = Math.floor((remaining % 60000) / 1000);

  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

/**
 * Format a USD value
 *
 * @param value - Value in USD
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted USD string (e.g., "$1,234.56")
 */
export function formatUSD(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a percentage value
 *
 * @param value - Value between 0 and 1
 * @returns Formatted percentage string (e.g., "85%")
 */
export function formatPercentage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/**
 * Truncate a string with ellipsis
 *
 * @param text - Text to truncate
 * @param maxLength - Maximum length before truncation
 * @returns Truncated text with ellipsis if needed
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
}

/**
 * Truncate an endpoint URL for display
 *
 * @param endpoint - Full endpoint URL
 * @param maxLength - Maximum length (default: 30)
 * @returns Truncated endpoint string
 */
export function truncateEndpoint(endpoint: string, maxLength = 30): string {
  return truncate(endpoint, maxLength);
}

/**
 * Format a number with compact notation
 *
 * @param value - Number to format
 * @returns Compact formatted number (e.g., "1.2K", "3.4M")
 */
export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
  }).format(value);
}
