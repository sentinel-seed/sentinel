/**
 * Sentinel Guard - Content Script
 *
 * Injected into AI chat platforms to:
 * - Protect conversations from other extensions
 * - Scan input for sensitive data
 * - Detect and block threats
 */

import { scanAll, maskSensitiveData, PatternMatch } from '../lib/patterns';

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

function attachInputListener(input: HTMLElement) {
  if (input.dataset.sentinelProtected) return;
  input.dataset.sentinelProtected = 'true';

  // Intercept form submission
  const form = input.closest('form');
  if (form) {
    form.addEventListener('submit', handleSubmit, true);
  }

  // Intercept Enter key
  input.addEventListener('keydown', (e) => {
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

function getOrCreateIndicator(input: HTMLElement): HTMLElement {
  let indicator = input.parentElement?.querySelector('.sentinel-indicator') as HTMLElement;

  if (!indicator) {
    indicator = document.createElement('div');
    indicator.className = 'sentinel-indicator';
    input.parentElement?.insertBefore(indicator, input);
  }

  return indicator;
}

// Warning modal
function showWarning(text: string, input: HTMLElement) {
  const matches = scanAll(text);

  // Report to background
  chrome.runtime.sendMessage({
    type: 'REPORT_THREAT',
    payload: {
      type: 'secret',
      message: `Blocked: ${matches.length} sensitive item(s) detected`,
      details: { matches: matches.slice(0, 5) },
    },
  });

  // Create modal
  const modal = document.createElement('div');
  modal.className = 'sentinel-modal-overlay';
  modal.innerHTML = `
    <div class="sentinel-modal">
      <div class="sentinel-modal-header">
        <span class="sentinel-logo">🛡️</span>
        <span>Sentinel Guard</span>
        <button class="sentinel-close">&times;</button>
      </div>
      <div class="sentinel-modal-body">
        <h3>⚠️ Sensitive Data Detected</h3>
        <p>The following items were found in your message:</p>
        <ul class="sentinel-matches">
          ${matches
            .slice(0, 5)
            .map((m) => `<li><strong>${m.type}:</strong> ${m.message}</li>`)
            .join('')}
          ${matches.length > 5 ? `<li>...and ${matches.length - 5} more</li>` : ''}
        </ul>
      </div>
      <div class="sentinel-modal-actions">
        <button class="sentinel-btn sentinel-btn-primary" data-action="remove">Remove All</button>
        <button class="sentinel-btn sentinel-btn-secondary" data-action="mask">Mask Data</button>
        <button class="sentinel-btn sentinel-btn-danger" data-action="send">Send Anyway</button>
      </div>
    </div>
  `;

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

function triggerSend(input: HTMLElement) {
  const sendSelector = SEND_SELECTORS[platform] || SEND_SELECTORS.unknown;
  const sendButton = document.querySelector(sendSelector) as HTMLButtonElement;
  if (sendButton) {
    sendButton.click();
  }
}

// Conversation Shield - protect from other extensions
function setupConversationShield() {
  // Monitor for suspicious DOM access
  const originalQuerySelector = Document.prototype.querySelector;
  const originalQuerySelectorAll = Document.prototype.querySelectorAll;

  // Wrap querySelector to detect suspicious queries
  Document.prototype.querySelector = function (selector: string) {
    checkSuspiciousSelector(selector);
    return originalQuerySelector.call(this, selector);
  };

  Document.prototype.querySelectorAll = function (selector: string) {
    checkSuspiciousSelector(selector);
    return originalQuerySelectorAll.call(this, selector);
  };
}

function checkSuspiciousSelector(selector: string) {
  // Selectors that other extensions might use to harvest conversations
  const suspiciousPatterns = [
    /conversation/i,
    /message.*content/i,
    /chat.*history/i,
    /assistant.*response/i,
  ];

  for (const pattern of suspiciousPatterns) {
    if (pattern.test(selector)) {
      // Log but don't block (might be legitimate)
      console.log('[Sentinel Guard] Detected query for conversation data:', selector);
      break;
    }
  }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SCAN_PAGE') {
    const bodyText = document.body.innerText;
    const matches = scanAll(bodyText);

    if (matches.length > 0) {
      const critical = matches.filter((m) => m.severity === 'critical').length;
      const high = matches.filter((m) => m.severity === 'high').length;

      // Show toast notification
      const toast = document.createElement('div');
      toast.className = 'sentinel-toast sentinel-toast-warning';
      toast.innerHTML = `
        <span>🛡️</span>
        <span>Page scan: ${matches.length} item(s) found (${critical} critical, ${high} high)</span>
      `;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 5000);

      sendResponse({ matches, count: matches.length });
    } else {
      // Show success toast
      const toast = document.createElement('div');
      toast.className = 'sentinel-toast sentinel-toast-success';
      toast.innerHTML = `
        <span>🛡️</span>
        <span>Page scan complete: No sensitive data found</span>
      `;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);

      sendResponse({ matches: [], count: 0 });
    }
  }
  return true;
});

// Start
init();
