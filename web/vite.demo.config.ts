import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { dependencyAliases } from '../docs/web/scripts/config.mjs'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: dependencyAliases, dedupe: ['react', 'react-dom'] },
  build: { outDir: 'dist-demo', emptyOutDir: true },
  server: { host: '127.0.0.1', port: 5184, strictPort: true },
  preview: { host: '127.0.0.1', port: 5184, strictPort: true },
})
