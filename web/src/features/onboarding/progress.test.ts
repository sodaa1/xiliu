import { beforeEach, expect, test, vi } from 'vitest'
import { createSeed } from '../demo/seed'
import {
  getGuideProgress,
  startGuide,
  dismissGuide,
  resetGuide,
  recordGuideAction,
} from './progress'
beforeEach(() => {
  localStorage.clear()
  resetGuide()
})
const item = () => createSeed().content[0]
test('guide resumes dismissed progress but can also restart from the beginning', () => {
  expect(getGuideProgress().status).toBe('new')
  startGuide()
  recordGuideAction({ type: 'saved', item: item() })
  dismissGuide()
  expect(getGuideProgress()).toMatchObject({ status: 'dismissed', step: 1 })
  startGuide()
  expect(getGuideProgress()).toMatchObject({ status: 'active', step: 1 })
  resetGuide()
  startGuide()
  expect(getGuideProgress()).toMatchObject({ status: 'active', step: 0 })
})
test('only the matching saved, archived and successfully referenced document advances the guide', () => {
  const saved = item()
  startGuide()
  recordGuideAction({ type: 'saved', item: saved })
  recordGuideAction({ type: 'archived', items: [{ ...saved, id: 'other', status: 'knowledge' }] })
  expect(getGuideProgress().step).toBe(1)
  recordGuideAction({ type: 'archived', items: [{ ...saved, status: 'knowledge' }] })
  expect(getGuideProgress().step).toBe(2)
  recordGuideAction({
    type: 'asked',
    documentId: saved.id,
    referenceTitle: saved.title,
    outcome: 'stopped',
  })
  recordGuideAction({
    type: 'asked',
    documentId: 'other',
    referenceTitle: saved.title,
    outcome: 'success',
  })
  expect(getGuideProgress().status).toBe('active')
  recordGuideAction({
    type: 'asked',
    documentId: saved.id,
    referenceTitle: saved.title,
    outcome: 'success',
  })
  expect(getGuideProgress()).toMatchObject({ status: 'completed', step: 3 })
})
test('demo onboarding never consumes the normal progress', async () => {
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
