import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient } from '@tanstack/react-query'
import { expect, test } from 'vitest'
import { DemoBar } from './DemoBar'
import { resetDemoExperience } from './reset'
import { mutateDemo, readDemoState } from './store'

test('reset requires confirmation and clears only demo state and queries', async () => {
  const cache = new QueryClient()
  cache.setQueryData(['content'], 'old')
  localStorage.setItem('xiliu-preferences-v1', 'real-settings')
  localStorage.setItem('xiliu-demo-preferences-v1', 'old-demo')
  await mutateDemo((state) => {
    state.tasks[0].completed = true
  })
  render(
    <MemoryRouter>
      <DemoBar onReset={() => resetDemoExperience(cache)} />
    </MemoryRouter>
  )
  const user = userEvent.setup()
  expect(screen.getByText('游客演示')).toBeInTheDocument()
  expect(screen.getByText(/仅在当前页面/)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '重置体验' }))
  await user.click(screen.getByRole('button', { name: '继续体验' }))
  expect((await readDemoState()).tasks[0].completed).toBe(true)
  await user.click(screen.getByRole('button', { name: '重置体验' }))
  await user.click(screen.getByRole('button', { name: '确认重置' }))
  expect((await readDemoState()).tasks[0].completed).toBe(false)
  expect(cache.getQueryData(['content'])).toBeUndefined()
  expect(localStorage.getItem('xiliu-preferences-v1')).toBe('real-settings')
  expect(localStorage.getItem('xiliu-demo-preferences-v1')).toBeNull()
})
