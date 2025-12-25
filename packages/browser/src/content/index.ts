/**
 * Sentinel Guard - Content Script
 *
 * Injected into AI chat platforms to:
 * - Protect conversations from other extensions
 * - Scan input for sensitive data
 * - Detect and block threats
 */

import { scanAll, maskSensitiveData, PatternMatch } from '../lib/patterns';

/**
 * Escape HTML to prevent XSS attacks
 * C001: Critical security fix
 */
function escapeHtml(text: string): string {
  if (!text || typeof text !== 'string') return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Create an HTML element safely without innerHTML
 */
function createSafeElement(tag: string, className?: string, textContent?: string): HTMLElement {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (textContent) element.textContent = textContent;
  return element;
}

// Platform detection
function detectPlatform(): string {
  const hostname = window.location.hostname;

  if (hostname.includes('chat.openai.com') || hostname.includes('chatgpt.com')) {
    return 'chatgpt';
  }
  if (hostname.includes('claude.ai')) {
    return 'claude';
  }
  if (hostname.includes('gemini.google.com')) {
    return 'gemini';
  }
  if (hostname.includes('perplexity.ai')) {
    return 'perplexity';
  }
  if (hostname.includes('deepseek.com')) {
    return 'deepseek';
  }
  if (hostname.includes('grok.x.ai')) {
    return 'grok';
  }
  if (hostname.includes('copilot.microsoft.com')) {
    return 'copilot';
  }
  if (hostname.includes('meta.ai')) {
    return 'meta';
  }

  return 'unknown';
}

// Input selectors for each platform
const INPUT_SELECTORS: Record<string, string> = {
  chatgpt: 'textarea[data-id="root"], #prompt-textarea',
  claude: 'div[contenteditable="true"]',
  gemini: 'rich-textarea textarea',
  perplexity: 'textarea',
  deepseek: 'textarea',
  grok: 'textarea',
  copilot: 'textarea, [contenteditable="true"]',
  meta: 'textarea, [contenteditable="true"]',
  unknown: 'textarea, [contenteditable="true"]',
};

// Send button selectors
const SEND_SELECTORS: Record<string, string> = {
  chatgpt: 'button[data-testid="send-button"], button[aria-label*="Send"]',
  claude: 'button[aria-label*="Send"]',
  gemini: 'button[aria-label*="Send"]',
  perplexity: 'button[aria-label*="Submit"]',
  deepseek: 'button[type="submit"]',
  grok: 'button[type="submit"], button[aria-label*="Send"]',
  copilot: 'button[type="submit"], button[aria-label*="Send"]',
  meta: 'button[type="submit"], button[aria-label*="Send"]',
  unknown: 'button[type="submit"], button[aria-label*="Send"]',
};

const platform = detectPlatform();
let isEnabled = true;
let protectionLevel: 'basic' | 'recommended' | 'maximum' = 'recommended';

// Initialize
async function init() {
  console.log(`[Sentinel Guard] Initializing on ${platform}`);

  // Load settings
  const response = await chrome.runtime.sendMessage({ type: 'GET_SETTINGS' });
  if (response) {
    isEnabled = response.enabled;
    protectionLevel = response.protectionLevel;
  }

  if (!isEnabled) {
    console.log('[Sentinel Guard] Extension disabled');
    return;
  }

  // Setup protection
  setupInputProtection();
  setupConversationShield();

  // Report session start
  chrome.runtime.sendMessage({ type: 'INCREMENT_STAT', payload: 'sessionsProtected' });

  console.log('[Sentinel Guard] Protection active');
}

// Input protection - scan before sending
function setupInputProtection() {
  const inputSelector = INPUT_SELECTORS[platform] || INPUT_SELECTORS.unknown;

  // Use MutationObserver to catch dynamically loaded inputs
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node instanceof Element) {
          const inputs = node.matches(inputSelector)
            ? [node]
            : Array.from(node.querySelectorAll(inputSelector));

          for (const input of inputs) {
            attachInputListener(input as HTMLElement);
          }
        }
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // Also check existing inputs
  document.querySelectorAll(inputSelector).forEach((input) => {
    attachInputListener(input as HTMLElement);
  });
}

