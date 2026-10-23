import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { App } from './App'
import { startGuide } from '../features/onboarding/progress'

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
test('home themes share the same top right controls without workspace breadcrumbs', async () => {
  const view = mount('/today')
  const user = userEvent.setup()
  const controls = () =>
    Array.from(view.container.querySelectorAll('.workspace-controls button')).map((button) =>
      button.getAttribute('aria-label')
    )
  const original = controls()
  expect(original).toEqual(['原有主题', '山水工作台'])
  expect(screen.queryByText('我的空间')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '山水工作台' }))
  expect(controls()).toEqual(original)
  expect(screen.queryByRole('link', { name: '外观设置' })).not.toBeInTheDocument()
})

test('assistant inbox and plans retain the committed layout scope', async () => {
  const view = mount('/inbox')
  expect(view.container.querySelector('.app-shell')).not.toHaveClass('workspace-v2')
  expect(view.container.querySelector('.workbench-reading-pane')).not.toBeInTheDocument()
  const user = userEvent.setup()
  for (const name of ['助手', '个人计划']) {
    await user.click(
      within(screen.getByRole('navigation', { name: '主导航' })).getByRole('link', { name })
    )
    await waitFor(() =>
      expect(view.container.querySelector('.app-shell')).not.toHaveClass('workspace-v2')
    )
  }
})
test('App icon rail navigates to every page', async () => {
  const view = mount('/today'),
    user = userEvent.setup()
  const navigation = screen.getByRole('navigation', { name: '主导航' })
  for (const [label, path] of [
    ['资讯', '/feed'],
    ['收件箱', '/inbox'],
    ['知识库', '/knowledge'],
    ['个人计划', '/plans'],
    ['助手', '/assistant'],
    ['今日', '/today'],
  ]) {
    const link = within(navigation).getByRole('link', { name: label })
    await user.click(link)
    await waitFor(() =>
      expect(view.container.querySelector('[data-route-path]')).toHaveAttribute(
        'data-route-path',
        path
      )
    )
    expect(link).toHaveAttribute('aria-current', 'page')
  }
})

test('tour keeps its origin when the workbench homepage changes the shell', async () => {
  localStorage.setItem('xiliu-home-theme-v1', 'workbench')
  const view = mount('/inbox'),
    user = userEvent.setup()
  act(() => startGuide())
  await user.click(screen.getByRole('button', { name: '下一步' }))
  await waitFor(() =>
    expect(view.container.querySelector('[data-route-path]')).toHaveAttribute(
      'data-route-path',
      '/today'
    )
  )
  await user.click(screen.getByRole('button', { name: '跳过引导' }))
  await waitFor(() =>
    expect(view.container.querySelector('[data-route-path]')).toHaveAttribute(
      'data-route-path',
      '/inbox'
    )
  )
})

test('App 设置 overlay preserves page and keyboard navigation selects panels', async () => {
  const view = mount('/today'),
    user = userEvent.setup()
  await user.click(screen.getByRole('link', { name: '设置' }))
  expect(screen.getByRole('dialog', { name: '设置' })).toBeVisible()
  await user.click(screen.getByRole('tab', { name: '个人信息' }))
  await user.keyboard('{ArrowRight}')
  expect(screen.getByRole('tabpanel', { name: '外观' })).toBeVisible()
  await user.keyboard('{End}')
  expect(screen.getByRole('tabpanel', { name: '数据与存储' })).toBeVisible()
  await user.keyboard('{Home}')
  expect(screen.getByRole('tabpanel', { name: '个人信息' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: '关闭设置' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(view.container.querySelector('[data-route-path]')).toHaveAttribute(
    'data-route-path',
    '/today'
  )
})

test('settings panels preserve the original feed return route', async () => {
  const user = userEvent.setup()
  const view = render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={['/feed?source=manual']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
  const rail = screen.getByRole('navigation', { name: '主导航' })
  await user.click(within(rail.closest('aside')!).getByRole('link', { name: '设置' }))
  const dialog = await screen.findByRole('dialog', { name: '设置' })
  await user.click(within(dialog).getByRole('tab', { name: '模型与连接' }))
  await user.click(within(dialog).getByRole('tab', { name: '个人信息' }))
  await user.click(screen.getByRole('button', { name: '关闭设置' }))
  await waitFor(() =>
    expect(view.container.querySelector('[data-route-path]')).toHaveAttribute(
      'data-route-path',
      '/feed'
    )
  )
})
