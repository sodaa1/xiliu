import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { FeedCard, FeedPage } from './FeedPage'
import type { FeedItem } from '../../lib/workspace-api'

afterEach(() => vi.unstubAllGlobals())

const previewItem: FeedItem = {
  id: 'external',
  source: 'aihot',
  title: 'Preview story',
  summary: 'Short summary',
  url: 'https://example.org/news',
  published_at: '2026-10-14T10:00:00Z',
  tags: ['ai'],
  metadata: {},
}

function mountFeedCard() {
  return render(
    <MemoryRouter>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
          })
        }
      >
        <FeedCard item={previewItem} />
      </QueryClientProvider>
    </MemoryRouter>
  )
}

test('feed preview opens by keyboard and returns focus when dismissed', async () => {
  mountFeedCard()
  const user = userEvent.setup()
  await user.tab()
  const title = screen.getByRole('button', { name: 'Preview story' })
  expect(title).toHaveFocus()
  await user.keyboard('{Enter}')
  expect(screen.getByRole('dialog', { name: 'Preview story' })).toBeVisible()
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(title).toHaveFocus()
  await user.keyboard(' ')
  expect(screen.getByRole('dialog', { name: 'Preview story' })).toBeVisible()
})

test('feed preview blocks duplicate saves and shows save failures before retry', async () => {
  let finishSave!: (response: Response) => void
  const saves: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      if (input === '/api/feed/external/save' && init?.method === 'POST') {
        saves.push(input)
        return new Promise<Response>((resolve) => {
          finishSave = resolve
        })
      }
      throw new Error(`Unexpected request: ${input}`)
    })
  )
  mountFeedCard()
  const user = userEvent.setup()
  await user.click(screen.getByRole('heading', { name: 'Preview story', level: 2 }))
  const dialog = screen.getByRole('dialog', { name: 'Preview story' })
  const save = within(dialog).getByRole('button', { name: '收进收件箱' })
  await user.click(save)
  expect(save).toBeDisabled()
  expect(save).toHaveTextContent('保存中')
  await user.click(save)
  expect(saves).toHaveLength(1)

  finishSave(Response.json({ error: { message: '无法保存，请重试。' } }, { status: 503 }))
  expect(await within(dialog).findByRole('alert')).toHaveTextContent('无法保存，请重试。')
  expect(save).toBeEnabled()
  await user.click(save)
  expect(saves).toHaveLength(2)
  finishSave(Response.json({ id: 'saved' }))
  expect(await within(dialog).findByRole('button', { name: '已收进收件箱' })).toBeDisabled()
  expect(within(dialog).queryByRole('alert')).not.toBeInTheDocument()
})

test('manual add edit remove restore and external hide restore remain available in 资讯', async () => {
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

test('feed card opens a preview with AI summary, read original and save actions', async () => {
  const user = userEvent.setup()
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = new URL(String(input), 'http://localhost')
      if (url.pathname === '/api/feed' && (!init?.method || init.method === 'GET')) {
        return Response.json({
          items: [
            {
              id: 'external',
              source: 'aihot',
              title: 'Preview story',
              summary: 'Short summary',
              url: 'https://example.org/news',
              tags: ['ai'],
              metadata: {},
              hidden: false,
              deleted_at: null,
            },
          ],
          sources: [],
        })
      }
      if (url.pathname === '/api/feed/external/summarize' && init?.method === 'POST')
        return Response.json({ summary: '这是一段更详细的 AI 总结，解释了它为什么值得关注。' })
      return Response.json({})
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
  await user.click(await screen.findByRole('heading', { name: 'Preview story', level: 2 }))
  const dialog = await screen.findByRole('dialog', { name: 'Preview story' })
  expect(within(dialog).getByRole('link', { name: /阅读原文/ })).toHaveAttribute(
    'href',
    'https://example.org/news'
  )
  expect(within(dialog).getByRole('button', { name: /收进收件箱/ })).toBeVisible()
  await user.click(within(dialog).getByRole('button', { name: /AI 总结/ }))
  expect(await within(dialog).findByText(/更详细的 AI 总结/)).toBeVisible()
})
