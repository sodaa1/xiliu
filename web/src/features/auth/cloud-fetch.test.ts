import { afterEach, expect, it, vi } from 'vitest'
import { appFetch } from '../../lib/app-fetch'
import { applySession, currentSession } from './session'

vi.mock('../../lib/runtime-mode', () => ({ isCloud: true, isDemo: false }))
afterEach(() => {
  applySession(null)
  vi.unstubAllGlobals()
})

it('attaches the active workspace and CSRF without persisting credentials', async () => {
  applySession({
    user: { id: 'alice', username: 'alice' },
    workspace: { id: 'workspace-a' },
    csrf_token: 'csrf-a',
    trial: { enabled: true, limit: 5, remaining: 5 },
  })
  const fetcher = vi.fn().mockResolvedValue(new Response('{}'))
  vi.stubGlobal('fetch', fetcher)
  await appFetch('/api/tasks', { method: 'POST', body: '{}' })
  const headers = fetcher.mock.calls[0][1].headers as Headers
  expect(headers.get('X-Workspace-ID')).toBe('workspace-a')
  expect(headers.get('X-CSRF-Token')).toBe('csrf-a')
})

it('clears identity and aborts existing streams when another tab changes account', async () => {
  applySession({
    user: { id: 'alice', username: 'alice' },
    workspace: { id: 'workspace-a' },
    csrf_token: 'csrf-a',
    trial: { enabled: true, limit: 5, remaining: 5 },
  })
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response('{}', {
        status: 409,
        headers: { 'X-Session-Changed': '1' },
      })
    )
  )
  await expect(appFetch('/api/tasks')).rejects.toThrow('会话已失效')
  expect(currentSession()).toBeNull()
})
