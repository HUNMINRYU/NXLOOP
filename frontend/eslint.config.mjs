import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    ".next-e2e/**",
    "out/**",
    "build/**",
    "dist/**",
    "next-env.d.ts",
  ]),
  // Project-specific rule relaxation: some effects intentionally initialize state.
  // 발표/데모 전에는 이 규칙이 너무 엄격해 기본 UI까지 막을 수 있어 warn으로 낮춘다.
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  // Ensure our overrides apply after next/core configs.
  // (eslint-config-next sets set-state-in-effect to error.)
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
