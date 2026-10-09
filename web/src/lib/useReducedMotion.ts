import { useSyncExternalStore } from 'react'
import { usePreferences } from './preferences'

const query = '(prefers-reduced-motion: reduce)'
const read = () => window.matchMedia?.(query).matches ?? false
function subscribe(callback: () => void) {
  const media = window.matchMedia?.(query)
  media?.addEventListener('change', callback)
  return () => media?.removeEventListener('change', callback)
}

export function useReducedMotion() {
  const preferences = usePreferences()
  const system = useSyncExternalStore(subscribe, read, () => false)
  return preferences.reducedMotion || system
}
