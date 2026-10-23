import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { TodayWorkspace } from './TodayWorkspace'
afterEach(() => vi.unstubAllGlobals())
test('the home workspace links to actual inbox records and shows actual task states', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string) =>
      Response.json(
        String(input) === '/api/inbox'
          ? [
              {
                id: 'doc one',
                title: '待整理原文',
                status: 'inbox',
                processing_status: 'ready',
                type: 'note',
                summary: '',
                content: '',
                source: '',
                tags: [],
                filename: null,
                created_at: '2026-10-22',
                updated_at: '2026-10-22',
              },
            ]
          : {
              tasks: [
                { id: 'task', title: '正在做的事情', status: 'in_progress', completed: false },
              ],
              feed: [{ id: 'news', title: '真实资讯', url: 'https://example.com/article' }],
            }
      )
    )
  )
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <TodayWorkspace />
      </MemoryRouter>
    </QueryClientProvider>
  )
  expect(await screen.findByRole('link', { name: /^待整理原文/ })).toHaveAttribute(
    'href',
    '/inbox?item=doc%20one'
  )
  expect(within(screen.getByRole('region', { name: '今日要做' })).getByText('进行中')).toBeVisible()
  expect(screen.getByRole('link', { name: '真实资讯' })).toHaveAttribute(
    'href',
    'https://example.com/article'
  )
})
