import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import hooks from 'eslint-plugin-react-hooks'
import refresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
export default tseslint.config(
  { ignores: ['dist', 'dist-demo', 'node_modules', '.preview'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/components/react-bits/*.jsx'],
    languageOptions: { globals: globals.browser },
    rules: {
      'no-empty': ['error', { allowEmptyCatch: true }],
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z]' }],
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { 'react-hooks': hooks, 'react-refresh': refresh },
    rules: {
      ...hooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
  { files: ['eslint.config.js', 'scripts/*.mjs'], languageOptions: { globals: globals.node } }
)
