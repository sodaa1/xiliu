import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { TodayPage } from './TodayPage'
function State() {
  const location = useLocation()
  return <output>{JSON.stringify(location.state)}</output>
}
function mount() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) =>
      url === '/api/conversations'
        ? Response.json({ id: 'new-chat' })
        : Response.json({ error: { message: 'offline' } }, { status: 503 })
    )
  )
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}
    >
      <MemoryRouter>
        <Routes>
          <Route path="/" element={<TodayPage />} />
          <Route path="/assistant" element={<State />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}
afterEach(() => vi.unstubAllGlobals())
test('quick capture starts with the home draft and closing it keeps the draft', async () => {
  mount()
  fireEvent.change(screen.getByLabelText('问问息流'), { target: { value: 'A note worth keeping' } })
  fireEvent.click(screen.getByRole('button', { name: '快速收录' }))
  expect(await screen.findByLabelText('文字或链接')).toHaveValue('A note worth keeping')
  fireEvent.click(screen.getByRole('button', { name: '关闭弹窗' }))
  expect(screen.getByLabelText('问问息流')).toHaveValue('A note worth keeping')
})
test('home sends its draft into a new assistant conversation', async () => {
  mount()
  fireEvent.change(screen.getByLabelText('问问息流'), {
    target: { value: 'Help me plan tomorrow' },
  })
  fireEvent.submit(screen.getByLabelText('问问息流').closest('form')!)
  expect(await screen.findByRole('status')).toHaveTextContent('Help me plan tomorrow')
})

test('switching background recovers after the previous image failed to load', async () => {
  let selected = 'first'
  vi.stubGlobal('fetch', async (url: string) =>
    url === '/api/appearance/backgrounds'
      ? Response.json({
          settings: { mode: 'custom', selected },
          images: [
            { id: selected, name: 'wallpaper.png', url: `/api/appearance/backgrounds/${selected}` },
          ],
        })
      : Response.json({ error: { message: 'offline' } }, { status: 503 })
  )
  const view = render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <TodayPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
  await waitFor(() =>
    expect(view.container.querySelector('.home-wallpaper')).toHaveAttribute(
      'src',
      '/api/appearance/backgrounds/first'
    )
  )
  fireEvent.error(view.container.querySelector('.home-wallpaper')!)
  expect(view.container.querySelector('.home-wallpaper')).not.toBeVisible()
  selected = 'second'
  window.dispatchEvent(new Event('xiliu-home-background'))
  await waitFor(() =>
    expect(view.container.querySelector('.home-wallpaper')).toHaveAttribute(
      'src',
      '/api/appearance/backgrounds/second'
    )
  )
  expect(view.container.querySelector('.home-wallpaper')).toBeVisible()
})
