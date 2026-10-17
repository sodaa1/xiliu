import { useState } from 'react'
import { isDemo } from './runtime-mode'
import { storageKey as scopedKey } from '../features/auth/session'

export function usePanelSize(key: string, min: number, max: number, initial = max) {
  const storageKey = scopedKey(isDemo ? key.replace(/^xiliu-/, 'xiliu-demo-') : key)
  const fallback = Math.max(min, Math.min(max, initial))
  const [value, setValue] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      const size = saved === null ? fallback : Number(saved)
      return Number.isFinite(size) ? Math.max(min, Math.min(max, size)) : fallback
    } catch {
      return fallback
    }
  })
  return [
    value,
    (next: number) => {
      const size = Math.max(min, Math.min(max, next))
      setValue(size)
      try {
        localStorage.setItem(storageKey, String(size))
      } catch {
        /* Optional browser storage. */
      }
    },
  ] as const
}
