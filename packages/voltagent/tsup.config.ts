import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    'guardrails/index': 'src/guardrails/index.ts',
    'validators/index': 'src/validators/index.ts',
  },
  format: ['cjs', 'esm'],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
  treeshake: true,
  minify: false,
  target: 'node18',
  outDir: 'dist',
  external: ['@voltagent/core'],
  // Bundle sentinel-core since it's not published to npm
  // This ensures the package works standalone without the monorepo
  noExternal: ['@sentinelseed/core'],
});
