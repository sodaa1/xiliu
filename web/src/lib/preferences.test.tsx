import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import userEvent from '@testing-library/user-event'

const initial = {
  displayName: '',
  email: '',
  bio: '',
  avatar: '',
  theme: 'light',
  fontSize: 'small',
  fontFamily: 'system',
  density: 'comfortable',
  reducedMotion: false,
}
let current: { preferences: typeof initial; revision: number; initialized: boolean }
let requests: { changes: Record<string, unknown>; expected_revision: number }[]
let rejectNextWrite = false

beforeEach(() => {
  vi.resetModules()
  localStorage.clear()
  current = { preferences: { ...initial }, revision: 0, initialized: false }
  requests = []
  rejectNextWrite = false
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, options?: RequestInit) => {
      if (options?.method === 'PUT') {
        const body = JSON.parse(String(options.body))
        requests.push(body)
        if (rejectNextWrite || body.expected_revision !== current.revision) {
          rejectNextWrite = false
          return new Response(
            JSON.stringify({ error: { code: 'conflict', message: '已在其他窗口更新' } }),
            { status: 409 }
          )
        }
        current = {
          preferences: { ...current.preferences, ...body.changes },
          revision: current.revision + 1,
          initialized: true,
        }
      }
      return new Response(JSON.stringify(current), { status: 200 })
    })
  )
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  delete window.__TAURI__
})

test('durable server preferences remain visible when browser storage is unavailable', async () => {
  current = { preferences: { ...initial, displayName: 'Before' }, revision: 1, initialized: true }
  const preferences = await import('./preferences')
  function Name() {
    return <span>{preferences.usePreferences().displayName}</span>
  }
  render(<Name />)
  await waitFor(() => expect(screen.getByText('Before')).toBeVisible())
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('storage blocked')
  })
  await act(() => preferences.savePreferences({ displayName: 'Durable edit' }))
  expect(current.preferences.displayName).toBe('Durable edit')
  expect(screen.getByText('Durable edit')).toBeVisible()
})

test('migrates browser preferences once without resetting profile or avatar', async () => {
  localStorage.setItem(
    'xiliu-preferences-v1',
    JSON.stringify({
      displayName: 'Browser name',
      theme: 'dark',
      avatar: 'data:image/png;base64,aGVsbG8=',
      api_key: 'secret',
    })
  )
  const preferences = await import('./preferences')
  expect(preferences).toHaveProperty('syncPreferences')
  await preferences.syncPreferences()
  expect(current.preferences.displayName).toBe('Browser name')
  expect(current.preferences.theme).toBe('dark')
  expect(current.preferences.avatar).toBe('data:image/png;base64,aGVsbG8=')
  expect(current.preferences).not.toHaveProperty('api_key')
  await preferences.syncPreferences()
  expect(requests).toHaveLength(1)
})

test('a fresh browser does not initialize defaults that could displace another browser legacy seed', async () => {
  const preferences = await import('./preferences')
  await preferences.syncPreferences()
  await preferences.syncPreferences()
  expect(current.initialized).toBe(false)
  expect(requests).toHaveLength(0)
  expect(localStorage.getItem('xiliu-preferences-v1')).toBeNull()
})

test('server preferences override a stale desktop seed without overwriting agent changes', async () => {
  current = {
    preferences: { ...initial, displayName: 'Agent name', theme: 'dark' },
    revision: 4,
    initialized: true,
  }
  localStorage.setItem(
    'xiliu-preferences-v1',
    JSON.stringify({ displayName: 'Old desktop', theme: 'light' })
  )
  const preferences = await import('./preferences')
  expect(preferences).toHaveProperty('syncPreferences')
  function Name() {
    return <span>{preferences.usePreferences().displayName}</span>
  }
  render(<Name />)
  await act(() => preferences.syncPreferences())
  expect(screen.getByText('Agent name')).toBeVisible()
  expect(JSON.parse(localStorage.getItem('xiliu-preferences-v1')!).theme).toBe('dark')
  expect(requests).toHaveLength(0)
})

test('a rejected stale save displays latest server values without claiming the edit succeeded', async () => {
  current = { preferences: { ...initial, displayName: 'Before' }, revision: 1, initialized: true }
  const preferences = await import('./preferences')
  expect(preferences).toHaveProperty('syncPreferences')
  await preferences.syncPreferences()
  current = {
    preferences: { ...initial, displayName: 'Concurrent agent' },
    revision: 2,
    initialized: true,
  }
  rejectNextWrite = true
  await expect(preferences.savePreferences({ displayName: 'Stale form' })).rejects.toThrow()
  expect(current.preferences.displayName).toBe('Concurrent agent')
  expect(JSON.parse(localStorage.getItem('xiliu-preferences-v1')!).displayName).toBe(
    'Concurrent agent'
  )
})

test('subscribed UI polls and receives agent edits without a storage event', async () => {
  current = { preferences: { ...initial, displayName: 'Before' }, revision: 1, initialized: true }
  const preferences = await import('./preferences')
  function Name() {
    return <span>{preferences.usePreferences().displayName}</span>
  }
  render(<Name />)
  await waitFor(() => expect(screen.getByText('Before')).toBeVisible())
  current = {
    preferences: { ...initial, displayName: 'Agent changed name' },
    revision: 2,
    initialized: true,
  }
  await waitFor(() => expect(screen.getByText('Agent changed name')).toBeVisible(), {
    timeout: 4000,
  })
})

test('open Personal Settings updates pristine fields but protects unsaved drafts from agent edits', async () => {
  current = { preferences: { ...initial, displayName: 'Original' }, revision: 1, initialized: true }
  const preferences = await import('./preferences')
  const { PersonalSettings } = await import('../features/settings/PersonalSettings')
  render(<PersonalSettings />)
  await waitFor(() => expect(screen.getByLabelText('昵称')).toHaveValue('Original'))
  const user = userEvent.setup()
  await user.clear(screen.getByLabelText('昵称'))
  await user.type(screen.getByLabelText('昵称'), 'Unsaved draft')
  current = {
    preferences: { ...initial, displayName: 'Agent edit' },
    revision: 2,
    initialized: true,
  }
  expect(preferences).toHaveProperty('syncPreferences')
  await act(() => preferences.syncPreferences())
  expect(screen.getByLabelText('昵称')).toHaveValue('Unsaved draft')
  await user.click(screen.getByRole('button', { name: '保存个人信息' }))
  expect(await screen.findByRole('alert')).toBeVisible()
  expect(current.preferences.displayName).toBe('Agent edit')
  expect(screen.getByLabelText('昵称')).toHaveValue('Unsaved draft')
  expect(screen.queryByText('个人信息已保存')).not.toBeInTheDocument()
})
