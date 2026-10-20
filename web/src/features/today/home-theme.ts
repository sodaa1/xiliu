import { useSyncExternalStore } from 'react'
import { isDemo } from '../../lib/runtime-mode'
import { storageKey } from '../auth/session'
export type HomeTheme = 'original' | 'workbench'
const key = () => storageKey(isDemo ? 'xiliu-demo-home-theme-v1' : 'xiliu-home-theme-v1')
const event = 'xiliu-home-theme'
let cachedKey = '',
  memory: HomeTheme = 'original',
  memoryOnly = false
function read(): HomeTheme {
  if (cachedKey !== key()) {
    cachedKey = key()
    memory = 'original'
    memoryOnly = false
  }
  if (memoryOnly) return memory
  try {
    return localStorage.getItem(key()) === 'workbench' ? 'workbench' : 'original'
  } catch {
    return memory
  }
}
function subscribe(callback: () => void) {
  const storage = (change: StorageEvent) => {
    if (change.key === key() || change.key === null) callback()
  }
  window.addEventListener(event, callback)
  window.addEventListener('storage', storage)
  return () => {
    window.removeEventListener(event, callback)
    window.removeEventListener('storage', storage)
  }
}
export function setHomeTheme(theme: HomeTheme) {
  cachedKey = key()
  memory = theme
  try {
    localStorage.setItem(key(), theme)
    memoryOnly = false
  } catch {
    memoryOnly = true
  }
  window.dispatchEvent(new Event(event))
}
export function useHomeTheme() {
  return useSyncExternalStore(subscribe, read, () => 'original' as const)
}
