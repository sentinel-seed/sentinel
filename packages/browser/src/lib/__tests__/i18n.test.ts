/**
 * @fileoverview Unit tests for i18n module
 *
 * Tests internationalization functionality:
 * - Language setting and getting
 * - Translation retrieval
 * - Browser language detection
 * - Available languages
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  setLanguage,
  getLanguage,
  t,
  getTranslations,
  getAvailableLanguages,
  detectBrowserLanguage,
  Language,
} from '../i18n';

describe('i18n', () => {
  // Reset language to English before each test
  beforeEach(() => {
    setLanguage('en');
  });

  describe('setLanguage and getLanguage', () => {
    it('should set and get language correctly', () => {
      setLanguage('es');
      expect(getLanguage()).toBe('es');

      setLanguage('pt');
      expect(getLanguage()).toBe('pt');

      setLanguage('en');
      expect(getLanguage()).toBe('en');
    });

    it('should default to English', () => {
      setLanguage('en');
      expect(getLanguage()).toBe('en');
    });
  });

  describe('t (translate)', () => {
    it('should return English translation by default', () => {
      setLanguage('en');
      expect(t('appName')).toBe('Sentinel Guard');
      expect(t('protected')).toBe('Protected');
      expect(t('disabled')).toBe('Disabled');
    });

    it('should return Spanish translation when set', () => {
      setLanguage('es');
      expect(t('appName')).toBe('Sentinel Guard');
      expect(t('protected')).toBe('Protegido');
      expect(t('disabled')).toBe('Desactivado');
    });

    it('should return Portuguese translation when set', () => {
      setLanguage('pt');
      expect(t('appName')).toBe('Sentinel Guard');
      expect(t('protected')).toBe('Protegido');
      expect(t('disabled')).toBe('Desativado');
    });

    it('should return navigation translations', () => {
      setLanguage('en');
      expect(t('dashboard')).toBe('Dashboard');
      expect(t('alerts')).toBe('Alerts');
      expect(t('settings')).toBe('Settings');
    });

    it('should return dashboard translations', () => {
      setLanguage('en');
      expect(t('threatsBlocked')).toBe('Threats Blocked');
      expect(t('secretsCaught')).toBe('Secrets Caught');
      expect(t('sessionsProtected')).toBe('Sessions Protected');
    });

    it('should return protection level translations', () => {
      setLanguage('en');
      expect(t('basic')).toBe('Basic');
      expect(t('recommended')).toBe('Recommended');
      expect(t('maximum')).toBe('Maximum');

      setLanguage('es');
      expect(t('basic')).toBe('Básico');
      expect(t('recommended')).toBe('Recomendado');
      expect(t('maximum')).toBe('Máximo');

      setLanguage('pt');
      expect(t('basic')).toBe('Básico');
      expect(t('recommended')).toBe('Recomendado');
      expect(t('maximum')).toBe('Máximo');
    });

    it('should return agent shield translations', () => {
      setLanguage('en');
      expect(t('agentShield')).toBe('Agent Shield');
      expect(t('connectedAgents')).toBe('Connected Agents');
      expect(t('trustLevel')).toBe('Trust Level');
    });

    it('should return MCP gateway translations', () => {
      setLanguage('en');
      expect(t('mcpGateway')).toBe('MCP Gateway');
      expect(t('registeredServers')).toBe('Registered Servers');
    });

    it('should return approval system translations', () => {
      setLanguage('en');
      expect(t('pendingApprovals')).toBe('Pending Approvals');
      expect(t('approve')).toBe('Approve');
      expect(t('reject')).toBe('Reject');
    });

    it('should return settings and data translations', () => {
      setLanguage('en');
      expect(t('settings')).toBe('Settings');
      expect(t('enabled')).toBe('Enabled');
      expect(t('enableProtection')).toBe('Enable protection');
      expect(t('disableProtection')).toBe('Disable protection');
      expect(t('notifications')).toBe('Notifications');
      expect(t('language')).toBe('Language');
    });

    it('should return warning modal translations', () => {
      setLanguage('en');
      expect(t('warningTitle')).toBe('Security Warning');
      expect(t('sensitiveDataDetected')).toBe('Sensitive data detected in your message');
      expect(t('removeAll')).toBe('Remove All');
      expect(t('maskData')).toBe('Mask Data');
      expect(t('sendAnyway')).toBe('Send Anyway');
      expect(t('cancel')).toBe('Cancel');
    });

    it('should return history translations', () => {
      setLanguage('en');
      expect(t('history')).toBe('History');
      expect(t('export')).toBe('Export');
      expect(t('clear')).toBe('Clear');
    });
  });

  describe('getTranslations', () => {
    it('should return all translations for current language', () => {
      setLanguage('en');
      const translations = getTranslations();

      expect(translations.appName).toBe('Sentinel Guard');
      expect(translations.protected).toBe('Protected');
      expect(translations.dashboard).toBe('Dashboard');
    });

    it('should return Spanish translations', () => {
      setLanguage('es');
      const translations = getTranslations();

      expect(translations.protected).toBe('Protegido');
      expect(translations.disabled).toBe('Desactivado');
    });

    it('should return Portuguese translations', () => {
      setLanguage('pt');
      const translations = getTranslations();

      expect(translations.protected).toBe('Protegido');
      expect(translations.disabled).toBe('Desativado');
    });

    it('should have all required keys', () => {
      const translations = getTranslations();

      // Core keys
      expect(translations.appName).toBeDefined();
      expect(translations.protected).toBeDefined();
      expect(translations.disabled).toBeDefined();
      expect(translations.dashboard).toBeDefined();
      expect(translations.settings).toBeDefined();

      // Agent Shield keys
      expect(translations.agentShield).toBeDefined();
      expect(translations.connectedAgents).toBeDefined();

      // MCP Gateway keys
      expect(translations.mcpGateway).toBeDefined();
      expect(translations.registeredServers).toBeDefined();

      // Approval keys
      expect(translations.pendingApprovals).toBeDefined();
      expect(translations.approve).toBeDefined();
      expect(translations.reject).toBeDefined();
    });
  });

  describe('getAvailableLanguages', () => {
    it('should return all available languages', () => {
      const languages = getAvailableLanguages();

      expect(languages).toHaveLength(3);
      expect(languages).toContainEqual({ code: 'en', name: 'English' });
      expect(languages).toContainEqual({ code: 'es', name: 'Español' });
      expect(languages).toContainEqual({ code: 'pt', name: 'Português' });
    });

    it('should return language codes as valid Language type', () => {
      const languages = getAvailableLanguages();
      const validCodes: Language[] = ['en', 'es', 'pt'];

      languages.forEach((lang) => {
        expect(validCodes).toContain(lang.code);
      });
    });
  });

  describe('detectBrowserLanguage', () => {
    const originalNavigator = global.navigator;

    afterEach(() => {
      Object.defineProperty(global, 'navigator', {
        value: originalNavigator,
        writable: true,
      });
    });

    it('should detect English', () => {
      Object.defineProperty(global, 'navigator', {
        value: { language: 'en-US' },
        writable: true,
      });

      expect(detectBrowserLanguage()).toBe('en');
    });

    it('should detect Spanish', () => {
      Object.defineProperty(global, 'navigator', {
        value: { language: 'es-ES' },
        writable: true,
      });

      expect(detectBrowserLanguage()).toBe('es');
    });

    it('should detect Portuguese', () => {
      Object.defineProperty(global, 'navigator', {
        value: { language: 'pt-BR' },
        writable: true,
      });

      expect(detectBrowserLanguage()).toBe('pt');
    });

    it('should default to English for unsupported languages', () => {
      Object.defineProperty(global, 'navigator', {
        value: { language: 'fr-FR' },
        writable: true,
      });

      expect(detectBrowserLanguage()).toBe('en');
    });

    it('should handle language codes without region', () => {
      Object.defineProperty(global, 'navigator', {
        value: { language: 'es' },
        writable: true,
      });

      expect(detectBrowserLanguage()).toBe('es');
    });
  });

  describe('Language Consistency', () => {
    it('should have same keys in all languages', () => {
      setLanguage('en');
      const enKeys = Object.keys(getTranslations());

      setLanguage('es');
      const esKeys = Object.keys(getTranslations());

      setLanguage('pt');
      const ptKeys = Object.keys(getTranslations());

      expect(enKeys.sort()).toEqual(esKeys.sort());
      expect(enKeys.sort()).toEqual(ptKeys.sort());
    });

    it('should not have empty translations', () => {
      const languages: Language[] = ['en', 'es', 'pt'];

      languages.forEach((lang) => {
        setLanguage(lang);
        const translations = getTranslations();

        Object.entries(translations).forEach(([key, value]) => {
          expect(value).toBeTruthy();
          expect(typeof value).toBe('string');
          expect(value.length).toBeGreaterThan(0);
        });
      });
    });
  });
});
