/**
 * Sentinel Guard - Internationalization (i18n)
 * Supports: English (en), Spanish (es), Portuguese (pt)
 */

export type Language = 'en' | 'es' | 'pt';

export interface Translations {
  // Header
  appName: string;
  protected: string;
  disabled: string;

  // Navigation
  dashboard: string;
  alerts: string;
  settings: string;

  // Dashboard
  threatsBlocked: string;
  secretsCaught: string;
  sessionsProtected: string;
  protection: string;
  quickActions: string;
  scanPage: string;
  checkClipboard: string;

  // Protection levels
  protectionLevel: string;
  basic: string;
  recommended: string;
  maximum: string;

  // Settings
  enabled: string;
  enableProtection: string;
  notifications: string;
  showNotifications: string;
  language: string;
  selectLanguage: string;
  protectedPlatforms: string;
  howAggressive: string;

  // Alerts
  noAlerts: string;
  noAlertsDesc: string;
  acknowledge: string;

  // Warning modal
  warningTitle: string;
  sensitiveDataDetected: string;
  detectedItems: string;
  removeAll: string;
  maskData: string;
  sendAnyway: string;
  cancel: string;

  // Content script messages
  criticalIssues: string;
  sensitiveItems: string;
  itemsToReview: string;
  piiDetected: string;
  walletThreat: string;
  pageScanComplete: string;
  noSensitiveData: string;
  clipboardWarning: string;
  clipboardSafe: string;
}

