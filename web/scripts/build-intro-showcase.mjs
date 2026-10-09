import { build } from 'vite'
import react from '@vitejs/plugin-react'
import { cpSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = fileURLToPath(new URL('..', import.meta.url))
const output = path.join(webRoot, '.preview', 'xiliu-showcase')
await build({
  configFile: false,
  root: webRoot,
  base: './',
  publicDir: false,
  plugins: [react()],
  build: {
    outDir: output,
    emptyOutDir: true,
    rollupOptions: { input: path.join(webRoot, 'intro', 'index.html') },
  },
})

const html = readFileSync(path.join(output, 'intro', 'index.html'), 'utf8')
  .replace('<html lang="zh-CN">', '<html lang="zh-CN" data-showcase="public">')
  .replaceAll('../assets/', './assets/')
  .replace('/intro/favicon.svg', './favicon.svg')
  .replace(
    '</head>',
    '  <link rel="canonical" href="https://933693.xyz/projects/xiliu/" />\n  </head>'
  )
writeFileSync(path.join(output, 'index.html'), html)
cpSync(path.join(webRoot, 'public', 'intro', 'favicon.svg'), path.join(output, 'favicon.svg'))
mkdirSync(path.join(output, 'assets'), { recursive: true })
console.log(`Standalone public showcase: ${output}`)
