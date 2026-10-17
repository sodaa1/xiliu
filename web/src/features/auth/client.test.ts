import { afterEach, expect, it, vi } from 'vitest'
import { authenticate, loadSession } from './client'

afterEach(() => vi.unstubAllGlobals())
it('sends credentials only to the same-origin identity endpoint', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response('{}'))
  vi.stubGlobal('fetch', fetcher)
  const storage = vi.spyOn(Storage.prototype, 'setItem')
  await authenticate('login', 'alice', 'long-enough-password')
  expect(fetcher.mock.calls[0][0]).toBe('/api/auth/login')
  expect(fetcher.mock.calls[0][1].credentials).toBe('same-origin')
  expect(storage).not.toHaveBeenCalled()
})
it('treats missing identity as signed out and preserves server error messages', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })))
  expect(await loadSession()).toBeNull()
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ error: { message: '账号或密码不正确。' } }), { status: 401 })
      )
  )
  await expect(authenticate('login', 'alice', 'incorrect-password')).rejects.toThrow(
    '账号或密码不正确。'
  )
})
