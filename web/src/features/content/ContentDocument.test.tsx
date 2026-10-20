import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, afterEach, test, expect, vi } from 'vitest'
import { ContentPage } from './ContentPage'
import type { ContentItem } from '../../lib/workspace-api'
let item: ContentItem, requests: string[]
beforeEach(() => {
  item = {
    id: 'one',
    type: 'note',
    status: 'inbox',
    title: '独立阅读资料',
    content: '保留的完整原文内容',
    summary: '资料摘要',
    source: '',
    tags: ['设计'],
    created_at: '2026-10-19T00:00:00Z',
    updated_at: '2026-10-19T00:00:00Z',
    filename: null,
    processing_status: 'failed',
    processing_error: '网络暂时不可用',
  }
  requests = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = String(input)
      if (init?.method === 'POST') requests.push(url)
      if (url === '/api/inbox/one/retry') {
        item = { ...item, processing_status: 'ready', processing_error: null }
        return Response.json(item)
      }
      if (url === '/api/inbox/classify-batch') {
        item = { ...item, status: 'knowledge', folder_id: 'design' }
        return Response.json({ items: [item] })
      }
      if (url === '/api/content/one') return Response.json(item)
      if (url === '/api/knowledge/folders') return Response.json([])
      if (url.startsWith('/api/content?')) return Response.json([item])
      return Response.json([])
    })
  )
})
afterEach(() => vi.unstubAllGlobals())
test('standalone document retains retry errors and shows classification result after archiving', async () => {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <ContentPage status="inbox" documentId="one" />
      </MemoryRouter>
    </QueryClientProvider>
  )
  const user = userEvent.setup()
  expect(await screen.findByText(/网络暂时不可用/)).toBeVisible()
  expect(screen.getByText('保留的完整原文内容')).toBeVisible()
  await user.click(screen.getByRole('button', { name: '重新整理' }))
  await waitFor(() => expect(screen.queryByText(/网络暂时不可用/)).not.toBeInTheDocument())
  expect(requests).toContain('/api/inbox/one/retry')
  await user.click(screen.getByRole('button', { name: '内容操作：独立阅读资料' }))
  await user.click(screen.getByRole('menuitem', { name: '归档到知识库' }))
  await waitFor(() => expect(requests).toContain('/api/inbox/classify-batch'))
  await waitFor(() => expect(document.querySelector('.document-reading-page')).toBeInTheDocument())
  await user.click(screen.getByRole('button', { name: '内容操作：独立阅读资料' }))
  expect(await screen.findByRole('menuitem', { name: '查看归类结果' })).toHaveAttribute(
    'href',
    '/knowledge?folder=design&document=one'
  )
  expect(screen.queryByRole('menuitem', { name: '归档到知识库' })).not.toBeInTheDocument()
})
