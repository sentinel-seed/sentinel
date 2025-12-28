/**
 * Sentinel Guard - Bot/Agent Detector
 *
 * Detects automated agents, bots, and suspicious automation on AI platforms.
 * Helps users identify when they might be interacting with non-human entities
 * or when their session is being automated by third parties.
 */

export interface BotIndicator {
  type: string;
  confidence: number; // 0-100
  description: string;
  details?: Record<string, unknown>;
}

export interface BotDetectionResult {
  isBot: boolean;
  confidence: number; // 0-100
  indicators: BotIndicator[];
  summary: string;
}

// Known automation framework signatures
const AUTOMATION_SIGNATURES = {
  // Selenium/WebDriver
  webdriver: [
    'webdriver',
    '__webdriver_evaluate',
    '__selenium_evaluate',
    '__webdriver_script_function',
    '__webdriver_script_func',
    '__webdriver_script_fn',
    '__fxdriver_evaluate',
    '__driver_unwrapped',
    '__webdriver_unwrapped',
    '__driver_evaluate',
    '__selenium_unwrapped',
    '_Selenium_IDE_Recorder',
    '_selenium',
    'calledSelenium',
  ],
  // Puppeteer/Playwright
  puppeteer: [
    '__puppeteer_evaluation_script__',
    '__playwright_evaluation_script__',
  ],
  // PhantomJS
  phantom: [
    'callPhantom',
    '_phantom',
    'phantom',
  ],
  // Nightmare
  nightmare: [
    '__nightmare',
    'nightmare',
  ],
  // Generic automation
  generic: [
    'domAutomation',
    'domAutomationController',
  ],
};

// Suspicious navigator properties (used as reference for checkNavigatorProperties)
const _SUSPICIOUS_NAVIGATOR_PROPS = [
  'webdriver',
  'languages', // Empty or single language can indicate automation
  'plugins', // Empty plugins array is suspicious
  'hardwareConcurrency', // Unusual values
];

/**
 * Check for automation framework signatures in window object
 */
function checkAutomationSignatures(): BotIndicator[] {
  const indicators: BotIndicator[] = [];
  const win = window as unknown as Record<string, unknown>;

  for (const [framework, signatures] of Object.entries(AUTOMATION_SIGNATURES)) {
    for (const sig of signatures) {
      if (sig in win || (win.document && sig in (win.document as Record<string, unknown>))) {
        indicators.push({
          type: 'automation_signature',
          confidence: 95,
          description: `${framework} automation detected`,
          details: { signature: sig, framework },
        });
      }
    }
  }

  return indicators;
}

/**
 * Check navigator properties for bot indicators
 */
function checkNavigatorProperties(): BotIndicator[] {
  const indicators: BotIndicator[] = [];
  const nav = navigator;

  // Check webdriver property
  if ((nav as unknown as Record<string, unknown>).webdriver === true) {
    indicators.push({
      type: 'webdriver_flag',
      confidence: 99,
      description: 'WebDriver flag is set to true',
    });
  }

  // Check for missing/empty plugins (common in headless browsers)
  if (!nav.plugins || nav.plugins.length === 0) {
    indicators.push({
      type: 'no_plugins',
      confidence: 60,
      description: 'No browser plugins detected (possible headless browser)',
    });
  }

  // Check for missing/empty languages
  if (!nav.languages || nav.languages.length === 0) {
    indicators.push({
      type: 'no_languages',
      confidence: 70,
      description: 'No languages configured (possible automation)',
    });
  }

  // Check for suspicious userAgent patterns
  const ua = nav.userAgent.toLowerCase();
  const headlessPatterns = ['headless', 'phantomjs', 'slimerjs', 'electron'];
  for (const pattern of headlessPatterns) {
    if (ua.includes(pattern)) {
      indicators.push({
        type: 'headless_ua',
        confidence: 90,
        description: `Headless browser signature in user agent: ${pattern}`,
      });
    }
  }

  return indicators;
}

/**
 * Check for Chrome-specific automation indicators
 */
