import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { App } from './App'

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

test('App 设置 overlay preserves page and keyboard navigation selects panels', async () => {
  const view = mount('/today'),
    user = userEvent.setup()
  await user.click(
    within(screen.getByRole('navigation', { name: '快捷导航' })).getByRole('link', { name: '设置' })
  )
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
