import { afterEach, expect, test, vi } from 'vitest'
afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.resetModules()
})
test('normal requests retain their URL, body and cancellation signal', async () => {
  vi.stubEnv('MODE', 'production')
  const fetch = vi.fn().mockResolvedValue(Response.json({ ok: true }))
  vi.stubGlobal('fetch', fetch)
  const { appFetch } = await import('./app-fetch')
  const init = { method: 'PUT', body: '{}', signal: new AbortController().signal }
  await appFetch('/api/settings/preferences', init)
  expect(fetch).toHaveBeenCalledWith('/api/settings/preferences', init)
})
test('demo handles known and unknown requests without any network fallback', async () => {
  vi.stubEnv('MODE', 'demo')
  const fetch = vi.fn(() => {
    throw new Error('must not reach a backend')
  })
  vi.stubGlobal('fetch', fetch)
  const { appFetch } = await import('./app-fetch')
  expect((await appFetch('/api/health')).ok).toBe(true)
  const unknown = await appFetch('/api/not-supported')
  expect(unknown.status).toBe(400)
  expect((await unknown.json()).error.code).toBe('demo_unavailable')
  expect(fetch).not.toHaveBeenCalled()
})
