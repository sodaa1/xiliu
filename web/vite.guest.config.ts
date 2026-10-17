import { defineConfig, mergeConfig } from 'vite'
import demo from './vite.demo.config'

export default mergeConfig(
  demo,
  defineConfig({
    base: '/demo/',
    define: { 'import.meta.env.VITE_DEMO_ROUTER': JSON.stringify('hash') },
    build: { outDir: 'dist-guest', emptyOutDir: true },
  })
)
