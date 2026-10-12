import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'node:fs'
import { dependencyAliases, siteRoot } from '../docs/web/scripts/config.mjs'
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'xiliu-introduction-preview',
      configureServer(server) {
        server.middlewares.use('/intro', async (request, response, next) => {
          if (request.url === '/favicon.svg') {
            response.setHeader('Content-Type', 'image/svg+xml')
            response.end(readFileSync(`${siteRoot}/public/favicon.svg`))
            return
          }
          if (!['/', '', '/index.html'].includes(request.url?.split('?')[0] ?? '')) return next()
          const source = readFileSync(`${siteRoot}/index.html`, 'utf8')
            .replace(' data-showcase="public"', '')
            .replace('./favicon.svg', '/intro/favicon.svg')
            .replace('./src/main.tsx', `/@fs/${siteRoot.replaceAll('\\', '/')}/src/main.tsx`)
          response.setHeader('Content-Type', 'text/html; charset=utf-8')
          response.end(await server.transformIndexHtml('/intro/', source))
        })
      },
    },
  ],
  resolve: { alias: dependencyAliases, dedupe: ['react', 'react-dom'] },
  build: {
    rollupOptions: {
      input: {
        app: fileURLToPath(new URL('./index.html', import.meta.url)),
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8765' },
    fs: { allow: [fileURLToPath(new URL('..', import.meta.url))] },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
    include: ['src/**/*.test.{ts,tsx}', '../docs/web/src/**/*.test.{ts,tsx}'],
  },
})
