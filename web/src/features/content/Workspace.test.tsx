import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { beforeEach, expect, test, vi } from 'vitest'
import { ContentPage } from './ContentPage'
import { FeedPage } from '../feed/FeedPage'
import { PlansPage } from '../plans/PlansPage'
import { AutomationsDrawer } from '../automations/AutomationsDrawer'
import type { Automation, ContentItem, Task } from '../../lib/workspace-api'

const stamp = '2026-10-07T01:00:00Z'
const news = {
  id: 'news',
  source: 'github',
  title: 'A new open source project',
  summary: 'A useful tool for research.',
  url: 'https://github.com/example/project',
  published_at: stamp,
  tags: ['tools'],
  metadata: {},
}
let content: ContentItem[], tasks: Task[], automations: Automation[]
let requests: { url: string; method: string; body: Record<string, unknown> }[]
beforeEach(() => {
  content = []
  tasks = []
  automations = []
  requests = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = String(input),
        method = init?.method ?? 'GET',
        body = init?.body ? JSON.parse(String(init.body)) : {}
      requests.push({ url, method, body })
      if (url === '/api/knowledge/folders') return Response.json([])
      if (url === '/api/tasks' && method === 'GET') return Response.json(tasks)
      if (url === '/api/inbox')
        return Response.json(content.filter((item) => item.status === 'inbox'))
      if (url === '/api/inbox/import') {
        const item: ContentItem = {
          id: 'captured',
          title: String(body.text),
          content: String(body.text),
          type: 'note',
          source: '',
          tags: [],
          summary: '',
          status: 'inbox',
          filename: null,
          created_at: stamp,
          updated_at: stamp,
          processing_status: 'pending',
          ai_processed: false,
        }
        content.push(item)
        return Response.json(item)
      }
      if (url === '/api/content/captured' && method === 'GET') {
        if (!content.length)
          return Response.json({ error: { message: 'Deleted content' } }, { status: 404 })
        if (requests.filter((request) => request.url === url).length > 1) {
          content[0] = { ...content[0], status: 'knowledge', processing_status: 'ready' }
        }
        return Response.json(content[0])
      }
      if (url === '/api/content/captured' && method === 'DELETE') {
        content = []
        return new Response(null, { status: 204 })
      }
      if (url === '/api/content' && method === 'POST') {
        const item = {
          id: 'captured',
          summary: '',
          filename: null,
          created_at: stamp,
          updated_at: stamp,
          status: 'inbox',
          ...body,
        }
        content.push(item)
        return Response.json(item)
      }
      if (url.startsWith('/api/content?')) {
        const status = new URLSearchParams(url.split('?')[1]).get('status')
        return Response.json(content.filter((item) => item.status === status))
      }
      if (url === '/api/content/captured' && method === 'PATCH') {
        content = content.map((item) => ({ ...item, ...body }))
        return Response.json(content[0])
      }
      if (url.startsWith('/api/feed?'))
        return Response.json({
          items: [news],
          sources: [
            {
              source: 'github',
              label: 'GitHub Top 5',
              status: 'ok',
              message: '已更新',
              updated_at: stamp,
            },
          ],
        })
      if (url === '/api/feed/news/save') {
        content.push({
          id: 'saved',
          type: 'link',
          status: 'inbox',
          title: news.title,
          content: news.summary,
          summary: '',
          source: news.url,
          tags: [],
          filename: null,
          created_at: stamp,
          updated_at: stamp,
        })
        return Response.json(content[0])
      }
      if (url === '/api/conversations' && method === 'POST')
        return Response.json({
          id: 'new-chat',
          title: 'New Chat',
          created_at: stamp,
          updated_at: stamp,
        })
      if (url === '/api/today')
        return Response.json({ feed: [], tasks, inbox_count: content.length })
      if (url === '/api/tasks' && method === 'POST') {
        const task = {
          id: 'task',
          title: body.title,
          due_at: body.due_at,
          completed: false,
          created_at: stamp,
          updated_at: stamp,
        }
        tasks.push(task)
        return Response.json(task)
      }
      if (url === '/api/tasks/task' && method === 'PATCH') {
        tasks = tasks.map((item) => ({ ...item, ...body }))
        return Response.json(tasks[0])
      }
      if (url === '/api/tasks/task' && method === 'DELETE') {
        tasks = []
        return new Response(null, { status: 204 })
      }
      if (url === '/api/automations' && method === 'POST') {
        const automation: Automation = {
          id: 'automation',
          name: body.name,
          prompt: body.prompt,
          trigger_type: 'cron',
          schedule: { hour: 9, minute: 0 },
          timezone: body.timezone,
          enabled: true,
        }
        automations.push(automation)
        return Response.json(automation)
      }
      if (url === '/api/automations') return Response.json(automations)
      if (url === '/api/automations/automation' && method === 'PATCH') {
        automations = automations.map((item) => ({ ...item, ...body }))
        return Response.json(automations[0])
      }
      if (url === '/api/automations/automation' && method === 'DELETE') {
        automations = []
        return new Response(null, { status: 204 })
      }
      if (url.endsWith('/runs'))
        return Response.json([
          {
            run_id: 'run',
            status: 'success',
            started_at: stamp,
            finished_at: stamp,
            result_preview: 'Your daily brief is ready.',
          },
        ])
      return Response.json(
        { error: { message: `Unexpected test request: ${method} ${url}` } },
        { status: 404 }
      )
    })
  )
})
function mount(children: React.ReactNode, path = '/') {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={cache}>
      <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}
function AssistantState() {
  const location = useLocation()
  return <output>{JSON.stringify(location.state)}</output>
}
function TodayWithDrawer() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button onClick={() => setOpen(true)}>Automations</button>
      <PlansPage />
      {open && <AutomationsDrawer onClose={() => setOpen(false)} />}
    </>
  )
}