const translations: Record<Language, Translations> = {
  en: {
    // Header
    appName: 'Sentinel Guard',
    protected: 'Protected',
    disabled: 'Disabled',

    // Navigation
    dashboard: 'Dashboard',
    alerts: 'Alerts',
    settings: 'Settings',

    // Dashboard
    threatsBlocked: 'Threats Blocked',
    secretsCaught: 'Secrets Caught',
    sessionsProtected: 'Sessions Protected',
    protection: 'protection',
    quickActions: 'Quick Actions',
    scanPage: 'Scan Page',
    checkClipboard: 'Check Clipboard',

    // Protection levels
    protectionLevel: 'Protection Level',
    basic: 'Basic',
    recommended: 'Recommended',
    maximum: 'Maximum',

    // Settings
    enabled: 'Enabled',
    enableProtection: 'Enable protection',
    notifications: 'Notifications',
    showNotifications: 'Show desktop notifications',
    language: 'Language',
    selectLanguage: 'Select language',
    protectedPlatforms: 'Protected Platforms',
    howAggressive: 'How aggressive should protection be?',

    // Alerts
    noAlerts: 'No alerts',
    noAlertsDesc: 'You\'re all clear! No security alerts.',
    acknowledge: 'Acknowledge',

    // Warning modal
    warningTitle: 'Security Warning',
    sensitiveDataDetected: 'Sensitive data detected in your message',
    detectedItems: 'Detected items',
    removeAll: 'Remove All',
    maskData: 'Mask Data',
    sendAnyway: 'Send Anyway',
    cancel: 'Cancel',

    // Content script messages
    criticalIssues: 'critical issue(s)',
    sensitiveItems: 'sensitive item(s) detected',
    itemsToReview: 'item(s) to review',
    piiDetected: 'PII item(s) detected',
    walletThreat: 'Wallet threat detected',
    pageScanComplete: 'Page scan complete',
    noSensitiveData: 'No sensitive data found',
    clipboardWarning: 'sensitive item(s) found in clipboard!',
    clipboardSafe: 'Clipboard is safe',
  },

  es: {
    // Header
    appName: 'Sentinel Guard',
    protected: 'Protegido',
    disabled: 'Desactivado',

    // Navigation
    dashboard: 'Panel',
    alerts: 'Alertas',
    settings: 'Ajustes',

    // Dashboard
    threatsBlocked: 'Amenazas Bloqueadas',
    secretsCaught: 'Secretos Detectados',
    sessionsProtected: 'Sesiones Protegidas',
    protection: 'protección',
    quickActions: 'Acciones Rápidas',
    scanPage: 'Escanear Página',
    checkClipboard: 'Verificar Portapapeles',

    // Protection levels
    protectionLevel: 'Nivel de Protección',
    basic: 'Básico',
    recommended: 'Recomendado',
    maximum: 'Máximo',

    // Settings
    enabled: 'Activado',
    enableProtection: 'Activar protección',
    notifications: 'Notificaciones',
    showNotifications: 'Mostrar notificaciones de escritorio',
    language: 'Idioma',
    selectLanguage: 'Seleccionar idioma',
    protectedPlatforms: 'Plataformas Protegidas',
    howAggressive: '¿Qué tan agresiva debe ser la protección?',

    // Alerts
    noAlerts: 'Sin alertas',
    noAlertsDesc: '¡Todo limpio! No hay alertas de seguridad.',
    acknowledge: 'Reconocer',

    // Warning modal
    warningTitle: 'Advertencia de Seguridad',
    sensitiveDataDetected: 'Se detectaron datos sensibles en tu mensaje',
    detectedItems: 'Elementos detectados',
    removeAll: 'Eliminar Todo',
    maskData: 'Enmascarar Datos',
    sendAnyway: 'Enviar de Todos Modos',
    cancel: 'Cancelar',

    // Content script messages
    criticalIssues: 'problema(s) crítico(s)',
    sensitiveItems: 'elemento(s) sensible(s) detectado(s)',
    itemsToReview: 'elemento(s) para revisar',
    piiDetected: 'elemento(s) PII detectado(s)',
    walletThreat: 'Amenaza de billetera detectada',
    pageScanComplete: 'Escaneo de página completo',
    noSensitiveData: 'No se encontraron datos sensibles',
    clipboardWarning: '¡elemento(s) sensible(s) encontrado(s) en el portapapeles!',
    clipboardSafe: 'El portapapeles está seguro',
  },

  pt: {
    // Header
    appName: 'Sentinel Guard',
    protected: 'Protegido',
    disabled: 'Desativado',

    // Navigation
    dashboard: 'Painel',
    alerts: 'Alertas',
    settings: 'Configurações',

    // Dashboard
    threatsBlocked: 'Ameaças Bloqueadas',
    secretsCaught: 'Segredos Detectados',
    sessionsProtected: 'Sessões Protegidas',
    protection: 'proteção',
    quickActions: 'Ações Rápidas',
    scanPage: 'Escanear Página',
    checkClipboard: 'Verificar Área de Transferência',

    // Protection levels
    protectionLevel: 'Nível de Proteção',
    basic: 'Básico',
    recommended: 'Recomendado',
    maximum: 'Máximo',

    // Settings
    enabled: 'Ativado',
    enableProtection: 'Ativar proteção',
    notifications: 'Notificações',
    showNotifications: 'Mostrar notificações na área de trabalho',
    language: 'Idioma',
    selectLanguage: 'Selecionar idioma',
    protectedPlatforms: 'Plataformas Protegidas',
    howAggressive: 'Quão agressiva deve ser a proteção?',

    // Alerts
    noAlerts: 'Sem alertas',
    noAlertsDesc: 'Tudo limpo! Nenhum alerta de segurança.',
    acknowledge: 'Reconhecer',

    // Warning modal
    warningTitle: 'Aviso de Segurança',
    sensitiveDataDetected: 'Dados sensíveis detectados na sua mensagem',
    detectedItems: 'Itens detectados',
    removeAll: 'Remover Tudo',
    maskData: 'Mascarar Dados',
    sendAnyway: 'Enviar Mesmo Assim',
    cancel: 'Cancelar',

    // Content script messages
    criticalIssues: 'problema(s) crítico(s)',
    sensitiveItems: 'item(ns) sensível(is) detectado(s)',
    itemsToReview: 'item(ns) para revisar',
    piiDetected: 'item(ns) PII detectado(s)',
    walletThreat: 'Ameaça de carteira detectada',
    pageScanComplete: 'Varredura da página completa',
    noSensitiveData: 'Nenhum dado sensível encontrado',
    clipboardWarning: 'item(ns) sensível(is) encontrado(s) na área de transferência!',
    clipboardSafe: 'Área de transferência segura',
  },
};

// Current language (will be loaded from storage)
let currentLanguage: Language = 'en';

/**
 * Set the current language
 */
export function setLanguage(lang: Language): void {
  currentLanguage = lang;
}

/**
 * Get the current language
 */
export function getLanguage(): Language {
  return currentLanguage;
}

/**
 * Get translation for a key
 */
export function t(key: keyof Translations): string {
  return translations[currentLanguage][key] || translations.en[key] || key;
}

/**
 * Get all translations for current language
 */
export function getTranslations(): Translations {
  return translations[currentLanguage];
}

/**
 * Get available languages
 */
export function getAvailableLanguages(): { code: Language; name: string }[] {
  return [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'pt', name: 'Português' },
  ];
}

/**
 * Detect browser language and return closest match
 */
export function detectBrowserLanguage(): Language {
  const browserLang = navigator.language.toLowerCase().split('-')[0];
  if (browserLang === 'es') return 'es';
  if (browserLang === 'pt') return 'pt';
  return 'en';
}
