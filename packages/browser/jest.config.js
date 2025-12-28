/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/src'],
  testMatch: ['**/*.test.ts', '**/*.spec.ts', '**/*.test.tsx', '**/*.spec.tsx'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  collectCoverageFrom: [
    'src/**/*.ts',
    'src/**/*.tsx',
    '!src/**/*.d.ts',
    '!src/**/*.test.ts',
    '!src/**/*.test.tsx',
    '!src/content/index.ts', // Content script requires browser APIs
    '!src/background/index.ts', // Background script requires chrome APIs
  ],
  coverageThreshold: {
    global: {
      branches: 35,
      functions: 35,
      lines: 45,
      statements: 45,
    },
  },
  // Mock chrome API
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
};
