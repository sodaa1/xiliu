import type { ChatRun } from '../lib/types'

export const DEFAULT_PET_HEIGHT = 96
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
