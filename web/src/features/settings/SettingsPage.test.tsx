import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { App } from '../../app/App'

beforeEach(() => {
  localStorage.clear()
  window.dispatchEvent(new StorageEvent('storage', { key: null }))
  let preferenceSnapshot = {
    preferences: {
      displayName: '',
      email: '',
      bio: '',
      avatar: '',
      theme: 'light',
      fontSize: 'small',
      fontFamily: 'system',
      density: 'comfortable',
      reducedMotion: false,
    },
    revision: 0,
    initialized: false,
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, options?: RequestInit) => {
      const url = String(input)
      if (url === '/api/appearance/backgrounds')
        return Response.json({ settings: { mode: 'blank', selected: null }, images: [] })
      if (url.startsWith('/api/appearance/models/')) return Response.json(null)
      if (url === '/api/settings/preferences') {
        if (options?.method === 'PUT') {
          const body = JSON.parse(String(options.body))
          if (body.expected_revision !== preferenceSnapshot.revision)
            return Response.json({ error: { code: 'conflict' } }, { status: 409 })
          preferenceSnapshot = {
            preferences: { ...preferenceSnapshot.preferences, ...body.changes },
            revision: preferenceSnapshot.revision + 1,
            initialized: true,
          }
        }
        return Response.json(preferenceSnapshot)
      }
      if (url === '/api/settings/model')
        return Response.json({
          provider: 'deepseek',
          model: 'deepseek-v4-pro',
          base_url: 'https://api.deepseek.com',
          api_key_set: true,
        })
      if (url === '/api/models/catalog')
        return Response.json({
          deepseek: { models: ['deepseek-v4-pro'], base_url: 'https://api.deepseek.com' },
        })
      if (url === '/api/settings/data')
        return Response.json({
          data_dir: '/data',
          database: '/data/app.sqlite3',
          content_count: 0,
          scheduler_active: false,
        })
      if (url === '/api/automations') return Response.json([])
      if (url.startsWith('/api/feed')) return Response.json({ items: [], sources: [] })
      if (url === '/api/today') return Response.json({ feed: [], tasks: [], inbox_count: 0 })
      return Response.json([])
    })
  )
})
function mount(path = '/settings') {
  localStorage.setItem(
    'xiliu-guide-v1',
    JSON.stringify({ version: 2, status: 'completed', step: 0 })
  )
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
}
test('settings opens above the current page; profile and appearance persist', async () => {
  const view = mount('/feed'),
    user = userEvent.setup()
  await user.click(
    within(screen.getByRole('navigation', { name: '快捷导航' })).getByRole('link', { name: '设置' })
  )
  expect(screen.getByRole('dialog', { name: '设置' })).toBeVisible()
  await user.type(screen.getByLabelText('昵称'), '小溪')
  await user.click(screen.getByRole('button', { name: '保存个人信息' }))
  expect(await screen.findByText('个人信息已保存')).toBeVisible()
  await user.click(screen.getByRole('tab', { name: '外观' }))
  await user.click(screen.getByRole('combobox', { name: '主题' }))
  await user.click(screen.getByRole('option', { name: /深色/ }))
  await user.click(screen.getByRole('combobox', { name: '字体大小' }))
  await user.click(screen.getByRole('option', { name: /大/ }))
  await waitFor(() => expect(document.documentElement).toHaveAttribute('data-theme', 'dark'))
  expect(document.documentElement.style.fontSize).toBe('18px')
  await user.click(screen.getByRole('button', { name: '关闭设置' }))
  expect(screen.getByRole('heading', { name: '资讯' })).toBeVisible()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  view.unmount()
  mount()
  expect(screen.getByLabelText('昵称')).toHaveValue('小溪')
  expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  expect(document.documentElement.style.fontSize).toBe('18px')
})

test('global pill navigation sits above the page, not inside the 今日 heading', async () => {
  mount('/today')
  const user = userEvent.setup()
  const nav = screen.getByRole('navigation', { name: '快捷导航' })
  expect(within(nav).getByRole('link', { name: '助手' })).toHaveAttribute('href', '/assistant')
  expect(within(nav).getByRole('link', { name: '设置' })).toHaveAttribute('href', '/settings')
  const header = screen.getByRole('heading', { name: /今天从容开始/ }).closest('header')!
  expect(within(header).queryByRole('link', { name: '助手' })).not.toBeInTheDocument()
  await user.click(within(nav).getByRole('link', { name: '资讯' }))
  await waitFor(() => expect(screen.getByRole('heading', { name: '资讯' })).toBeVisible())
})
test('automation management is inside 设置 instead of the global toolbar', async () => {
  mount()
  const user = userEvent.setup()
  expect(screen.queryByRole('button', { name: '自动任务' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('tab', { name: '自动化' }))
  const panel = screen.getByRole('tabpanel', { name: '自动化' })
  await user.click(within(panel).getByRole('button', { name: '创建每日任务' }))
  expect(within(panel).getByLabelText('任务名称')).toBeVisible()
  expect(screen.getAllByRole('dialog')).toHaveLength(1)
})
