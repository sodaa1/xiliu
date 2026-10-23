import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { FeedPage } from './FeedPage'
afterEach(() => vi.unstubAllGlobals())
test('feed selection keeps a readable queue and opens the actual summary in a nonmodal reader', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      Response.json({
        items: [0, 1].map((i) => ({
          id: String(i),
          title: `阅读资料 ${i}`,
          summary: `实际摘要 ${i}`,
          url: `https://example.com/${i}`,
          source: 'manual',
          published_at: '2026-10-22',
          tags: [],
          metadata: {},
        })),
        sources: [],
      })
    )
  )
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <FeedPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
  await userEvent.setup().click(await screen.findByRole('button', { name: '阅读资料 0' }))
  const reader = await screen.findByRole('region', { name: '资讯阅读' })
  expect(within(reader).getByText('实际摘要 0')).toBeVisible()
  await userEvent.setup().click(screen.getByRole('button', { name: '阅读：阅读资料 1' }))
  expect(within(reader).getByText('实际摘要 1')).toBeVisible()
  expect(screen.getByRole('button', { name: '阅读：阅读资料 0' })).toBeVisible()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  await userEvent.setup().click(screen.getByRole('button', { name: '返回资讯列表' }))
  expect(screen.queryByRole('region', { name: '资讯阅读' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: '阅读资料 0' })).toBeVisible()
})