// Track forms with attached listeners to avoid duplicates (N003)
const formsWithListeners = new WeakSet<HTMLFormElement>();

function attachInputListener(input: HTMLElement) {
  if (input.dataset.sentinelProtected) return;
  input.dataset.sentinelProtected = 'true';

  // Intercept form submission - N003: avoid duplicate listeners
  const form = input.closest('form');
  if (form && !formsWithListeners.has(form)) {
    form.addEventListener('submit', handleSubmit, true);
    formsWithListeners.add(form);
  }

  // Intercept Enter key - N004: check bypass flag
  input.addEventListener('keydown', (e) => {
    // N004: Check bypass flag before blocking
    if (input.dataset.sentinelBypass === 'true') return;

    if (e.key === 'Enter' && !e.shiftKey) {
      const text = getInputText(input);
      if (text && shouldBlockSubmission(text)) {
        e.preventDefault();
        e.stopPropagation();
        showWarning(text, input);
      }
    }
  }, true);

  // Real-time scanning (debounced)
  let scanTimeout: number | undefined;
  input.addEventListener('input', () => {
    clearTimeout(scanTimeout);
    scanTimeout = window.setTimeout(() => {
      const text = getInputText(input);
      if (text) {
        scanAndIndicate(text, input);
      }
    }, 500);
  });
}

function getInputText(element: HTMLElement): string {
  if (element instanceof HTMLTextAreaElement) {
    return element.value;
  }
  if (element.contentEditable === 'true') {
    return element.textContent || '';
  }
  return '';
}

function handleSubmit(e: Event) {
  const form = e.target as HTMLFormElement;
  const input = form.querySelector(INPUT_SELECTORS[platform] || INPUT_SELECTORS.unknown);

  if (input) {
    const text = getInputText(input as HTMLElement);
    if (text && shouldBlockSubmission(text)) {
      e.preventDefault();
      e.stopPropagation();
      showWarning(text, input as HTMLElement);
    }
  }
}

function shouldBlockSubmission(text: string): boolean {
  const matches = scanAll(text);

  if (protectionLevel === 'maximum') {
    return matches.length > 0;
  }

  if (protectionLevel === 'recommended') {
    return matches.some((m) => m.severity === 'critical' || m.severity === 'high');
  }

  // Basic: only critical
  return matches.some((m) => m.severity === 'critical');
}

function scanAndIndicate(text: string, input: HTMLElement) {
  const matches = scanAll(text);
  const indicator = getOrCreateIndicator(input);

  // N002: Handle case where indicator creation failed
  if (!indicator) {
    return;
  }

  if (matches.length > 0) {
    const critical = matches.filter((m) => m.severity === 'critical').length;
    const high = matches.filter((m) => m.severity === 'high').length;

    indicator.className = 'sentinel-indicator';
    if (critical > 0) {
      indicator.classList.add('sentinel-critical');
      indicator.textContent = `⚠️ ${critical} critical issue${critical > 1 ? 's' : ''}`;
    } else if (high > 0) {
      indicator.classList.add('sentinel-warning');
      indicator.textContent = `⚠️ ${high} sensitive item${high > 1 ? 's' : ''} detected`;
    } else {
      indicator.classList.add('sentinel-info');
      indicator.textContent = `ℹ️ ${matches.length} item${matches.length > 1 ? 's' : ''} to review`;
    }
    indicator.style.display = 'block';
  } else {
    indicator.style.display = 'none';
  }
}

function getOrCreateIndicator(input: HTMLElement): HTMLElement | null {
  // N002: Handle case where parentElement is null
  if (!input.parentElement) {
    return null;
  }

  let indicator = input.parentElement.querySelector('.sentinel-indicator') as HTMLElement | null;

  if (!indicator) {
    indicator = document.createElement('div');
    indicator.className = 'sentinel-indicator';
    input.parentElement.insertBefore(indicator, input);
  }

  return indicator;
}