function checkChromeAutomation(): BotIndicator[] {
  const indicators: BotIndicator[] = [];
  const win = window as unknown as Record<string, unknown>;

  // Check Chrome DevTools protocol
  if (win.chrome) {
    // chrome object exists, check for ChromeDriver properties
    // Check for cdc_ (ChromeDriver) properties
    for (const key of Object.keys(win)) {
      if (key.startsWith('cdc_') || key.startsWith('$cdc_')) {
        indicators.push({
          type: 'chromedriver',
          confidence: 95,
          description: 'ChromeDriver control variable detected',
          details: { variable: key },
        });
      }
    }
  }

  return indicators;
}

/**
 * Check for abnormal timing patterns (bot-like behavior)
 */
interface TimingTracker {
  clicks: number[];
  keystrokes: number[];
}

const timingTracker: TimingTracker = {
  clicks: [],
  keystrokes: [],
};

/**
 * Record a user interaction for timing analysis
 */
export function recordInteraction(type: 'click' | 'keystroke'): void {
  const now = Date.now();
  const tracker = type === 'click' ? timingTracker.clicks : timingTracker.keystrokes;

  tracker.push(now);

  // Keep only last 50 interactions
  if (tracker.length > 50) {
    tracker.shift();
  }
}

/**
 * Analyze timing patterns for bot-like behavior
 */
function analyzeTimingPatterns(): BotIndicator[] {
  const indicators: BotIndicator[] = [];

  // Analyze click patterns
  if (timingTracker.clicks.length >= 10) {
    const intervals = calculateIntervals(timingTracker.clicks);
    const stats = calculateStats(intervals);

    // Very consistent timing is suspicious (humans have variance)
    if (stats.stdDev < 10 && stats.mean < 100) {
      indicators.push({
        type: 'consistent_clicks',
        confidence: 75,
        description: 'Click timing is unnaturally consistent',
        details: { mean: stats.mean, stdDev: stats.stdDev },
      });
    }

    // Inhuman speed
    if (stats.mean < 50) {
      indicators.push({
        type: 'fast_clicks',
        confidence: 85,
        description: 'Click speed exceeds human capability',
        details: { meanInterval: stats.mean },
      });
    }
  }

  // Analyze keystroke patterns
  if (timingTracker.keystrokes.length >= 20) {
    const intervals = calculateIntervals(timingTracker.keystrokes);
    const stats = calculateStats(intervals);

    // Very consistent typing is suspicious
    if (stats.stdDev < 5) {
      indicators.push({
        type: 'consistent_typing',
        confidence: 70,
        description: 'Typing rhythm is unnaturally consistent',
        details: { mean: stats.mean, stdDev: stats.stdDev },
      });
    }

    // Inhuman typing speed (< 20ms per keystroke = 3000+ WPM)
    if (stats.mean < 20) {
      indicators.push({
        type: 'fast_typing',
        confidence: 90,
        description: 'Typing speed exceeds human capability',
        details: { meanInterval: stats.mean },
      });
    }
  }

  return indicators;
}

/**
 * Calculate intervals between timestamps
 */
function calculateIntervals(timestamps: number[]): number[] {
  const intervals: number[] = [];
  for (let i = 1; i < timestamps.length; i++) {
    intervals.push(timestamps[i] - timestamps[i - 1]);
  }
  return intervals;
}

/**
 * Calculate mean and standard deviation
 */
function calculateStats(values: number[]): { mean: number; stdDev: number } {
  if (values.length === 0) return { mean: 0, stdDev: 0 };

  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const squaredDiffs = values.map((v) => Math.pow(v - mean, 2));
  const variance = squaredDiffs.reduce((a, b) => a + b, 0) / values.length;
  const stdDev = Math.sqrt(variance);

  return { mean, stdDev };
}

/**
 * Check for permission anomalies
 */
async function checkPermissionAnomalies(): Promise<BotIndicator[]> {
  const indicators: BotIndicator[] = [];

  try {
    // Check notification permission (bots often have it denied or not asked)
    if ('Notification' in window) {
      if (Notification.permission === 'denied') {
        // This alone isn't suspicious, but combined with others...
      }
    }

    // Check for permissions API support (missing in some automation frameworks)
    if (!('permissions' in navigator)) {
      indicators.push({
        type: 'no_permissions_api',
        confidence: 40,
        description: 'Permissions API not available',
      });
    }
  } catch {
    // Permissions check failed, not necessarily suspicious
  }

  return indicators;
}

