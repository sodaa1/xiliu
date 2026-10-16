import type { ContentItem } from '../../lib/workspace-api'
import type { ChatOutcome } from '../../lib/types'
import { isDemo } from '../../lib/runtime-mode'

export interface GuideProgress {
  version: 1
  status: 'new' | 'active' | 'dismissed' | 'completed'
  step: 0 | 1 | 2 | 3
  itemId?: string
  referenceTitle?: string
}
export type GuideAction =
  | { type: 'saved'; item: ContentItem }
  | { type: 'archived'; items: ContentItem[] }
  | { type: 'asked'; documentId?: string; referenceTitle: string; outcome: ChatOutcome }
const key = isDemo ? 'xiliu-demo-guide-v1' : 'xiliu-guide-v1'
const fresh: GuideProgress = { version: 1, status: 'new', step: 0 }
let cached: GuideProgress = fresh,
  rawCache: string | null | undefined,
  memoryOnly = false
const listeners = new Set<() => void>()
export function getGuideProgress(): GuideProgress {
  if (memoryOnly) return cached
  try {
    const raw = localStorage.getItem(key)
    if (raw === rawCache) return cached
    rawCache = raw
    const value = JSON.parse(raw ?? 'null')
    cached =
      value &&
      value.version === 1 &&
      ['new', 'active', 'dismissed', 'completed'].includes(value.status) &&
      [0, 1, 2, 3].includes(value.step) &&
      (value.itemId === undefined || typeof value.itemId === 'string')
        ? value
        : fresh
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
    localStorage.setItem(key, rawCache)
  } catch {
    memoryOnly = true
  }
  emit()
}
export function subscribeGuide(listener: () => void) {
  listeners.add(listener)
  const onStorage = (event: StorageEvent) => {
    if (event.key === key || event.key === null) emit()
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
  const previous = getGuideProgress()
  write({ ...(previous.step === 3 ? fresh : previous), status: 'active' })
}
export function dismissGuide() {
  write({ ...getGuideProgress(), status: 'dismissed' })
}
export function resetGuide() {
  write({ ...fresh })
}
export function recordGuideAction(action: GuideAction) {
  const state = getGuideProgress()
  if (state.status !== 'active') return
  if (state.step === 0 && action.type === 'saved')
    write({ ...state, step: 1, itemId: action.item.id, referenceTitle: action.item.title })
  if (state.step === 1 && action.type === 'archived') {
    const item = action.items.find(
      (item) => item.id === state.itemId && item.status === 'knowledge' && item.tags.length > 0
    )
    if (item) write({ ...state, step: 2, referenceTitle: item.title })
  }
  if (
    state.step === 2 &&
    action.type === 'asked' &&
    action.documentId === state.itemId &&
    action.outcome === 'success'
  )
    write({ ...state, step: 3, status: 'completed' })
}
