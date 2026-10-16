import { beforeEach, expect, test, vi } from 'vitest'
import { resetGuide, getGuideProgress, startGuide, dismissGuide } from './progress'
beforeEach(() => {
  localStorage.clear()
  resetGuide()
})
test('previously dismissed or completed guides do not reopen automatically', () => {
  localStorage.setItem(
    'xiliu-guide-v1',
    JSON.stringify({ version: 1, status: 'dismissed', step: 1 })
  )
  expect(getGuideProgress().status).toBe('dismissed')
})
test('demo tour state remains separate from normal mode', async () => {
  startGuide()
  dismissGuide()
  vi.resetModules()
  vi.stubEnv('MODE', 'demo')
  const demo = await import('./progress')
  expect(demo.getGuideProgress().status).toBe('new')
  demo.startGuide()
  expect(JSON.parse(localStorage.getItem('xiliu-guide-v1')!).status).toBe('dismissed')
  vi.unstubAllEnvs()
})