// Warning modal
function showWarning(text: string, input: HTMLElement) {
  const matches = scanAll(text);

  // N005: Handle sendMessage errors
  chrome.runtime.sendMessage({
    type: 'REPORT_THREAT',
    payload: {
      type: 'secret',
      message: `Blocked: ${matches.length} sensitive item(s) detected`,
      details: { matches: matches.slice(0, 5) },
    },
  }).catch((err) => {
    console.warn('[Sentinel Guard] Failed to report threat:', err);
  });

  // C001: Create modal using safe DOM methods instead of innerHTML
  const modal = document.createElement('div');
  modal.className = 'sentinel-modal-overlay';

  const modalContent = document.createElement('div');
  modalContent.className = 'sentinel-modal';

  // Header
  const header = document.createElement('div');
  header.className = 'sentinel-modal-header';
  const logo = document.createElement('span');
  logo.className = 'sentinel-logo';
  logo.textContent = '🛡️';
  const title = document.createElement('span');
  title.textContent = 'Sentinel Guard';
  const closeBtn = document.createElement('button');
  closeBtn.className = 'sentinel-close';
  closeBtn.textContent = '×';
  header.append(logo, title, closeBtn);

  // Body
  const body = document.createElement('div');
  body.className = 'sentinel-modal-body';
  const h3 = document.createElement('h3');
  h3.textContent = '⚠️ Sensitive Data Detected';
  const p = document.createElement('p');
  p.textContent = 'The following items were found in your message:';
  const ul = document.createElement('ul');
  ul.className = 'sentinel-matches';

  // C001: Create list items safely (no innerHTML with user data)
  for (const match of matches.slice(0, 5)) {
    const li = document.createElement('li');
    const strong = document.createElement('strong');
    strong.textContent = escapeHtml(match.type) + ':';
    li.append(strong, ' ' + escapeHtml(match.message));
    ul.appendChild(li);
  }
  if (matches.length > 5) {
    const li = document.createElement('li');
    li.textContent = `...and ${matches.length - 5} more`;
    ul.appendChild(li);
  }

  body.append(h3, p, ul);

  // Actions
  const actions = document.createElement('div');
  actions.className = 'sentinel-modal-actions';
  const btnRemove = document.createElement('button');
  btnRemove.className = 'sentinel-btn sentinel-btn-primary';
  btnRemove.dataset.action = 'remove';
  btnRemove.textContent = 'Remove All';
  const btnMask = document.createElement('button');
  btnMask.className = 'sentinel-btn sentinel-btn-secondary';
  btnMask.dataset.action = 'mask';
  btnMask.textContent = 'Mask Data';
  const btnSend = document.createElement('button');
  btnSend.className = 'sentinel-btn sentinel-btn-danger';
  btnSend.dataset.action = 'send';
  btnSend.textContent = 'Send Anyway';
  actions.append(btnRemove, btnMask, btnSend);

  modalContent.append(header, body, actions);
  modal.appendChild(modalContent);
  document.body.appendChild(modal);

  // Handle actions
  modal.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    const action = target.dataset.action;

    if (target.classList.contains('sentinel-close') || target.classList.contains('sentinel-modal-overlay')) {
      modal.remove();
      return;
    }

    if (action === 'remove') {
      // Remove all sensitive data
      let cleaned = text;
      for (const match of matches.sort((a, b) => b.start - a.start)) {
        cleaned = cleaned.substring(0, match.start) + cleaned.substring(match.end);
      }
      setInputText(input, cleaned.trim());
      modal.remove();
    } else if (action === 'mask') {
      // Mask sensitive data
      const masked = maskSensitiveData(text, matches);
      setInputText(input, masked);
      modal.remove();
    } else if (action === 'send') {
      // User confirmed - allow send
      modal.remove();
      // Temporarily disable protection to allow send
      input.dataset.sentinelBypass = 'true';
      triggerSend(input);
      setTimeout(() => {
        delete input.dataset.sentinelBypass;
      }, 100);
    }
  });
}

function setInputText(element: HTMLElement, text: string) {
  if (element instanceof HTMLTextAreaElement) {
    element.value = text;
    element.dispatchEvent(new Event('input', { bubbles: true }));
  } else if (element.contentEditable === 'true') {
    element.textContent = text;
    element.dispatchEvent(new Event('input', { bubbles: true }));
  }
}

