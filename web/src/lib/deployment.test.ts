import { afterEach, expect, test, vi } from 'vitest'
import { publicAsset, usesHashRouting } from './deployment'

afterEach(() => vi.unstubAllEnvs())

test('bundled assets follow the deployment base without changing desktop root paths', () => {
  vi.stubEnv('BASE_URL', '/')
  expect(publicAsset('companion/standing.png')).toBe('/companion/standing.png')
  vi.stubEnv('BASE_URL', '/xiliu/')
  expect(publicAsset('companion/standing.png')).toBe('/xiliu/companion/standing.png')
})

test('hash navigation is enabled only for a demo explicitly built for static hosting', () => {
  vi.stubEnv('MODE', 'demo')
  vi.stubEnv('VITE_DEMO_ROUTER', 'hash')
  expect(usesHashRouting()).toBe(true)
  vi.stubEnv('MODE', 'production')
  expect(usesHashRouting()).toBe(false)
  vi.stubEnv('MODE', 'demo')
  vi.stubEnv('VITE_DEMO_ROUTER', '')
  expect(usesHashRouting()).toBe(false)
})
