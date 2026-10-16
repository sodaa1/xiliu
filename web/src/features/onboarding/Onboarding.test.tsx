import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { Onboarding } from './Onboarding'
import { getGuideProgress, startGuide, resetGuide, recordGuideAction } from './progress'
import { createSeed } from '../demo/seed'
beforeEach(() => {
  localStorage.clear()
  resetGuide()
  vi.stubGlobal('fetch', async () => Response.json(createSeed().content[0]))
})
afterEach(() => vi.unstubAllGlobals())
function mount() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <Onboarding />
      </MemoryRouter>
    </QueryClientProvider>
  )
}
test('welcome can be skipped without mutating any real content', async () => {
  mount()
  expect(screen.getByRole('button', { name: '开始快速上手' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '浏览所有功能' })).toHaveAttribute('href', '/guide')
  await userEvent.click(screen.getByRole('button', { name: '稍后再看' }))
  expect(screen.queryByRole('button', { name: '开始快速上手' })).not.toBeInTheDocument()
  expect(getGuideProgress().status).toBe('dismissed')
})
test('progress links point at the actual saved document, not just the next module', () => {
  startGuide()
  mount()
  expect(screen.getByRole('link', { name: '前往当前步骤' })).toHaveAttribute('href', '/feed')
  act(() => recordGuideAction({ type: 'saved', item: createSeed().content[0] }))
  expect(screen.getByRole('link', { name: '前往当前步骤' })).toHaveAttribute(
    'href',
    '/inbox?item=note-inbox'
  )
  expect(screen.getByRole('heading', { name: /添加标签/ })).toBeInTheDocument()
})
