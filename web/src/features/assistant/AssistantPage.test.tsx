import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { AssistantPage } from './AssistantPage'

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
        <AssistantPage />
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
  await user.selectOptions(screen.getByLabelText('当前对话模型'), 'deepseek-v4-pro')
  await waitFor(() => expect(patches).toEqual([{ model_override: 'deepseek-v4-pro' }]))
})
test('slash opens menu and keyboard completes a command', async () => {
  mount()
  const user = userEvent.setup()
  await user.type(screen.getByRole('textbox', { name: '消息' }), '/')
  expect(await screen.findByRole('listbox', { name: '命令建议' })).toBeVisible()
  await user.keyboard('{Enter}')
  expect(screen.getByRole('textbox', { name: '消息' })).toHaveValue('/clear ')
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
  await user.selectOptions(screen.getByLabelText('当前对话模型'), 'deepseek-v4-pro')
  await user.click(screen.getByRole('button', { name: 'Second chat' }))
  await screen.findByText('Second history')
  finish(Response.json({ ...first, model_override: 'deepseek-v4-pro' }))
  await waitFor(() => expect(screen.getByLabelText('当前对话模型')).toBeEnabled())
  expect(screen.getByLabelText('当前对话模型')).toHaveValue('')
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
