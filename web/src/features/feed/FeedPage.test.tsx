import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { FeedPage } from './FeedPage'
import type { FeedItem } from '../../lib/workspace-api'
let items: FeedItem[]
let writes: { url: string; method: string; body: Record<string, unknown> }[]
beforeEach(() => {
  items = Array.from({ length: 4 }, (_, index) => ({
    id: 'n' + index,
    source: 'manual',
    title: '资讯标题 ' + index,
    summary: '真实接口数据形成的摘要 ' + index,
    url: 'https://example.com/' + index,
    published_at: `2026-10-${19 - index}T09:00:00Z`,
    tags: [index === 0 ? '设计' : 'AI'],
    metadata: {},
  }))
  writes = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = String(input),
        method = init?.method ?? 'GET',
        body = init?.body ? JSON.parse(String(init.body)) : {}
      if (method !== 'GET') writes.push({ url, method, body })
      if (url === '/api/feed/manual' && method === 'POST') {
        const item = { ...items[0], ...body, id: 'new', published_at: new Date().toISOString() }
        items = [item, ...items]
        return Response.json(item)
      }
      if (url.startsWith('/api/feed/manual/') && method === 'PATCH') {
        const id = url.split('/').at(-1)
        items = items.map((item) => (item.id === id ? { ...item, ...body } : item))
        return Response.json(items.find((item) => item.id === id))
      }
      if (url.startsWith('/api/feed/manual/') && method === 'DELETE') {
        const id = url.split('/').at(-1)
        items = items.filter((item) => item.id !== id)
        return Response.json({ deleted: true })
      }
      if (url.startsWith('/api/feed')) {
        const params = new URL(url, 'http://localhost').searchParams
        return Response.json({
          items: items.filter(
            (item) =>
              (!params.get('q') || item.title.includes(params.get('q')!)) &&
              (!params.get('source') || item.source === params.get('source'))
          ),
          sources: [{ source: 'manual', label: '我的资讯', status: 'ok', message: '已更新' }],
        })
      }
      return Response.json({})
    })
  )
})
afterEach(() => vi.unstubAllGlobals())
function mount() {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <FeedPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
  return userEvent.setup()
}
test('feed discovery uses actual items for featured stories topic filters sort and views', async () => {
  const user = mount()
  const featured = await screen.findByRole('region', { name: '焦点阅读' })
  expect(within(featured).getAllByRole('heading', { name: '资讯标题 0' })).toHaveLength(1)
  const fullListCard = document.querySelector('.feed-card-standard')!
  expect(
    within(fullListCard as HTMLElement).getByRole('button', { name: '编辑 资讯标题 0' })
  ).toBeVisible()
  await user.click(screen.getByRole('button', { name: '焦点阅读第 2 篇' }))
  expect(within(featured).getByRole('button', { name: '焦点阅读第 2 篇' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  await user.click(screen.getByRole('button', { name: '设计' }))
  expect(screen.queryByRole('region', { name: '焦点阅读' })).not.toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '资讯标题 0' })).toBeVisible()
  expect(screen.queryByRole('heading', { name: '资讯标题 1' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '卡片视图' }))
  expect(screen.getByRole('button', { name: '卡片视图' })).toHaveAttribute('aria-pressed', 'true')
  await user.selectOptions(screen.getByRole('combobox', { name: '资讯排序' }), 'oldest')
  await user.click(screen.getByRole('button', { name: '来源状态' }))
  expect(screen.getByRole('dialog', { name: '来源状态' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: '浏览' }))
  expect(screen.getByRole('button', { name: '我的资讯' })).toHaveAttribute('aria-pressed', 'true')
})
test('feed redesign preserves manual create edit delete and search through existing endpoints', async () => {
  items = items.slice(0, 1)
  const user = mount()
  await screen.findByRole('heading', { name: '资讯标题 0' })
  await user.click(screen.getByRole('button', { name: '添加资讯' }))
  await user.type(screen.getByRole('textbox', { name: '资讯链接' }), 'https://example.com/new')
  await user.type(screen.getByRole('textbox', { name: '资讯标题' }), '新增设计资讯')
  await user.click(screen.getByRole('button', { name: '保存资讯' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(writes.some((item) => item.url === '/api/feed/manual' && item.method === 'POST')).toBe(
    true
  )
  await user.click(screen.getByRole('button', { name: '编辑 新增设计资讯' }))
  await user.clear(screen.getByRole('textbox', { name: '资讯标题' }))
  await user.type(screen.getByRole('textbox', { name: '资讯标题' }), '编辑后的资讯')
  await user.click(screen.getByRole('button', { name: '保存资讯' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  fireEvent.change(screen.getByRole('textbox', { name: '搜索资讯' }), {
    target: { value: '编辑后的' },
  })
  expect(await screen.findByRole('heading', { name: '编辑后的资讯' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: '删除 编辑后的资讯' }))
  await waitFor(() =>
    expect(screen.queryByRole('heading', { name: '编辑后的资讯' })).not.toBeInTheDocument()
  )
  expect(
    writes.some((item) => item.url === '/api/feed/manual/new' && item.method === 'DELETE')
  ).toBe(true)
})
