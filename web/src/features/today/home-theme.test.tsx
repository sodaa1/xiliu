import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { setHomeTheme, useHomeTheme } from './home-theme'
import { HomeThemeSwitch } from './HomeThemeSwitch'
function Choice() {
  const theme = useHomeTheme()
  return (
    <button onClick={() => setHomeTheme(theme === 'original' ? 'workbench' : 'original')}>
      {theme}
    </button>
  )
}
beforeEach(() => localStorage.clear())
afterEach(() => vi.restoreAllMocks())

test('theme selector exposes its selected state and supports keyboard switching', async () => {
  const user = userEvent.setup()
  render(<HomeThemeSwitch />)
  expect(screen.getByRole('button', { name: '原有主题' })).toHaveAttribute('aria-pressed', 'true')
  await user.tab()
  await user.tab()
  await user.keyboard('{Enter}')
  expect(screen.getByRole('button', { name: '山水工作台' })).toHaveAttribute('aria-pressed', 'true')
  expect(localStorage.getItem('xiliu-home-theme-v1')).toBe('workbench')
})
test('preserves the original theme and persists an independent workbench choice', async () => {
  localStorage.setItem('xiliu-preferences-v1', '{"theme":"dark"}')
  const user = userEvent.setup()
  render(<Choice />)
  expect(screen.getByRole('button', { name: 'original' })).toBeVisible()
  await user.click(screen.getByRole('button'))
  expect(localStorage.getItem('xiliu-home-theme-v1')).toBe('workbench')
  expect(localStorage.getItem('xiliu-preferences-v1')).toBe('{"theme":"dark"}')
  act(() => window.dispatchEvent(new StorageEvent('storage', { key: 'xiliu-home-theme-v1' })))
  expect(screen.getByRole('button', { name: 'workbench' })).toBeVisible()
})
test('can switch in memory when browser storage writes fail', async () => {
  const user = userEvent.setup()
  render(<Choice />)
  const blocked = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota')
  })
  await user.click(screen.getByRole('button'))
  expect(screen.getByRole('button', { name: 'workbench' })).toBeVisible()
  await user.click(screen.getByRole('button'))
  expect(screen.getByRole('button', { name: 'original' })).toBeVisible()
  blocked.mockRestore()
  act(() => setHomeTheme('original'))
})
