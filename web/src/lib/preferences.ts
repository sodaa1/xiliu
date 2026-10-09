import { useLayoutEffect, useSyncExternalStore } from 'react'
import { saveDesktopPreferences } from '../desktop/bridge'

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
const key = 'xiliu-preferences-v1'
const listeners = new Set<() => void>()
let cachedRaw: string | null | undefined
let cached: Preferences = defaultPreferences
function read(): Preferences {
  let raw: string | null
  try {
    raw = localStorage.getItem(key)
  } catch {
    return cached
  }
  if (raw === cachedRaw) return cached
  cachedRaw = raw
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
  const storage = (event: StorageEvent) => {
    if (event.key === key || event.key === null) emit()
  }
  window.addEventListener('storage', storage)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', storage)
  }
}
let nativeSaveQueue: Promise<void> = Promise.resolve()
export async function savePreferences(changes: Partial<Preferences>): Promise<void> {
  const updated = { ...read(), ...changes }
  const json = JSON.stringify(updated)
  try {
    localStorage.setItem(key, json)
  } catch {
    throw new Error('无法保存到此浏览器，请检查存储空间或隐私设置。')
  }
  emit()
  // Preserve call order even when appearance controls are changed rapidly.
  const write = nativeSaveQueue.catch(() => {}).then(() => saveDesktopPreferences(json))
  nativeSaveQueue = write
  try {
    await write
  } catch {
    throw new Error('当前窗口的偏好已生效，但桌面备份未保存，重启后可能恢复旧设置。请重试保存。')
  }
}
export function usePreferences() {
  return useSyncExternalStore(subscribe, read, () => defaultPreferences)
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
          system: "Inter, 'Segoe UI', 'Microsoft YaHei', sans-serif",
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
