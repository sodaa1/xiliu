import { useEffect, useState } from 'react'
import { isDemo } from '../../lib/runtime-mode'
import { storageKey } from '../auth/session'
export function useHomeDraft() {
  const key = storageKey(isDemo ? 'xiliu-demo-home-draft' : 'xiliu-home-draft')
  const [draft, setDraft] = useState(() => {
    try {
      return sessionStorage.getItem(key) ?? ''
    } catch {
      return ''
    }
  })
  useEffect(() => {
    try {
      if (draft) sessionStorage.setItem(key, draft)
      else sessionStorage.removeItem(key)
    } catch {
      /* Keep the in-memory draft. */
    }
  }, [key, draft])
  return [draft, setDraft] as const
}
