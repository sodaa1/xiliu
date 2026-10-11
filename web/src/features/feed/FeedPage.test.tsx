import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { FeedPage } from './FeedPage'

afterEach(() => vi.unstubAllGlobals())

test('manual add edit remove restore and external hide restore remain available in Feed', async () => {
  const user = userEvent.setup()
  let items = [
    {
      id: 'external',
      source: 'aihot',
      title: 'External story',
      summary: '',
      url: 'https://example.org/news',
      tags: [],
      metadata: {},
      hidden: false,
      deleted_at: null,
    },
  ]
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = new URL(String(input), 'http://localhost')
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (url.pathname === '/api/feed' && (!init?.method || init.method === 'GET')) {
        return Response.json({
          items: items.filter(
            (item) =>
              url.searchParams.get('include_hidden') === 'true' ||
              (!item.hidden && !item.deleted_at)
          ),
          sources: [],
        })
      }
      if (url.pathname === '/api/feed/manual' && init?.method === 'POST') {
        const item = {
          id: 'manual',
          source: 'manual',
          title: body.title || body.url,
          summary: '',
          url: body.url,
          tags: [],
          metadata: {},
          hidden: false,
          deleted_at: null,
        }
        items.push(item)
        return Response.json(item)
      }
      const id = url.pathname.includes('/manual/') ? 'manual' : 'external'
      items = items.map((item) =>
        item.id !== id
          ? item
          : {
              ...item,
              ...(init?.method === 'PATCH' ? body : {}),
              ...(init?.method === 'DELETE' ? { deleted_at: '2026-10-10' } : {}),
              ...(url.pathname.endsWith('/restore') ? { deleted_at: null } : {}),
              ...(url.pathname.endsWith('/hide') ? { hidden: true } : {}),
              ...(url.pathname.endsWith('/unhide') ? { hidden: false } : {}),
            }
      )
      return Response.json(items.find((item) => item.id === id))
    })
  )
  render(
    <MemoryRouter>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
          })
        }
      >
        <FeedPage />
      </QueryClientProvider>
    </MemoryRouter>
  )
  await screen.findByText('External story')
  await user.click(screen.getByRole('button', { name: '添加资讯' }))
  await user.type(screen.getByLabelText('资讯链接'), 'https://example.org/manual')
  await user.type(screen.getByLabelText('资讯标题'), 'Manual story')
  await user.click(screen.getByRole('button', { name: '保存资讯' }))
  await screen.findByText('Manual story')
  await user.click(screen.getByRole('button', { name: '编辑 Manual story' }))
  await user.clear(screen.getByLabelText('资讯标题'))
  await user.type(screen.getByLabelText('资讯标题'), 'Edited story')
  await user.click(screen.getByRole('button', { name: '保存资讯' }))
  await screen.findByText('Edited story')
  await user.click(screen.getByRole('button', { name: '删除 Edited story' }))
  await waitFor(() => expect(screen.queryByText('Edited story')).not.toBeInTheDocument())
  await user.click(screen.getByRole('button', { name: '隐藏 External story' }))
  await waitFor(() => expect(screen.queryByText('External story')).not.toBeInTheDocument())
  await user.click(screen.getByLabelText('显示已移除资讯'))
  await screen.findByText('Edited story')
  await user.click(screen.getByRole('button', { name: '恢复 Edited story' }))
  await user.click(screen.getByRole('button', { name: '取消隐藏 External story' }))
  await user.click(screen.getByLabelText('显示已移除资讯'))
  await screen.findByText('Edited story')
  await screen.findByText('External story')
})
