import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { AccountControl } from './AccountControl'
import { TrialSelector } from './TrialSelector'
import { applySession, chatSource, updateTrial } from './session'
import { logout } from './client'

vi.mock('./client', () => ({ logout: vi.fn() }))
const session = {
  user: { id: 'alice', username: 'alice' },
  workspace: { id: 'workspace-a' },
  csrf_token: 'csrf',
  trial: { enabled: true, limit: 5, remaining: 5 },
}
afterEach(() => {
  act(() => applySession(null))
  vi.resetAllMocks()
})

it('logs out and removes the visible account', async () => {
  applySession(session)
  vi.mocked(logout).mockImplementation(async () => {
    applySession(null)
  })
  render(<AccountControl />)
  await userEvent.click(screen.getByRole('button', { name: '退出' }))
  await waitFor(() => expect(screen.queryByText('alice')).not.toBeInTheDocument())
  expect(logout).toHaveBeenCalledOnce()
})

it('selects own API and renders the authoritative exhausted trial state', async () => {
  applySession(session)
  const configure = vi.fn()
  render(<TrialSelector busy={false} onConfigure={configure} />)
  await userEvent.click(screen.getByLabelText('自有 API'))
  expect(chatSource()).toBe('own')
  act(() => updateTrial({ enabled: true, limit: 5, remaining: 0 }))
  expect(screen.getByRole('radio', { name: /公共试用/ })).toBeDisabled()
  expect(screen.getByText(/累计 5 次试用已用完/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: '配置自有 API' }))
  expect(configure).toHaveBeenCalledOnce()
})
