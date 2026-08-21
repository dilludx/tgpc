import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import tsParser from '@typescript-eslint/parser';
import globals from 'globals';

export default [
  { ignores: ['.svelte-kit/', 'node_modules/', 'build/', 'dist/', '**/*.d.ts'] },
  js.configs.recommended,
  ...svelte.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.node }
    }
  },
  {
    files: ['**/*.ts'],
    languageOptions: {
      parser: tsParser
    },
    rules: {
      // tsc reports undefined globals; core no-undef cannot see TS ambient
      // namespaces like App.Platform and false-positives on them.
      'no-undef': 'off'
    }
  },
  {
    files: ['**/*.svelte'],
    languageOptions: {
      parserOptions: {
        // Parse <script lang="ts"> blocks with the TypeScript parser.
        parser: tsParser
      }
    }
  },
  {
    rules: {
      'no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      // Best-effort try/catch blocks are intentional in this codebase.
      'no-empty': ['error', { allowEmptyCatch: true }],
      // Existing each blocks predate this gate; keying them is a behavior-
      // sensitive refactor tracked separately. Warn, don't block.
      'svelte/require-each-key': 'warn',
      // App serves from the site root; resolve() adds nothing here.
      'svelte/no-navigation-without-resolve': 'off'
    }
  },
  {
    files: ['**/*.svelte'],
    rules: {
      // Svelte 5 runes ($state, $derived, $effect) are globals provided by the compiler.
      'no-undef': 'off'
    }
  }
];
