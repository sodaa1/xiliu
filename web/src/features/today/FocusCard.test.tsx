import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { FocusCard } from './FocusCard'
beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-19T23:59:00+08:00'))
})
afterEach(() => vi.useRealTimers())
test('focus timer resumes from storage and resets when a paused session crosses midnight', () => {
  localStorage.setItem(
    'xiliu-home-focus-v1',
    JSON.stringify({ day: new Date().toLocaleDateString('en-CA'), seconds: 5400, started: null })
  )
  render(<FocusCard />)
  expect(screen.getByText('1.5 小时')).toBeVisible()
  vi.setSystemTime(new Date('2026-10-20T00:01:00+08:00'))
  fireEvent.click(screen.getByRole('button', { name: '开始专注' }))
  expect(screen.getByText('0 分钟')).toBeVisible()
  act(() => vi.advanceTimersByTime(65000))
  expect(screen.getByText('1 分钟')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: '暂停计时' }))
  const value = JSON.parse(localStorage.getItem('xiliu-home-focus-v1')!)
  expect(value.seconds).toBe(65)
  expect(value.started).toBeNull()
})
