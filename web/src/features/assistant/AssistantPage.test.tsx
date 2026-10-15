import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { AssistantPage } from './AssistantPage'
import { App } from '../../app/App'
import { ChatProvider } from './ChatProvider'

const first = {
  id: 'one',
  title: 'First chat',
  model_override: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}
let conversations = [first]
let patches: unknown[] = []
beforeEach(() => {
  conversations = [first]
  patches = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = String(input)
      if (url === '/api/settings/model')
        return Response.json({
          provider: 'deepseek',
          model: 'deepseek-flash',
          base_url: 'https://api.deepseek.com',
          api_key_set: true,
        })
      if (url === '/api/models/catalog')
        return Response.json({
          deepseek: {
            base_url: 'https://api.deepseek.com',
            models: ['deepseek-flash', 'deepseek-v4-pro'],
          },
        })
      if (url === '/api/commands')
        return Response.json([
          { name: 'clear', description: '清除上下文' },
          { name: 'compress', description: '压缩上下文' },
          { name: 'skill', description: '使用技能' },
          { name: 'mcp', description: '使用连接' },
        ])
      if (url.startsWith('/api/capabilities/')) return Response.json([])
      if (url.startsWith('/api/feed')) return Response.json({ items: [], sources: [] })
      if (url === '/api/conversations' && init?.method === 'POST') {
        const created = { ...first, id: 'two', title: 'New Chat' }
        conversations = [created, ...conversations]
        return Response.json(created)
      }
      if (url === '/api/conversations') return Response.json(conversations)
      if (url.endsWith('/messages')) {
        const content = url.includes('/two/') ? 'Second history' : 'First history'
        return Response.json([
          {
            id: content,
            conversation_id: 'one',
            seq: 1,
            role: 'assistant',
            content,
            created_at: first.created_at,
            metadata_json: '{}',
          },
        ])
      }
      if (init?.method === 'PATCH') {
        patches.push(JSON.parse(String(init.body)))
        return Response.json({ ...first, model_override: 'deepseek-v4-pro' })
      }
      return Response.json(
        conversations.find((conversation) => url.endsWith(conversation.id)) ?? first
      )
    })
  )
})
function mount(path = '/assistant?c=one') {
  const query = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={query}>
      <MemoryRouter initialEntries={[path]}>
        <ChatProvider>
          <AssistantPage />
        </ChatProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}
test('new conversation appears in list and selected history reloads', async () => {
  mount()
  const user = userEvent.setup()
  expect(await screen.findByText('First history')).toBeVisible()
  await user.click(screen.getByRole('button', { name: /New Chat/ }))
  expect(await screen.findByRole('button', { name: 'New Chat' })).toBeVisible()
  expect(await screen.findByText('Second history')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'First chat' }))
  expect(await screen.findByText('First history')).toBeVisible()
})
test('model selector patches current conversation override', async () => {
  mount()
  const user = userEvent.setup()
  await screen.findByText('First history')
  await user.click(screen.getByRole('combobox', { name: '当前对话模型' }))
  await user.click(screen.getByRole('option', { name: 'deepseek-v4-pro' }))
  await waitFor(() => expect(patches).toEqual([{ model_override: 'deepseek-v4-pro' }]))
})

test('a running chat does not lock a new chat, deletion or a second send', async () => {
  const original = vi.mocked(fetch).getMockImplementation()!
  const streams = new Map<string, ReadableStreamDefaultController<Uint8Array>>()
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/chat'))
      return new Response(
        new ReadableStream({
          start(controller) {
            streams.set(url, controller)
          },
        })
      )
    return original(input, init)
  })
  mount()
  const user = userEvent.setup()
  await screen.findByText('First history')
  await user.type(screen.getByRole('textbox', { name: '消息' }), 'First turn')
  await user.click(screen.getByRole('button', { name: '发送消息' }))
  await waitFor(() => expect(streams.size).toBe(1))
  await user.click(screen.getByRole('button', { name: /新建 New Chat/ }))
  await screen.findByText('Second history')
  expect(screen.getByRole('textbox', { name: '消息' })).toBeEnabled()
  await user.click(screen.getByRole('button', { name: '对话操作：New Chat' }))
  expect(screen.getByRole('button', { name: '删除对话' })).toBeEnabled()
  await user.type(screen.getByRole('textbox', { name: '消息' }), 'Second turn')
  await user.click(screen.getByRole('button', { name: '发送消息' }))
  await waitFor(() => expect(streams.size).toBe(2))
  for (const [url, stream] of streams) {
    stream.enqueue(
      new TextEncoder().encode(
        JSON.stringify({ type: 'final', message_id: url, text: 'Done' }) + '\n'
      )
    )
    stream.close()
  }
  await waitFor(() => expect(screen.getByRole('textbox', { name: '消息' })).toBeEnabled())
})

