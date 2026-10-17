import { useSyncExternalStore } from 'react'
import { isCloud } from '../../lib/runtime-mode'

export interface TrialBalance {
  enabled: boolean
  limit: number
  remaining: number
}
export interface CloudSession {
  user: { id: string; username: string }
  workspace: { id: string }
  csrf_token: string
  trial: TrialBalance
}
let session: CloudSession | null | undefined
let controller = new AbortController()
let source: 'own' | 'trial' = 'own'
const listeners = new Set<() => void>()
const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
const emit = () => listeners.forEach((listener) => listener())
export const currentSession = () => session
export const sessionSignal = () => controller.signal
export const chatSource = () => source
export function applySession(value: CloudSession | null) {
  controller.abort()
  controller = new AbortController()
  session = value
  source = value?.trial.enabled && value.trial.remaining > 0 ? 'trial' : 'own'
  emit()
}
export function updateTrial(trial: TrialBalance) {
  if (session) {
    session = { ...session, trial }
    emit()
  }
}
export function setChatSource(value: 'own' | 'trial') {
  source = value
  emit()
}
export const useCloudSession = () => useSyncExternalStore(subscribe, currentSession)
export const useChatSource = () => useSyncExternalStore(subscribe, chatSource)
export function storageKey(base: string) {
  return isCloud ? `${base}:cloud:${session?.workspace.id ?? 'signed-out'}` : base
}
