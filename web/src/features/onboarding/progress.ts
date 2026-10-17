import { isDemo } from '../../lib/runtime-mode'
import { tourSteps } from './steps'
import { storageKey } from '../auth/session'
export interface GuideProgress {
  version: 2
  status: 'new' | 'active' | 'dismissed' | 'completed'
  step: number
}
const key = () => storageKey(isDemo ? 'xiliu-demo-guide-v1' : 'xiliu-guide-v1')
let cachedKey = ''
const fresh: GuideProgress = { version: 2, status: 'new', step: 0 }
let cached = fresh
let rawCache: string | null | undefined
let memoryOnly = false
const listeners = new Set<() => void>()
export function getGuideProgress(): GuideProgress {
  if (cachedKey !== key()) {
    cachedKey = key()
    rawCache = undefined
    cached = fresh
    memoryOnly = false
  }
  if (memoryOnly) return cached
  try {
    const raw = localStorage.getItem(key())
    if (raw === rawCache) return cached
    rawCache = raw
    const value = JSON.parse(raw ?? 'null')
    if (value?.version === 1) {
      cached = ['dismissed', 'completed'].includes(value.status)
        ? { ...fresh, status: value.status }
        : fresh
    } else {
      cached =
        value?.version === 2 &&
        ['new', 'active', 'dismissed', 'completed'].includes(value.status) &&
        Number.isInteger(value.step) &&
        value.step >= 0 &&
        value.step < tourSteps.length
          ? value
          : fresh
    }
  } catch {
    cached = fresh
  }
  return cached
}
function emit() {
  listeners.forEach((listener) => listener())
}
function write(value: GuideProgress) {
  cached = value
  try {
    rawCache = JSON.stringify(value)
    localStorage.setItem(key(), rawCache)
  } catch {
    memoryOnly = true
  }
  emit()
}
export function subscribeGuide(listener: () => void) {
  listeners.add(listener)
  const onStorage = (event: StorageEvent) => {
    if (event.key === key() || event.key === null) emit()
  }
  window.addEventListener('storage', onStorage)
  window.addEventListener('xiliu-demo-reset', emit)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', onStorage)
    window.removeEventListener('xiliu-demo-reset', emit)
  }
}
export function startGuide() {
  write({ ...fresh, status: 'active' })
}
export function resetGuide() {
  write({ ...fresh })
}
export function dismissGuide() {
  write({ ...getGuideProgress(), status: 'dismissed' })
}
export function finishGuide() {
  write({ ...getGuideProgress(), status: 'completed' })
}
export function moveGuide(offset: number) {
  const previous = getGuideProgress()
  write({
    version: 2,
    status: 'active',
    step: Math.max(0, Math.min(tourSteps.length - 1, previous.step + offset)),
  })
}