test('stop targets only the visible running conversation and shows its saved cancellation', async () => {
  const original = vi.mocked(fetch).getMockImplementation()!
  let stream!: ReadableStreamDefaultController<Uint8Array>
  let stopped = false
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/chat'))
      return new Response(
        new ReadableStream({
          start(controller) {
            stream = controller
          },
        })
      )
    if (url === '/api/conversations/one/stop') {
      stopped = true
      stream.enqueue(
        new TextEncoder().encode(
          JSON.stringify({
            type: 'final',
            message_id: 'cancelled',
            text: '已停止本次回复。',
            metadata: { cancelled: true },
          }) + '\n'
        )
      )
      stream.close()
      return Response.json({ stopping: true })
    }
    if (url.endsWith('/messages') && stopped)
      return Response.json([
        {
          id: 'cancelled',
          conversation_id: 'one',
          seq: 2,
          role: 'assistant',
          content: '已停止本次回复。',
          metadata_json: '{"cancelled":true}',
        },
      ])
    return original(input, init)
  })
  mount()
  const user = userEvent.setup()
  await screen.findByText('First history')
  await user.type(screen.getByRole('textbox', { name: '消息' }), 'Wait')
  await user.click(screen.getByRole('button', { name: '发送消息' }))
  await user.click(await screen.findByRole('button', { name: '停止回复' }))
  expect(await screen.findByText('已停止本次回复。')).toBeVisible()
  await waitFor(() => expect(screen.getByRole('textbox', { name: '消息' })).toBeEnabled())
})

test('model menu keyboard action opens a local configuration card and preserves the draft', async () => {
  const original = vi.mocked(fetch).getMockImplementation()!
  let saved: unknown
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input) === '/api/settings/model' && init?.method === 'PUT') {
      saved = JSON.parse(String(init.body))
      return Response.json({
        provider: 'deepseek',
        model: 'deepseek-v4-pro',
        base_url: 'https://api.deepseek.com',
        api_key_set: true,
      })
    }
    return original(input, init)
  })
  mount()
  const user = userEvent.setup()
  await screen.findByText('First history')
  await user.type(screen.getByRole('textbox', { name: '消息' }), 'Keep this draft')
  const picker = screen.getByRole('combobox', { name: '当前对话模型' })
  picker.focus()
  await user.keyboard('{Enter}{Tab}{Enter}')
  expect(screen.getByRole('dialog', { name: '模型配置' })).toBeVisible()
  expect(screen.queryByRole('tablist', { name: '设置分类' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('combobox', { name: 'Model' }))
  await user.click(screen.getByRole('option', { name: 'deepseek-v4-pro' }))
  await user.click(screen.getByRole('button', { name: '保存设置' }))
  await waitFor(() =>
    expect(saved).toEqual({
      provider: 'deepseek',
      model: 'deepseek-v4-pro',
      base_url: 'https://api.deepseek.com',
      api_key: '',
    })
  )
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: '消息' })).toHaveValue('Keep this draft')
  expect(picker).toHaveFocus()
})
test('slash opens menu and keyboard completes a command', async () => {
  mount()
  const user = userEvent.setup()
  await user.type(screen.getByRole('textbox', { name: '消息' }), '/')
  expect(await screen.findByRole('listbox', { name: '命令建议' })).toBeVisible()
  await user.keyboard('{Enter}')
  expect(screen.getByRole('textbox', { name: '消息' })).toHaveValue('/clear ')
})

test('panel handles shrink the sidebar and composer within their original maximums', async () => {
  localStorage.removeItem('xiliu-conversation-width')
  localStorage.removeItem('xiliu-composer-height')
  mount()
  await screen.findByText('First history')
  const user = userEvent.setup()
  const sidebar = screen.getByRole('separator', { name: '调整对话侧栏宽度' })
  const maximum = Number(sidebar.getAttribute('aria-valuemax'))
  sidebar.focus()
  await user.keyboard('{ArrowLeft}')
  expect(sidebar).toHaveAttribute('aria-valuenow', String(maximum - 10))
  await user.keyboard('{End}')
  expect(sidebar).toHaveAttribute('aria-valuenow', String(maximum))
  const composer = screen.getByRole('separator', { name: '调整输入框高度' })
  composer.focus()
  await user.keyboard('{Home}')
  expect(composer).toHaveAttribute('aria-valuenow', '40')
  await user.keyboard('{ArrowDown}')
  expect(composer).toHaveAttribute('aria-valuenow', '40')
  localStorage.removeItem('xiliu-conversation-width')
  localStorage.removeItem('xiliu-composer-height')
})

test('empty assistant opens without a selected conversation', async () => {
  conversations = []
  mount('/assistant')
  expect(await screen.findByText('让信息流动，让思路清晰。')).toBeVisible()
  expect(screen.getByRole('textbox', { name: '消息' })).toBeEnabled()
})

test('two fast sends during initial creation start only one turn', async () => {
  conversations = []
  let finish!: (response: Response) => void
  const delayed = new Promise<Response>((resolve) => {
    finish = resolve
  })
  const original = vi.mocked(fetch).getMockImplementation()!
  let creates = 0
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input) === '/api/conversations' && init?.method === 'POST') {
      creates++
      return delayed
    }
    return original(input, init)
  })
  const user = userEvent.setup()
  mount('/assistant')
  await user.type(screen.getByRole('textbox', { name: '消息' }), 'Hello')
  await user.dblClick(screen.getByRole('button', { name: '发送消息' }))
  expect(creates).toBe(1)
  finish(Response.json({ ...first, id: 'created' }))
  await waitFor(() => expect(screen.getByRole('textbox', { name: '消息' })).toBeEnabled())
})

