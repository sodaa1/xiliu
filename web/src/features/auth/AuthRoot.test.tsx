import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { AuthForm, AuthRoot } from './AuthRoot'
import { applySession } from './session'
import { authenticate, loadBootstrap, loadSession } from './client'

vi.mock('./client', () => ({ authenticate: vi.fn(), loadBootstrap: vi.fn(), loadSession: vi.fn() }))
afterEach(() => {
  act(() => applySession(null))
  vi.resetAllMocks()
})

it('offers a separate guest build and shows real login errors', async () => {
  vi.mocked(authenticate).mockRejectedValue(new Error('账号或密码不正确。'))
  const success = vi.fn()
  render(<AuthForm signupEnabled onSuccess={success} />)
  expect(screen.getByRole('link', { name: /先体验一下/ })).toHaveAttribute('href', '/demo/#/today')
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('账号'), 'alice')
  await user.type(screen.getByLabelText('密码'), 'long-enough-password')
  await user.click(screen.getByRole('button', { name: '登录' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('账号或密码不正确。')
  expect(success).not.toHaveBeenCalled()
})

it('registers and hands off to a full-page authenticated navigation', async () => {
  vi.mocked(authenticate).mockResolvedValue({})
  const success = vi.fn()
  render(<AuthForm signupEnabled onSuccess={success} />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: /创建一个/ }))
  await user.type(screen.getByLabelText('账号'), 'alice')
  await user.type(screen.getByLabelText('密码'), 'long-enough-password')
  await user.click(screen.getByRole('button', { name: '注册并开始使用' }))
  await waitFor(() => expect(success).toHaveBeenCalledOnce())
  expect(authenticate).toHaveBeenCalledWith('register', 'alice', 'long-enough-password')
})

it('keeps business components unmounted until identity loads, then clears them on expiry', async () => {
  vi.mocked(loadBootstrap).mockResolvedValue({ signup_enabled: true })
  let complete!: (value: Awaited<ReturnType<typeof loadSession>>) => void
  vi.mocked(loadSession).mockReturnValue(
    new Promise((resolve) => {
      complete = resolve
    })
  )
  render(
    <AuthRoot>
      <div>private workspace</div>
    </AuthRoot>
  )
  expect(screen.queryByText('private workspace')).not.toBeInTheDocument()
  await act(async () =>
    complete({
      user: { id: 'alice', username: 'alice' },
      workspace: { id: 'a' },
      csrf_token: 'csrf',
      trial: { enabled: true, limit: 5, remaining: 5 },
    })
  )
  expect(await screen.findByText('private workspace')).toBeInTheDocument()
  act(() => applySession(null))
  expect(screen.queryByText('private workspace')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()
})
