import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { KnowledgePage } from './KnowledgePage'

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      const folder = {
        id: 'research',
        name: '研究',
        summary: '研究与论文',
        tags: ['论文'],
        priority: 2,
        item_count: 1,
        created_at: '',
        updated_at: '',
      }
      if (String(input) === '/api/knowledge/folders' && init?.method === 'POST')
        return Response.json({ ...folder, ...JSON.parse(String(init.body)) })
      if (String(input) === '/api/knowledge/folders') return Response.json([folder])
      if (String(input) === '/api/knowledge/folders/research/items') return Response.json([])
      if (String(input).startsWith('/api/content?')) return Response.json([])
      return Response.json({ error: { message: 'Unexpected test request' } }, { status: 404 })
    })
  )
})
function mount() {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <KnowledgePage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}
test('folder cards open nested contents and return to the folder homepage', async () => {
  mount()
  const user = userEvent.setup()
  await user.click(await screen.findByRole('link', { name: /1 项内容.*研究/ }))
  expect(await screen.findByRole('button', { name: '返回文件夹' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: '返回文件夹' }))
  expect(await screen.findByRole('link', { name: /1 项内容.*研究/ })).toBeVisible()
})
test('folder card edit and delete actions open their dialogs', async () => {
  mount()
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: '编辑规则' }))
  expect(await screen.findByRole('heading', { name: '编辑文件夹规则' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: '取消' }))
  await user.click(await screen.findByRole('button', { name: '删除文件夹 研究' }))
  expect(await screen.findByRole('heading', { name: '删除文件夹 研究' })).toBeVisible()
})
test('folder rules are submitted with parsed tags and numeric priority', async () => {
  mount()
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: '新建文件夹' }))
  await user.type(screen.getByLabelText('文件夹名称'), '工程')
  await user.type(screen.getByLabelText('匹配标签'), '代码,前端')
  await user.clear(screen.getByLabelText('优先级'))
  await user.type(screen.getByLabelText('优先级'), '5')
  await user.click(screen.getByRole('button', { name: '保存规则' }))
  const fetchMock = vi.mocked(fetch)
  const request = fetchMock.mock.calls.find(
    ([input, init]) => input === '/api/knowledge/folders' && init?.method === 'POST'
  )
  expect(JSON.parse(String(request?.[1]?.body))).toEqual({
    name: '工程',
    summary: '',
    tags: ['代码', '前端'],
    priority: 5,
  })
})

test('library category filters use actual folder tags and can reset without changing folders', async () => {
  const original = fetch
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      if (String(input) === '/api/knowledge/folders' && init?.method !== 'POST') {
        const response = await original(input)
        const folders = await response.json()
        return Response.json([
          ...folders,
          { ...folders[0], id: 'work', name: '工作', tags: ['项目'] },
        ])
      }
      return original(input, init)
    })
  )
  mount()
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: '论文' }))
  expect(screen.getByRole('heading', { name: '研究' })).toBeVisible()
  expect(screen.queryByRole('heading', { name: '工作' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '全部分类' }))
  expect(await screen.findByRole('heading', { name: '工作' })).toBeVisible()
})