test('unified capture saves text and the AI preference', async () => {
  mount(<ContentPage status="inbox" />)
  const user = userEvent.setup()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '添加到 Inbox' }))
  await user.type(screen.getByLabelText('文字或链接'), '关于信息汇聚的新想法')
  await user.click(screen.getByLabelText('使用 AI 整理'))
  await user.click(screen.getByRole('button', { name: '收进 Inbox' }))
  expect(await screen.findByRole('heading', { name: '关于信息汇聚的新想法' })).toBeVisible()
  expect(requests.find((item) => item.url === '/api/inbox/import')?.body).toEqual({
    text: '关于信息汇聚的新想法',
    use_ai: false,
  })
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(await screen.findByText('已归类至 未分类 · 本地整理', {}, { timeout: 4000 })).toBeVisible()
})
test('inbox card opens a preview with edit, open-original and download actions', async () => {
  content.push({
    id: 'captured',
    type: 'file',
    status: 'inbox',
    title: 'File note',
    content: 'Full content body',
    summary: 'A short summary',
    source: 'https://example.org/doc',
    tags: ['x'],
    filename: 'doc.pdf',
    created_at: stamp,
    updated_at: stamp,
    processing_status: 'ready',
    ai_processed: true,
  })
  mount(<ContentPage status="inbox" />)
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'File note' }))
  const dialog = await screen.findByRole('dialog', { name: 'File note' })
  expect(within(dialog).getByText('Full content body')).toBeVisible()
  expect(within(dialog).getAllByText('A short summary')).toHaveLength(1)
  expect(within(dialog).getByRole('link', { name: /打开原文/ })).toHaveAttribute(
    'href',
    'https://example.org/doc'
  )
  expect(within(dialog).getByRole('link', { name: /下载原件/ })).toBeInTheDocument()
  await user.click(within(dialog).getByRole('button', { name: '编辑' }))
  expect(await screen.findByRole('heading', { name: '编辑内容' })).toBeVisible()
})
test('deleting a recent import does not refetch the deleted ID', async () => {
  mount(<ContentPage status="inbox" />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: '添加到 Inbox' }))
  await user.type(screen.getByLabelText('文字或链接'), 'Temporary note')
  await user.click(screen.getByLabelText('使用 AI 整理'))
  await user.click(screen.getByRole('button', { name: '收进 Inbox' }))
  await user.click(await screen.findByRole('button', { name: '删除 Temporary note' }))
  await screen.findByText('已删除内容')
  await waitFor(() => expect(screen.queryByRole('heading', { name: 'Temporary note' })).toBeNull())
  const removed = requests.findIndex((request) => request.method === 'DELETE')
  expect(removed).toBeGreaterThan(-1)
  expect(
    requests.slice(removed + 1).filter((request) => request.url === '/api/content/captured')
  ).toEqual([])
})

test('Feed saves to Inbox and carries a separate reference into a new Assistant chat', async () => {
  mount(
    <Routes>
      <Route path="/feed" element={<FeedPage />} />
      <Route path="/assistant" element={<AssistantState />} />
    </Routes>,
    '/feed'
  )
  const user = userEvent.setup()
  await screen.findByRole('heading', { name: news.title })
  expect(screen.getByRole('link', { name: 'Read' })).toHaveAttribute('href', news.url)
  await user.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByRole('button', { name: '已收进 Inbox' })).toBeDisabled()
  expect(content[0].status).toBe('inbox')
  await user.click(screen.getByRole('button', { name: 'Ask AI' }))
  const state = JSON.parse((await screen.findByRole('status')).textContent!)
  expect(state.draft).toContain('解读')
  expect(state.reference).toEqual({
    title: news.title,
    content: `${news.summary}\n\n来源：${news.url}`,
  })
  expect(
    requests.filter((item) => item.url === '/api/conversations' && item.method === 'POST')
  ).toHaveLength(1)
})

test('Today manages tasks and its automation drawer creates, pauses, shows runs, deletes and closes with Escape', async () => {
  mount(<TodayWithDrawer />)
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('新增待办'), '读一篇论文')
  await user.click(screen.getByRole('button', { name: '添加' }))
  const checkbox = await screen.findByRole('checkbox', { name: '完成 读一篇论文' })
  await user.click(checkbox)
  await user.click(screen.getByRole('button', { name: /已完成/ }))
  await user.click(await screen.findByRole('checkbox', { name: '恢复 读一篇论文' }))
  await user.click(screen.getByRole('button', { name: /待完成/ }))
  await user.click(await screen.findByRole('button', { name: '删除待办 读一篇论文' }))
  await waitFor(() => expect(tasks).toHaveLength(0))
  const trigger = screen.getByRole('button', { name: 'Automations' })
  await user.click(trigger)
  expect(screen.getByRole('dialog')).toHaveFocus()
  await user.click(screen.getByRole('button', { name: '创建每日任务' }))
  await user.type(screen.getByLabelText('任务名称'), '每日研究')
  await user.type(screen.getByLabelText('让息流做什么'), '汇总最新研究进展')
  await user.click(screen.getByRole('button', { name: '创建任务' }))
  await user.click(await screen.findByRole('switch', { name: '每日研究 启用' }))
  await waitFor(() => expect(automations[0].enabled).toBe(false))
  await user.click(screen.getByRole('button', { name: '运行记录' }))
  expect(await screen.findByText('Your daily brief is ready.')).toBeVisible()
  await user.click(screen.getByRole('button', { name: '删除自动任务 每日研究' }))
  await waitFor(() => expect(automations).toHaveLength(0))
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(trigger).toHaveFocus()
})
