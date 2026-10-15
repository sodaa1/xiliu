import { act, render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import type { ContextType } from 'react'
import { ChatContext } from '../assistant/chat-context'
import { CompanionController } from './CompanionController'

afterEach(() => {
  delete window.__TAURI__
  vi.unstubAllGlobals()
})

function mount(fail = false) {
  const handlers = new Map<string, (event: { payload: unknown }) => void>()
  const calls: { name: string; args: Record<string, unknown> }[] = []
  const listeners = vi.fn()
  window.__TAURI__ = {
    core: {
      invoke: async (name, args) => {
        calls.push({ name, args })
        return undefined
      },
    },
    event: {
      listen: async <T,>(name: string, callback: (event: { payload: T }) => void) => {
        listeners(name)
        handlers.set(name, (event) => callback(event as { payload: T }))
        return () => {
          handlers.delete(name)
        }
      },
    },
  }
  const fetcher = vi.fn(async () =>
    fail
      ? Response.json({ error: { message: '创建失败' } }, { status: 503 })
      : Response.json({ id: 'new-chat', title: 'New' })
  )
  vi.stubGlobal('fetch', fetcher)
  const chat: NonNullable<ContextType<typeof ChatContext>> = {
    runs: {},
    errors: {},
    outcomes: {},
    selected: null,
    select: vi.fn(),
    dismiss: vi.fn(),
    stop: async () => {},
    send: vi.fn(async () => {}),
  }
  const client = new QueryClient()
  const content = (value: typeof chat) => (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/today']}>
        <ChatContext.Provider value={value}>
          <CompanionController />
        </ChatContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>
  )
  const view = render(content(chat))
  const emit = (name: string, payload: unknown) =>
    act(() => handlers.get(`companion-${name}`)?.({ payload }))
  const update = (value: Partial<typeof chat>) => view.rerender(content({ ...chat, ...value }))
  return { calls, fetcher, chat, emit, listeners, update }
}

test('only an explicit request creates a conversation, duplicate events are acknowledged once', async () => {
  const { calls, fetcher, chat, emit } = mount()
  await waitFor(() => expect(calls.some((c) => c.name === 'companion_ready')).toBe(true))
  expect(fetcher).not.toHaveBeenCalled()
  const request = { requestId: 'one', text: '帮我整理想法' }
  emit('request', request)
  emit('request', request)
  await waitFor(() => expect(calls.filter((c) => c.name === 'companion_ack')).toHaveLength(1))
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(chat.select).not.toHaveBeenCalled()
  expect(chat.send).toHaveBeenCalledWith('new-chat', '帮我整理想法', expect.any(Function))
  expect(calls.find((c) => c.name === 'companion_ack')?.args.cid).toBe('new-chat')
})

test('stopping a task never emits a successful-completion notification', async () => {
  const { calls, update } = mount()
  await waitFor(() => expect(calls.some((c) => c.name === 'companion_ready')).toBe(true))
  update({
    selected: 'cancelled',
    runs: {
      cancelled: {
        cid: 'cancelled',
        startedAt: 1,
        status: '正在停止…',
        steps: [],
        reasoning: '',
        stopping: true,
      },
    },
  })
  await act(async () => {})
  update({ runs: {} })
  await act(async () => {})
  expect(
    calls
      .filter((c) => c.name === 'companion_publish')
      .some((c) => (c.args.snapshot as { phase: string }).phase === 'success')
  ).toBe(false)
})

test('a confirmed successful final response produces a completion notification', async () => {
  const { calls, update } = mount()
  await waitFor(() => expect(calls.some((c) => c.name === 'companion_ready')).toBe(true))
  update({
    selected: 'done',
    runs: { done: { cid: 'done', startedAt: 1, status: '正在生成回答', steps: [], reasoning: '' } },
  })
  await act(async () => {})
  update({ runs: {}, outcomes: { done: 'success' } })
  await act(async () => {})
  expect(
    calls
      .filter((c) => c.name === 'companion_publish')
      .some((c) => (c.args.snapshot as { phase: string }).phase === 'success')
  ).toBe(true)
})

test('creation failure is acknowledged without sending or claiming success', async () => {
  const { calls, chat, emit } = mount(true)
  await waitFor(() => expect(calls.some((c) => c.name === 'companion_ready')).toBe(true))
  emit('request', { requestId: 'failed', text: '保留草稿' })
  await waitFor(() => expect(calls.some((c) => c.name === 'companion_ack')).toBe(true))
  expect(chat.send).not.toHaveBeenCalled()
  expect(calls.find((c) => c.name === 'companion_ack')?.args).toEqual({
    requestId: 'failed',
    cid: null,
    error: '创建失败',
  })
})

test('changing main page does not leave a gap in native request subscriptions', async () => {
  const { calls, emit, listeners } = mount()
  await waitFor(() => expect(calls.some((c) => c.name === 'companion_ready')).toBe(true))
  const initialSubscriptions = listeners.mock.calls.length
  emit('navigate', '/assistant')
  await act(async () => {})
  expect(listeners).toHaveBeenCalledTimes(initialSubscriptions)
})
