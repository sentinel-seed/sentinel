import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm", "cjs"],
  dts: true,
  sourcemap: true,
  clean: true,
  splitting: false,
  treeshake: true,
  outDir: "dist",
  target: "es2022",
  external: ["@solana/web3.js", "solana-agent-kit"],
  esbuildOptions(options) {
    // Suppress named/default export warning for CJS
    options.logOverride = {
      "commonjs-variable-in-esm": "silent",
    };
  },
});
