import type { ChatRun } from '../lib/types'
import { storageKey } from '../features/auth/session'

export const DEFAULT_PET_HEIGHT = 96
export const PET_SCALES = [100, 125, 150, 175, 200] as const
export const DEFAULT_COMPANION_SETTINGS: CompanionSettings = {
  enabled: true,
  visible: true,
  height: 96,
  alwaysOnTop: true,
  form: 'chibi',
  chibiScale: 100,
  standingScale: 100,
}
const PREVIEW_SETTINGS_KEY = 'xiliu.companion.preview-settings'
export function petScale(settings: CompanionSettings, form: 'chibi' | 'standing') {
  const raw =
    form === 'chibi'
      ? (settings.chibiScale ?? (settings.height / 96) * 100)
      : (settings.standingScale ?? 100)
  return Number.isFinite(raw) ? Math.round(Math.max(100, Math.min(200, raw)) / 25) * 25 : 100
}
export function petHeight(settings: CompanionSettings) {
  const form = settings.form === 'standing' ? 'standing' : 'chibi'
  return Math.round(((form === 'standing' ? 168 : 96) * petScale(settings, form)) / 100)
}
export function previewSettings(): CompanionSettings {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey(PREVIEW_SETTINGS_KEY)) ?? 'null')
    return { ...DEFAULT_COMPANION_SETTINGS, ...saved }
  } catch {
    return { ...DEFAULT_COMPANION_SETTINGS }
  }
}
export function savePreviewSettings(settings: CompanionSettings) {
  const saved = { ...settings, height: petHeight(settings) }
  localStorage.setItem(storageKey(PREVIEW_SETTINGS_KEY), JSON.stringify(saved))
  window.dispatchEvent(new Event('companion-preview-settings'))
  return saved
}
export type CompanionStatus = {
  phase: 'idle' | 'thinking' | 'success' | 'error'
  cid: string | null
  message: string
  count: number
}
export type CompanionSnapshot = CompanionStatus & { revision: number }
export type CompanionSettings = {
  enabled: boolean
  visible: boolean
  height: number
  alwaysOnTop: boolean
  form?: 'chibi' | 'standing'
  chibiScale?: number
  standingScale?: number
}
export type QuickRequest = {
  requestId: string
  text: string
  status: 'pending' | 'accepted' | 'failed'
  cid: string | null
  error: string | null
}
export const idleStatus: CompanionStatus = { phase: 'idle', cid: null, message: '', count: 0 }

export function describeRuns(
  runs: Record<string, ChatRun>,
  errors: Record<string, string>,
  selected: string | null
): CompanionStatus {
  const active = Object.values(runs)
  const run = (selected && runs[selected]) || active.sort((a, b) => b.startedAt - a.startedAt)[0]
  if (run)
    return {
      phase: 'thinking',
      cid: run.cid || null,
      message: run.status.replace(/\s+/g, ' ').trim().slice(0, 80),
      count: active.length,
    }
  const failure =
    Object.entries(errors).find(([id]) => id === selected) ?? Object.entries(errors)[0]
  if (failure)
    return {
      phase: 'error',
      cid: failure[0] || null,
      message: '这次任务未完成，点击查看详情',
      count: 0,
    }
  return idleStatus
}
export function acceptSnapshot(current: CompanionSnapshot, incoming: CompanionSnapshot) {
  return incoming.revision > current.revision ? incoming : current
}
export async function companionCall<T>(
  command: string,
  args: Record<string, unknown> = {}
): Promise<T> {
  if (!window.__TAURI__?.core) throw new Error('请在息流桌面版中使用这个功能。')
  return (await window.__TAURI__.core.invoke(`companion_${command}`, args)) as T
}
export async function companionListen<T>(name: string, handler: (payload: T) => void) {
  const event = window.__TAURI__?.event
  if (!event) throw new Error('桌面事件接口不可用。')
  return event.listen<T>(`companion-${name}`, (event) => handler(event.payload))
}
