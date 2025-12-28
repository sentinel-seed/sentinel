// Jest setup file
// Mock chrome API for testing

// Polyfill for structuredClone (required by fake-indexeddb in Node < 17)
if (typeof structuredClone === 'undefined') {
  global.structuredClone = (obj) => JSON.parse(JSON.stringify(obj));
}

global.chrome = {
  runtime: {
    sendMessage: jest.fn().mockResolvedValue({}),
    onMessage: {
      addListener: jest.fn(),
      removeListener: jest.fn(),
    },
    onInstalled: {
      addListener: jest.fn(),
    },
  },
  storage: {
    local: {
      get: jest.fn().mockResolvedValue({}),
      set: jest.fn().mockResolvedValue(undefined),
    },
  },
  alarms: {
    create: jest.fn(),
    onAlarm: {
      addListener: jest.fn(),
    },
  },
  notifications: {
    create: jest.fn(),
  },
};