/**
 * Check for canvas fingerprint anomalies
 */
function checkCanvasAnomaly(): BotIndicator[] {
  const indicators: BotIndicator[] = [];

  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      indicators.push({
        type: 'no_canvas',
        confidence: 50,
        description: 'Canvas 2D context not available',
      });
      return indicators;
    }

    // Draw something and check if it works
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('test', 2, 2);

    const data = canvas.toDataURL();

    // Empty or very short data URL is suspicious
    if (data.length < 100) {
      indicators.push({
        type: 'canvas_blocked',
        confidence: 60,
        description: 'Canvas rendering appears to be blocked or modified',
      });
    }
  } catch {
    indicators.push({
      type: 'canvas_error',
      confidence: 45,
      description: 'Canvas operations failed',
    });
  }

  return indicators;
}

/**
 * Check for WebGL anomalies
 */
function checkWebGLAnomaly(): BotIndicator[] {
  const indicators: BotIndicator[] = [];

  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') as WebGLRenderingContext | null;

    if (!gl) {
      indicators.push({
        type: 'no_webgl',
        confidence: 40,
        description: 'WebGL not available (possible headless browser)',
      });
      return indicators;
    }

    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    if (debugInfo) {
      const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) as string;
      const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) as string;

      // Check for known virtual/software renderers
      const softwareRenderers = ['swiftshader', 'llvmpipe', 'software'];
      const rendererLower = (renderer || '').toLowerCase();

      for (const sr of softwareRenderers) {
        if (rendererLower.includes(sr)) {
          indicators.push({
            type: 'software_renderer',
            confidence: 70,
            description: `Software WebGL renderer detected: ${renderer} (${vendor})`,
          });
        }
      }
    }
  } catch {
    // WebGL check failed
  }

  return indicators;
}

/**
 * Main detection function - runs all checks
 */
export async function detectBot(): Promise<BotDetectionResult> {
  const allIndicators: BotIndicator[] = [];

  // Run all synchronous checks
  allIndicators.push(...checkAutomationSignatures());
  allIndicators.push(...checkNavigatorProperties());
  allIndicators.push(...checkChromeAutomation());
  allIndicators.push(...analyzeTimingPatterns());
  allIndicators.push(...checkCanvasAnomaly());
  allIndicators.push(...checkWebGLAnomaly());

  // Run async checks
  const permissionIndicators = await checkPermissionAnomalies();
  allIndicators.push(...permissionIndicators);

  // Calculate overall confidence
  let totalConfidence = 0;
  if (allIndicators.length > 0) {
    // Weight by confidence and take the weighted average
    const weightedSum = allIndicators.reduce((sum, ind) => sum + ind.confidence, 0);
    totalConfidence = Math.min(100, weightedSum / allIndicators.length + (allIndicators.length * 5));
  }

  // Determine if it's a bot
  const isBot = totalConfidence >= 50;

  // Generate summary
  let summary: string;
  if (!isBot && allIndicators.length === 0) {
    summary = 'No automation indicators detected. Session appears human-operated.';
  } else if (!isBot) {
    summary = `Minor indicators detected (${allIndicators.length}), but likely human-operated.`;
  } else if (totalConfidence >= 90) {
    summary = `High confidence automation detected! ${allIndicators.length} indicators found.`;
  } else {
    summary = `Possible automation detected. ${allIndicators.length} suspicious indicators.`;
  }

  return {
    isBot,
    confidence: Math.round(totalConfidence),
    indicators: allIndicators,
    summary,
  };
}

/**
 * Quick check - returns true if likely bot
 */
export async function quickBotCheck(): Promise<boolean> {
  const result = await detectBot();
  return result.isBot;
}

/**
 * Setup interaction tracking listeners
 */
export function setupBotDetectionListeners(): void {
  document.addEventListener('click', () => recordInteraction('click'), true);
  document.addEventListener('keydown', () => recordInteraction('keystroke'), true);
}
