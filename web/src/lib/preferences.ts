import { useLayoutEffect, useSyncExternalStore } from 'react'
import { saveDesktopPreferences } from '../desktop/bridge'
import { appFetch } from './app-fetch'
import { isDemo } from './runtime-mode'
import { storageKey } from '../features/auth/session'

export interface Preferences {
  displayName: string
  email: string
  bio: string
  avatar: string
  theme: 'light' | 'dark' | 'system'
  fontSize: 'small' | 'medium' | 'large'
  fontFamily: 'system' | 'rounded' | 'serif'
  density: 'comfortable' | 'compact'
  reducedMotion: boolean
}
export const defaultPreferences: Preferences = {
  displayName: '',
  email: '',
  bio: '',
  avatar: '',
  theme: 'light',
  fontSize: 'small',
  fontFamily: 'system',
  density: 'comfortable',
  reducedMotion: false,
}
const key = () => storageKey(isDemo ? 'xiliu-demo-preferences-v1' : 'xiliu-preferences-v1')
let cachedKey = ''
const listeners = new Set<() => void>()
let cachedRaw: string | null | undefined
let cached: Preferences = defaultPreferences
let revision: number | null = null
let storageUnavailable = false
function read(): Preferences {
  if (cachedKey !== key()) {
    cachedKey = key()
    cachedRaw = undefined
    cached = defaultPreferences
    revision = null
    storageUnavailable = false
  }
  if (storageUnavailable) return cached
  let raw: string | null
  try {
    raw = localStorage.getItem(key())
  } catch {
    return cached
  }
  if (raw === cachedRaw) return cached
  cachedRaw = raw
  revision = null
  let value: Partial<Preferences> = {}
  try {
    value = JSON.parse(raw ?? '{}') ?? {}
  } catch {
    /* Invalid local data uses defaults. */
  }
  const result = { ...defaultPreferences }
  for (const field of ['displayName', 'email', 'bio'] as const)
    if (typeof value[field] === 'string')
      result[field] = value[field].slice(0, field === 'bio' ? 300 : 100)
  for (const field of ['theme', 'fontSize', 'fontFamily', 'density'] as const) {
    const choices = {
      theme: ['light', 'dark', 'system'],
      fontSize: ['small', 'medium', 'large'],
      fontFamily: ['system', 'rounded', 'serif'],
      density: ['comfortable', 'compact'],
    }
    if (choices[field].includes(String(value[field])))
      Object.assign(result, { [field]: value[field] })
  }
  result.reducedMotion = value.reducedMotion === true
  if (
    typeof value.avatar === 'string' &&
    value.avatar.length <= 220000 &&
    /^data:image\/(webp|png|jpeg);base64,[A-Za-z0-9+/=]+$/.test(value.avatar)
  )
    result.avatar = value.avatar
  return (cached = result)
}
function emit() {
  listeners.forEach((listener) => listener())
}
function subscribe(listener: () => void) {
  listeners.add(listener)
  if (listeners.size === 1) {
    void syncPreferences().catch(() => {})
    polling = window.setInterval(() => void syncPreferences().catch(() => {}), 2000)
    window.addEventListener('focus', refresh)
  }
  const storage = (event: StorageEvent) => {
    if (event.key === key() || event.key === null) {
      emit()
      refresh()
    }
  }
  window.addEventListener('storage', storage)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', storage)
    if (!listeners.size) {
      window.clearInterval(polling)
      window.removeEventListener('focus', refresh)
    }
  }
}
type Snapshot = { preferences: Preferences; revision: number; initialized: boolean }
let polling: number | undefined
let queue: Promise<void> = Promise.resolve()
function refresh() {
  void syncPreferences().catch(() => {})
}
function enqueue(operation: () => Promise<void>): Promise<void> {
  const next = queue.catch(() => {}).then(operation)
  queue = next
  return next
}
async function request(method = 'GET', body?: unknown): Promise<Snapshot> {
  const response = await appFetch('/api/settings/preferences', {
    method,
    ...(body
      ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      : {}),
  })
  if (!response.ok) {
    if (response.status === 409) throw new Error('偏好已在其他窗口或助手中更新，请检查后重试。')
    throw new Error('无法同步本机偏好，请重试保存。')
  }
  const snapshot = (await response.json()) as Snapshot
  if (
    !Number.isInteger(snapshot.revision) ||
    snapshot.revision < 0 ||
    typeof snapshot.initialized !== 'boolean' ||
    !snapshot.preferences ||
    typeof snapshot.preferences !== 'object'
  )
    throw new Error('本机偏好同步格式不正确。')
  return snapshot
}
function accept(snapshot: Snapshot) {
  if (!snapshot.initialized) {
    // Do not manufacture a legacy seed on a browser with no previous preferences.
    const changed = revision !== snapshot.revision
    revision = snapshot.revision
    if (changed) emit()
    return
  }
  const json = JSON.stringify(snapshot.preferences)
  try {
    localStorage.setItem(key(), json)
    storageUnavailable = false
  } catch {
    // The authoritative SQLite write remains durable without browser storage.
    storageUnavailable = true
  }
  const changed = json !== cachedRaw || revision !== snapshot.revision
  if (json !== cachedRaw) cached = snapshot.preferences
  cachedRaw = json
  revision = snapshot.revision
  if (changed) emit()
}
async function synchronize() {
  const legacy = read()
  const hasLegacy = cachedRaw !== null && cachedRaw !== undefined
  let snapshot = await request()
  if (!snapshot.initialized && hasLegacy) {
    try {
      snapshot = await request('PUT', { changes: legacy, expected_revision: 0 })
    } catch {
      // A concurrent migration or Agent write wins; never retry the stale seed.
      snapshot = await request()
      if (!snapshot.initialized) throw new Error('旧偏好尚未同步，请重试保存。')
    }
  }
  accept(snapshot)
}
export function syncPreferences(): Promise<void> {
  return enqueue(synchronize)
}
export function savePreferences(
  changes: Partial<Preferences>,
  expectedRevision?: number
): Promise<void> {
  return enqueue(async () => {
    if (revision === null) await synchronize()
    let snapshot: Snapshot
    try {
      snapshot = await request('PUT', { changes, expected_revision: expectedRevision ?? revision })
    } catch (error) {
      // Update the shared view, while the Personal form keeps its unsaved draft.
      try {
        accept(await request())
      } catch {
        /* Keep the last known view while offline. */
      }
      throw error
    }
    accept(snapshot)
    try {
      if (!isDemo) await saveDesktopPreferences(JSON.stringify(snapshot.preferences))
    } catch {
      throw new Error('本机偏好已保存，但桌面备份未保存，请重试保存。')
    }
  })
}
export function usePreferences() {
  return useSyncExternalStore(subscribe, read, () => defaultPreferences)
}
function readRevision() {
  read()
  return revision ?? 0
}
export function usePreferenceRevision() {
  return useSyncExternalStore(subscribe, readRevision, () => 0)
}
export function useApplyPreferences() {
  const preferences = usePreferences()
  useLayoutEffect(() => {
    const root = document.documentElement
    const system = window.matchMedia?.('(prefers-color-scheme: dark)')
    function apply() {
      const theme =
        preferences.theme === 'system' ? (system?.matches ? 'dark' : 'light') : preferences.theme
      root.dataset.theme = theme
      root.style.colorScheme = theme
      root.style.fontSize = `${{ small: 14, medium: 16, large: 18 }[preferences.fontSize]}px`
      root.style.setProperty(
        '--app-font',
        {
          system:
            "'PingFang SC', 'Microsoft YaHei UI', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans SC', 'Segoe UI', sans-serif",
          rounded: "'Microsoft YaHei UI', 'Yu Gothic UI', 'Segoe UI', sans-serif",
          serif: "'Noto Serif SC', 'Songti SC', SimSun, serif",
        }[preferences.fontFamily]
      )
      root.dataset.density = preferences.density
      root.dataset.motion = preferences.reducedMotion ? 'reduced' : 'system'
    }
    apply()
    system?.addEventListener('change', apply)
    return () => system?.removeEventListener('change', apply)
  }, [preferences])
}
