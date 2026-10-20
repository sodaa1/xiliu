import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { WorkbenchHome } from './WorkbenchHome'
import { WorkbenchShell } from './WorkbenchShell'
const today = new Date().toISOString()
let task = {
  id: 'task-a',
  title: '完成产品设计稿',
  completed: false,
  due_at: today,
  scope: 'day',
  created_at: today,
  updated_at: today,
}
let calls: { url: string; options?: RequestInit }[] = []
beforeEach(() => {
  task = { ...task, completed: false }
  calls = []
  localStorage.clear()
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, options?: RequestInit) => {
      const url = String(input)
      calls.push({ url, options })
      if (url === '/api/tasks/task-a' && options?.method === 'PATCH') {
        task = { ...task, ...JSON.parse(String(options.body)) }
        return Response.json(task)
      }
      if (url === '/api/today') return Response.json({ feed: [], tasks: [task], inbox_count: 2 })
      if (url.startsWith('/api/content')) return Response.json([])
      if (url === '/api/conversations') return Response.json([])
      if (url === '/api/inbox/import')
        return Response.json({
          id: 'note-a',
          title: '今日灵感',
          type: 'note',
          status: 'inbox',
          created_at: today,
        })
      return Response.json({
        preferences: { displayName: 'Soda', theme: 'light' },
        revision: 1,
        initialized: false,
      })
    })
  )
})
afterEach(() => vi.unstubAllGlobals())
function mount() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <WorkbenchHome />
      </MemoryRouter>
    </QueryClientProvider>
  )
}
test('renders reference dashboard sections from real workspace data and updates task completion', async () => {
  mount()
  expect(await screen.findByRole('checkbox', { name: '完成产品设计稿' })).toBeVisible()
  for (const name of ['今日任务', '快速记录', '灵感 · 资讯', '最近活动'])
    expect(screen.getByRole('heading', { name })).toBeVisible()
  fireEvent.click(screen.getByRole('checkbox', { name: '完成产品设计稿' }))
  await waitFor(() =>
    expect(screen.getByRole('checkbox', { name: '完成产品设计稿' })).toBeChecked()
  )
  expect(calls.some((c) => c.url === '/api/tasks/task-a' && c.options?.method === 'PATCH')).toBe(
    true
  )
})
test('quick note saves through the existing import endpoint and keeps its draft when closed', async () => {
  mount()
  fireEvent.change(screen.getByRole('textbox', { name: '快速记录内容' }), {
    target: { value: '今日灵感' },
  })
  fireEvent.click(screen.getByRole('button', { name: '快速记录' }))
  expect(await screen.findByRole('textbox', { name: '记录内容' })).toHaveValue('今日灵感')
  fireEvent.click(screen.getByRole('button', { name: '关闭弹窗' }))
  expect(screen.getByRole('textbox', { name: '快速记录内容' })).toHaveValue('今日灵感')
  fireEvent.click(screen.getByRole('button', { name: '快速记录' }))
  fireEvent.click(screen.getByRole('button', { name: '保存记录' }))
  await waitFor(() =>
    expect(calls.some((c) => c.url === '/api/inbox/import' && c.options?.method === 'POST')).toBe(
      true
    )
  )
})

test('saving capture stays open until its request finishes to protect subsequent drafts', async () => {
  const original = globalThis.fetch
  let finish!: (value: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn((input: string, options?: RequestInit) =>
      String(input) === '/api/inbox/import'
        ? new Promise<Response>((resolve) => {
            finish = resolve
          })
        : original(input, options)
    )
  )
  mount()
  fireEvent.change(screen.getByRole('textbox', { name: '快速记录内容' }), {
    target: { value: '待保存的内容' },
  })
  fireEvent.click(screen.getByRole('button', { name: '快速记录' }))
  fireEvent.click(screen.getByRole('button', { name: '保存记录' }))
  await waitFor(() => expect(screen.getByRole('button', { name: '保存记录' })).toBeDisabled())
  fireEvent.click(screen.getByRole('button', { name: '关闭弹窗' }))
  expect(screen.getByRole('dialog')).toBeVisible()
  finish(Response.json({ id: 'saved' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
})

test('workbench shell searches existing tasks and preserves settings overlay navigation', async () => {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={['/today']}>
        <WorkbenchShell inert={false}>
          <p>首页内容</p>
        </WorkbenchShell>
      </MemoryRouter>
    </QueryClientProvider>
  )
  const search = screen.getByRole('textbox', { name: '搜索息流' })
  fireEvent.change(search, { target: { value: '产品设计' } })
  fireEvent.submit(search.closest('form')!)
  expect(await screen.findByRole('link', { name: /任务.*完成产品设计稿/ })).toHaveAttribute(
    'href',
    '/plans'
  )
  expect(screen.getByRole('link', { name: '外观设置' })).toHaveAttribute(
    'href',
    '/settings?section=appearance'
  )
  fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
  expect(search).not.toHaveFocus()
  fireEvent.click(screen.getByRole('button', { name: '关闭弹窗' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})