test('late model PATCH response cannot overwrite a newly selected conversation', async () => {
  conversations = [first, { ...first, id: 'two', title: 'Second chat' }]
  let finish!: (response: Response) => void
  const delayed = new Promise<Response>((resolve) => {
    finish = resolve
  })
  const original = vi.mocked(fetch).getMockImplementation()!
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (init?.method === 'PATCH') return delayed
    return original(input, init)
  })
  const user = userEvent.setup()
  mount()
  await screen.findByText('First history')
  await user.click(screen.getByRole('combobox', { name: '当前对话模型' }))
  await user.click(screen.getByRole('option', { name: 'deepseek-v4-pro' }))
  await user.click(screen.getByRole('button', { name: 'Second chat' }))
  await screen.findByText('Second history')
  finish(Response.json({ ...first, model_override: 'deepseek-v4-pro' }))
  await waitFor(() => expect(screen.getByLabelText('当前对话模型')).toBeEnabled())
  expect(screen.getByLabelText('当前对话模型')).toHaveTextContent('默认')
})

test('unmount during initial creation never starts a provider turn', async () => {
  conversations = []
  let finish!: (response: Response) => void
  const delayed = new Promise<Response>((resolve) => {
    finish = resolve
  })
  const original = vi.mocked(fetch).getMockImplementation()!
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input) === '/api/conversations' && init?.method === 'POST') return delayed
    return original(input, init)
  })
  const user = userEvent.setup(),
    view = mount('/assistant')
  await user.type(screen.getByRole('textbox', { name: '消息' }), 'Hello')
  await user.click(screen.getByRole('button', { name: '发送消息' }))
  view.unmount()
  finish(Response.json({ ...first, id: 'created' }))
  await new Promise((resolve) => setTimeout(resolve, 30))
  expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).endsWith('/chat'))).toBe(false)
})

test('switching pages keeps the turn alive and restores its timed thinking', async () => {
  let stream!: ReadableStreamDefaultController<Uint8Array>
  let signal: AbortSignal | undefined
  const original = vi.mocked(fetch).getMockImplementation()!
  let completed = false
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input).endsWith('/chat')) {
      signal = init?.signal as AbortSignal
      return new Response(
        new ReadableStream({
          start(controller) {
            stream = controller
          },
        })
      )
    }
    if (String(input).endsWith('/messages') && completed)
      return Response.json([
        {
          id: 'answer',
          conversation_id: 'one',
          seq: 2,
          role: 'assistant',
          content: 'Finished answer',
          metadata_json: JSON.stringify({
            thinking: { elapsed_ms: 65000, steps: ['Working'], reasoning: 'Thought detail' },
          }),
        },
      ])
    return original(input, init)
  })
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={query}>
      <MemoryRouter initialEntries={['/assistant?c=one']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
  const user = userEvent.setup()
  await screen.findByText('First history')
  await user.type(screen.getByRole('textbox', { name: '消息' }), 'Hello')
  await user.click(screen.getByRole('button', { name: '发送消息' }))
  await waitFor(() => expect(signal).toBeDefined())
  stream.enqueue(
    new TextEncoder().encode(
      JSON.stringify({ type: 'progress', message: 'Thinking', reasoning_delta: 'Thought detail' }) +
        '\n'
    )
  )
  await user.click(screen.getByRole('combobox', { name: '当前对话模型' }))
  await user.click(screen.getByRole('button', { name: '添加或配置模型' }))
  expect(signal!.aborted).toBe(false)
  await user.click(screen.getByRole('button', { name: '关闭模型配置' }))
  expect(await screen.findByText(/思考中/)).toBeVisible()
  const rail = screen.getByRole('navigation', { name: '主导航' })
  await user.click(within(rail).getByRole('link', { name: 'Feed' }))
  expect(await screen.findByRole('heading', { name: 'Feed' })).toBeVisible()
  expect(signal!.aborted).toBe(false)
  await user.click(within(rail).getByRole('link', { name: 'Assistant' }))
  expect(await screen.findByText(/思考中/)).toBeVisible()
  expect(signal!.aborted).toBe(false)
  completed = true
  stream.enqueue(
    new TextEncoder().encode(
      JSON.stringify({
        type: 'final',
        message_id: 'answer',
        text: 'Finished answer',
        metadata: {
          thinking: { elapsed_ms: 65000, steps: ['Working'], reasoning: 'Thought detail' },
        },
      }) + '\n'
    )
  )
  stream.close()
  expect(await screen.findByText('Finished answer')).toBeVisible()
  const summary = await screen.findByText(/1分5秒/)
  expect(summary.closest('details')).not.toHaveAttribute('open')
  await user.click(summary)
  expect(summary.closest('details')).toHaveAttribute('open')
  expect(screen.getByText('Thought detail')).not.toBeVisible()
  await user.click(screen.getByText('模型原始摘要'))
  expect(screen.getByText('Thought detail')).toBeVisible()
})
