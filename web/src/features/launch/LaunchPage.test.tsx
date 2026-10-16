import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { LaunchPage } from './LaunchPage'

it('lets the user skip the introduction and enter 今日', async () => {
  // jsdom has no Canvas2D renderer; motion is verified in the real browser.
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
  render(
    <MemoryRouter>
      <LaunchPage />
    </MemoryRouter>
  )
  expect(screen.getByText('让灵感相连。')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: '跳过开场' }))
  expect(screen.queryByRole('button', { name: '跳过开场' })).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: '开始使用' })).toHaveAttribute('href', '/today')
})

it('shows the final handwritten wordmark immediately when the system reduces motion', () => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
  )
  render(
    <MemoryRouter>
      <LaunchPage />
    </MemoryRouter>
  )
  expect(screen.getByRole('heading', { name: 'xiliu' })).toBeInTheDocument()
  expect(screen.getByText('息流')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '跳过开场' })).not.toBeInTheDocument()
  vi.unstubAllGlobals()
})
