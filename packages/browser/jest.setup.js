// Jest setup file
// Mock chrome API and browser APIs for testing

// Polyfill for structuredClone (required by fake-indexeddb in Node < 17)
if (typeof structuredClone === 'undefined') {
  global.structuredClone = (obj) => JSON.parse(JSON.stringify(obj));
}

// Mock Canvas API (JSDOM doesn't implement it)
HTMLCanvasElement.prototype.getContext = jest.fn((contextType) => {
  if (contextType === '2d') {
    return {
      fillText: jest.fn(),
      textBaseline: '',
      font: '',
      fillStyle: '',
      fillRect: jest.fn(),
      clearRect: jest.fn(),
      getImageData: jest.fn(() => ({ data: new Uint8ClampedArray(4) })),
      putImageData: jest.fn(),
      createImageData: jest.fn(() => ({ data: new Uint8ClampedArray(4) })),
      setTransform: jest.fn(),
      drawImage: jest.fn(),
      save: jest.fn(),
      restore: jest.fn(),
      beginPath: jest.fn(),
      moveTo: jest.fn(),
      lineTo: jest.fn(),
      closePath: jest.fn(),
      stroke: jest.fn(),
      fill: jest.fn(),
      translate: jest.fn(),
      scale: jest.fn(),
      rotate: jest.fn(),
      arc: jest.fn(),
      measureText: jest.fn(() => ({ width: 0 })),
    };
  }
  if (contextType === 'webgl' || contextType === 'experimental-webgl') {
    return {
      getExtension: jest.fn(() => ({
        UNMASKED_VENDOR_WEBGL: 37445,
        UNMASKED_RENDERER_WEBGL: 37446,
      })),
      getParameter: jest.fn((param) => {
        if (param === 37445) return 'Mock Vendor';
        if (param === 37446) return 'Mock Renderer';
        return null;
      }),
    };
  }
  return null;
});

HTMLCanvasElement.prototype.toDataURL = jest.fn(() => 'data:image/png;base64,mockImageData');

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
