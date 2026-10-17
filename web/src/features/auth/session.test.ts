import { afterEach, describe, expect, it, vi } from 'vitest'
import { applySession, currentSession, sessionSignal, storageKey } from './session'

const alice = {
  user: { id: 'alice', username: 'alice' },
  workspace: { id: 'workspace-a' },
  csrf_token: 'csrf-a',
  trial: { enabled: true, limit: 5, remaining: 5 },
}

afterEach(() => {
  applySession(null)
  vi.restoreAllMocks()
})

describe('cloud session boundary', () => {
  it('aborts old work and discards all account data on logout', () => {
    applySession(alice)
    const old = sessionSignal()
    applySession(null)
    expect(old.aborted).toBe(true)
    expect(currentSession()).toBeNull()
  })
  it('partitions storage by workspace when explicitly cloud built', async () => {
    vi.resetModules()
    vi.doMock('../../lib/runtime-mode', () => ({ isCloud: true, isDemo: false }))
    const session = await import('./session')
    session.applySession(alice)
    const first = session.storageKey('draft')
    session.applySession({ ...alice, workspace: { id: 'workspace-b' } })
    expect(session.storageKey('draft')).not.toBe(first)
    expect(session.storageKey('draft')).toContain('workspace-b')
    vi.doUnmock('../../lib/runtime-mode')
  })
  it('leaves desktop storage names unchanged', () => {
    expect(storageKey('xiliu-preferences-v1')).toBe('xiliu-preferences-v1')
  })
})
