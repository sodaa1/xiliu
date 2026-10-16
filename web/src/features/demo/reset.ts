import type { QueryClient } from '@tanstack/react-query'
import { cancelAllDemoChats } from './chat'
import { resetDemoState } from './store'

export async function resetDemoExperience(cache: QueryClient) {
  cancelAllDemoChats()
  await cache.cancelQueries()
  await resetDemoState()
  for (const key of ['xiliu-demo-preferences-v1', 'xiliu-demo-guide-v1']) {
    try {
      localStorage.removeItem(key)
    } catch {
      /* Memory-only experience remains usable. */
    }
  }
  cache.clear()
  window.dispatchEvent(new StorageEvent('storage', { key: 'xiliu-demo-preferences-v1' }))
  window.dispatchEvent(new Event('xiliu-demo-reset'))
}
