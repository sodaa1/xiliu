import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import type { Task } from '../../lib/workspace-api'
import { PlansPage } from './PlansPage'

let tasks: Task[]
let writes: { method: string; body: Record<string, unknown> }[]
let failWrites = false
const make = (
  id: string,
  title: string,
  scope: Task['scope'],
  due_at: string | null,
  parent_id: string | null = null,
  completed = false
): Task => ({
  id,
  title,
  scope,
  due_at,
  parent_id,
  completed,
  created_at: '',
  updated_at: '',
  demo_revision: 'r1',
})
beforeEach(() => {
  tasks = [
    make('goal', '作品集目标', 'goal', null),
    make('week', '首页周计划', 'week', null, 'goal'),
    make('dated', '整理首页', 'day', new Date(2026, 9, 18, 14).toISOString(), 'week'),
    make('undated', '无日期阅读', 'day', null),
    make('done', '已完成任务', 'day', new Date(2026, 9, 18, 9).toISOString(), 'week', true),
  ]
  writes = []
  failWrites = false
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      if (String(input) === '/api/tasks' && (!init?.method || init.method === 'GET'))
        return Response.json(tasks)
      if (String(input).startsWith('/api/tasks') && init?.method) {
        const body = init.body ? JSON.parse(String(init.body)) : {}
        writes.push({ method: init.method, body })
        if (failWrites)
          return Response.json({ error: { message: '保存失败，请重试' } }, { status: 503 })
        const id = String(input).split('/').at(-1)
        if (init.method === 'POST') {
          const item = {
            ...make('new', body.title, body.scope, body.due_at, body.parent_id),
            ...body,
          }
          tasks = [...tasks, item]
          return Response.json(item)
        }
        if (init.method === 'DELETE') {
          tasks = tasks.filter((t) => t.id !== id)
          return new Response(null, { status: 204 })
        }
        tasks = tasks.map((t) => (t.id === id ? { ...t, ...body } : t))
        return Response.json(tasks.find((t) => t.id === id))
      }
      return Response.json({})
    })
  )
})
afterEach(() => vi.unstubAllGlobals())

test('task row can enter in progress without completing and can restore all three states', async () => {
  const { user } = mount()
  const list = await screen.findByRole('region', { name: '个人任务清单' })
  const trigger = await within(list).findByRole('button', { name: '任务操作：整理首页' })
  for (const [name, status, completed] of [
    ['进行中', 'in_progress', false],
    ['已完成', 'completed', true],
    ['未开始', 'not_started', false],
  ] as const) {
    await user.click(trigger)
    await user.click(screen.getByRole('menuitemradio', { name }))
    await waitFor(() => expect(writes.at(-1)?.body).toMatchObject({ status, completed }))
  }
})
function mount() {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  cache.setQueryData(['today'], { tasks: [] })
  render(
    <QueryClientProvider client={cache}>
      <PlansPage initialDate={new Date(2026, 9, 18)} />
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), cache }
}

test('shows computed stats, searches tasks and keeps undated tasks off the calendar', async () => {
  const { user } = mount()
  const list = await screen.findByRole('region', { name: '个人任务清单' })
  expect(await within(list).findByText('无日期阅读')).toBeVisible()
  const day = screen.getByRole('region', { name: '所选日期计划' })
  expect(within(day).queryByText('无日期阅读')).not.toBeInTheDocument()
  expect(screen.getByLabelText('今日待办：已完成 1，共 2 项')).toBeInTheDocument()
  expect(screen.getByText('暂无记录')).toBeVisible()
  await user.type(screen.getByRole('searchbox', { name: '搜索任务' }), '无日期')
  expect(within(list).queryByText('整理首页')).not.toBeInTheDocument()
  expect(within(list).getByText('无日期阅读')).toBeVisible()
})

test('calendar selection and day/week/month modes show real distinct views', async () => {
  const { user } = mount()
  await screen.findByRole('button', { name: '2026年10月18日' })
  await user.click(screen.getByRole('button', { name: '2026年10月19日' }))
  expect(
    within(screen.getByRole('region', { name: '所选日期计划' })).queryByText('整理首页')
  ).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '周视图' }))
  expect(screen.getByLabelText('周历日期')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '日视图' }))
  expect(screen.getByLabelText('单日视图')).toHaveTextContent('19')
  await user.click(screen.getByRole('button', { name: '月视图' }))
  expect(screen.getByLabelText('月历日期')).toBeInTheDocument()
})

