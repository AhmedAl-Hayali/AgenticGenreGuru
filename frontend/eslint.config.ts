import js from "@eslint/js";
import vitest from "@vitest/eslint-plugin";
import prettier from "eslint-config-prettier";
import globals from "globals";
import { defineConfig } from "eslint/config";
import tseslint from "typescript-eslint";

export default defineConfig(
  {
    ignores: [
      "node_modules/",
      "coverage/",
      "logs/",
      "fingerprint_app/static/fingerprint_app/app.js",
      "fingerprint_app/static/fingerprint_app/app.js.map",
    ],
  },
  {
    files: ["fingerprint_app/ts/**/*.ts", "tests/**/*.ts"],
    languageOptions: { globals: globals.browser },
  },
  {
    files: ["tests/**/*.ts"],
    plugins: { vitest },
    rules: { ...vitest.configs.recommended.rules },
  },
  {
    files: ["eslint.config.ts", "vitest.config.ts"],
    languageOptions: { globals: globals.node },
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  prettier,
);
