import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { PersonalSettings } from './PersonalSettings'

afterEach(() => {
  delete window.__TAURI__
  vi.unstubAllGlobals()
  localStorage.clear()
  window.dispatchEvent(new StorageEvent('storage', { key: null }))
})
test('desktop profile waits for native persistence and reports a backup failure without claiming success', async () => {
  localStorage.clear()
  let snapshot = {
    preferences: {
      displayName: '',
      email: '',
      bio: '',
      avatar: '',
      theme: 'light',
      fontSize: 'small',
      fontFamily: 'system',
      density: 'comfortable',
      reducedMotion: false,
    },
    revision: 0,
    initialized: false,
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, options?: RequestInit) => {
      if (options?.method === 'PUT') {
        const body = JSON.parse(String(options.body))
        snapshot = {
          preferences: { ...snapshot.preferences, ...body.changes },
          revision: snapshot.revision + 1,
          initialized: true,
        }
      }
      return Response.json(snapshot)
    })
  )
  let fail!: (error: Error) => void
  const invoke = vi.fn<(command: string, args: Record<string, unknown>) => Promise<unknown>>(
    () =>
      new Promise<void>((_, reject) => {
        fail = reject
      })
  )
  window.__TAURI__ = { core: { invoke } }
  render(<PersonalSettings />)
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('昵称'), '溪流')
  await user.click(screen.getByRole('button', { name: '保存个人信息' }))
  expect(invoke).toHaveBeenCalledWith('save_preferences', { json: expect.any(String) })
  const saved = JSON.parse(String(invoke.mock.calls[0][1].json))
  expect(saved.displayName).toBe('溪流')
  expect(screen.queryByText('个人信息已保存')).not.toBeInTheDocument()
  fail(new Error('disk unavailable'))
  expect(await screen.findByRole('alert')).toHaveTextContent('桌面备份未保存')
  expect(screen.queryByText('个人信息已保存')).not.toBeInTheDocument()
  expect(JSON.parse(localStorage.getItem('xiliu-preferences-v1')!).displayName).toBe('溪流')
  invoke.mockResolvedValueOnce(undefined)
  await user.click(screen.getByRole('button', { name: '保存个人信息' }))
  expect(await screen.findByText('个人信息已保存')).toBeVisible()
  expect(invoke).toHaveBeenCalledTimes(2)
})