test('creates a scoped task with parent and local time; invalidates both caches', async () => {
  const { user, cache } = mount()
  await screen.findByText('暂无记录')
  await user.click(screen.getByRole('tab', { name: '周计划' }))
  await user.click(screen.getByRole('button', { name: '新建任务' }))
  const form = screen.getByRole('dialog', { name: '新建任务' })
  await user.type(within(form).getByLabelText('任务标题'), '下周设计')
  await user.selectOptions(within(form).getByLabelText('关联上级计划'), 'goal')
  fireEvent.change(within(form).getByLabelText('开始日期'), {
    target: { value: '2026-10-19T09:00' },
  })
  fireEvent.change(within(form).getByLabelText('截止日期'), {
    target: { value: '2026-10-19T09:30' },
  })
  await user.click(within(form).getByRole('button', { name: '创建任务' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(writes.at(-1)?.body).toMatchObject({
    title: '下周设计',
    scope: 'week',
    parent_id: 'goal',
    due_at: new Date(2026, 9, 19, 9, 30).toISOString(),
  })
  expect(
    await within(screen.getByRole('region', { name: '个人任务清单' })).findByText('下周设计')
  ).toBeVisible()
  expect(cache.getQueryState(['today'])?.isInvalidated).toBe(true)
})

test('completes, edits and deletes the same task in both panels', async () => {
  const { user, cache } = mount()
  const list = await screen.findByRole('region', { name: '个人任务清单' })
  await within(list).findByText('整理首页')
  await user.click(within(list).getByRole('checkbox', { name: '完成 整理首页' }))
  await waitFor(() =>
    expect(
      within(screen.getByRole('region', { name: '所选日期计划' })).getByRole('checkbox', {
        name: '恢复 整理首页',
      })
    ).toBeChecked()
  )
  expect(cache.getQueryState(['today'])?.isInvalidated).toBe(true)
  await user.click(within(list).getByRole('button', { name: '任务操作：整理首页' }))
  await user.click(screen.getByRole('menuitem', { name: '编辑任务' }))
  const dialog = screen.getByRole('dialog', { name: '编辑任务' })
  await user.clear(within(dialog).getByLabelText('任务标题'))
  await user.type(within(dialog).getByLabelText('任务标题'), '更新首页')
  await user.click(within(dialog).getByRole('button', { name: '保存修改' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(writes.at(-1)?.body).toMatchObject({ title: '更新首页', demo_revision: 'r1' })
  await user.click(within(list).getByRole('button', { name: '任务操作：更新首页' }))
  await user.click(screen.getByRole('menuitem', { name: '删除任务' }))
  await waitFor(() => expect(screen.queryByText('更新首页')).not.toBeInTheDocument())
})

test('failed creation keeps the draft visible and announces the error', async () => {
  const { user } = mount()
  failWrites = true
  await user.click(screen.getByRole('button', { name: '新建任务' }))
  const dialog = screen.getByRole('dialog', { name: '新建任务' })
  await user.type(within(dialog).getByLabelText('任务标题'), '保留草稿')
  await user.click(within(dialog).getByRole('button', { name: '创建任务' }))
  expect(await within(dialog).findByRole('alert')).toHaveTextContent('保存失败')
  expect(within(dialog).getByLabelText('任务标题')).toHaveValue('保留草稿')
})

test('editing an independent calendar task does not inherit the central parent filter', async () => {
  tasks.push(make('independent', '独立日期任务', 'day', new Date(2026, 9, 18, 10).toISOString()))
  const { user } = mount()
  const focus = screen.getByRole('region', { name: '本周专注' })
  await user.click(await within(focus).findByRole('button', { name: '首页周计划' }))
  const calendar = screen.getByRole('region', { name: '所选日期计划' })
  await user.click(within(calendar).getByRole('button', { name: '任务操作：独立日期任务' }))
  await user.click(screen.getByRole('menuitem', { name: '编辑任务' }))
  const dialog = screen.getByRole('dialog', { name: '编辑任务' })
  expect(within(dialog).getByLabelText('关联上级计划')).toHaveValue('')
  await user.click(within(dialog).getByRole('button', { name: '保存修改' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(tasks.find((task) => task.id === 'independent')?.parent_id).toBeNull()
})

test('a goal filter remains usable across its weekly and direct daily children', async () => {
  tasks.push(make('direct', '直连目标待办', 'day', null, 'goal'))
  const { user } = mount()
  const goals = screen.getByRole('region', { name: '长期目标进度' })
  await user.click(await within(goals).findByRole('button', { name: '作品集目标' }))
  const list = screen.getByRole('region', { name: '个人任务清单' })
  await waitFor(() => expect(within(list).getByText('首页周计划')).toBeVisible())
  await user.click(screen.getByRole('tab', { name: '日待办' }))
  await waitFor(() => expect(within(list).getByText('直连目标待办')).toBeVisible())
  expect(within(list).queryByText('无日期阅读')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '清除上级计划筛选' }))
  await waitFor(() => expect(within(list).getByText('无日期阅读')).toBeVisible())
})
