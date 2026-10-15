import { useState } from 'react'

export function usePanelSize(key: string, min: number, max: number, initial = max) {
  const fallback = Math.max(min, Math.min(max, initial))
  const [value, setValue] = useState(() => {
    try {
      const saved = localStorage.getItem(key)
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
        localStorage.setItem(key, String(size))
      } catch {
        /* Optional browser storage. */
      }
    },
  ] as const
}
