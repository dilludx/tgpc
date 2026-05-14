import js from '@eslint/js';

export default [
  js.configs.recommended,
  {
    languageOptions: {
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        alert: 'readonly',
        Response: 'readonly',
        Blob: 'readonly',
        fetch: 'readonly',
        localStorage: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        location: 'readonly',
        URL: 'readonly',
        navigator: 'readonly',
      },
    },
    rules: {
      'no-redeclare': 'error',
      'no-unused-vars': 'warn',
      'no-undef': 'error',
    },
  },
];
