import { useState } from 'react'

export function usePanelSize(key: string, min: number, max: number) {
  const [value, setValue] = useState(() => {
    try {
      const saved = localStorage.getItem(key)
      const size = saved === null ? max : Number(saved)
      return Number.isFinite(size) ? Math.max(min, Math.min(max, size)) : max
    } catch {
      return max
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