function triggerSend(input: HTMLElement): boolean {
  const sendSelector = SEND_SELECTORS[platform] || SEND_SELECTORS.unknown;
  const sendButton = document.querySelector(sendSelector) as HTMLButtonElement | null;

  if (sendButton) {
    sendButton.click();
    return true;
  }

  // N006: Try alternative - simulate Enter key on input
  try {
    const event = new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
      which: 13,
      bubbles: true,
      cancelable: true
    });
    input.dispatchEvent(event);
    return true;
  } catch (err) {
    console.warn('[Sentinel Guard] Failed to trigger send:', err);
    return false;
  }
}

// Conversation Shield - protect from other extensions
// C003: Instead of modifying native prototypes, use MutationObserver to monitor DOM access
function setupConversationShield() {
  // Monitor for suspicious script injections instead of wrapping native methods
  const scriptObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node instanceof HTMLScriptElement) {
          // Check for suspicious script content
          const src = node.src || '';
          if (src && !isTrustedScriptSource(src)) {
            logSuspiciousActivity('External script injection', { src });
          }
        }
      }
    }
  });

  // Only observe if document.head exists
  if (document.head) {
    scriptObserver.observe(document.head, { childList: true });
  }

  // Monitor for potentially dangerous attribute changes on inputs
  const inputObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === 'attributes' && mutation.target instanceof HTMLElement) {
        const target = mutation.target;
        // Check for suspicious attribute manipulation on protected inputs
        if (target.dataset.sentinelProtected && mutation.attributeName === 'value') {
          logSuspiciousActivity('Protected input value modified externally', {
            element: target.tagName
          });
        }
      }
    }
  });

  // Observe the body for attribute changes on inputs
  if (document.body) {
    inputObserver.observe(document.body, {
      attributes: true,
      subtree: true,
      attributeFilter: ['value', 'data-sentinel-protected']
    });
  }
}

function isTrustedScriptSource(src: string): boolean {
  const trustedDomains = [
    'cdn.jsdelivr.net',
    'unpkg.com',
    'chat.openai.com',
    'chatgpt.com',
    'claude.ai',
    'gemini.google.com',
    'perplexity.ai'
  ];

  try {
    const url = new URL(src);
    return trustedDomains.some(domain => url.hostname.endsWith(domain));
  } catch {
    return false;
  }
}

function logSuspiciousActivity(type: string, details: Record<string, unknown>) {
  console.warn(`[Sentinel Guard] Suspicious activity detected: ${type}`, details);

  // Report to background - N005: Handle errors
  chrome.runtime.sendMessage({
    type: 'REPORT_THREAT',
    payload: { type, message: `Suspicious: ${type}`, details }
  }).catch(() => {
    // Ignore - background might not be available
  });
}

/**
 * Create a toast notification safely (no innerHTML)
 */
function createToast(message: string, type: 'warning' | 'success'): HTMLElement {
  const toast = document.createElement('div');
  toast.className = `sentinel-toast sentinel-toast-${type}`;

  const icon = document.createElement('span');
  icon.textContent = '🛡️';

  const text = document.createElement('span');
  text.textContent = message;

  toast.append(icon, text);
  return toast;
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SCAN_PAGE') {
    // N001: Guard against document.body being null
    if (!document.body) {
      sendResponse({ matches: [], count: 0, error: 'Document body not available' });
      return true;
    }

    const bodyText = document.body.innerText || '';
    const matches = scanAll(bodyText);

    if (matches.length > 0) {
      const critical = matches.filter((m) => m.severity === 'critical').length;
      const high = matches.filter((m) => m.severity === 'high').length;

      // C001: Create toast safely without innerHTML
      const toast = createToast(
        `Page scan: ${matches.length} item(s) found (${critical} critical, ${high} high)`,
        'warning'
      );
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 5000);

      sendResponse({ matches, count: matches.length });
    } else {
      // C001: Create toast safely without innerHTML
      const toast = createToast('Page scan complete: No sensitive data found', 'success');
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);

      sendResponse({ matches: [], count: 0 });
    }
  }
  return true;
});

// Start
init();
