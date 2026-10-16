import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { AssistantPage } from '../assistant/AssistantPage'
import { ChatProvider } from '../assistant/ChatProvider'
import { createSeed } from '../demo/seed'
import { getGuideProgress, resetGuide, startGuide, recordGuideAction } from './progress'

afterEach(() => vi.unstubAllGlobals())
test('clearing a referenced chat does not count as successfully asking about the document', async () => {
  localStorage.clear()
  resetGuide()
  startGuide()
  const state = createSeed(),
    item = state.content[0]
  recordGuideAction({ type: 'saved', item })
  recordGuideAction({ type: 'archived', items: [{ ...item, status: 'knowledge' }] })
  vi.stubGlobal('fetch', async (input: string) => {
    if (input.endsWith('/chat'))
      return new Response(
        JSON.stringify({
          type: 'final',
          role: 'event',
          reset_messages: true,
          text: '对话已清除',
          message_id: 'clear-event',
        }) + '\n'
      )
    if (input === '/api/conversations') return Response.json(state.conversations)
    if (input.endsWith('/messages')) return Response.json([])
    if (input === '/api/settings/model')
      return Response.json({
        provider: 'custom',
        model: 'test-model',
        base_url: '',
        api_key_set: true,
      })
    if (input === '/api/models/catalog')
      return Response.json({ custom: { base_url: '', models: ['test-model'] } })
    if (input.startsWith('/api/conversations/')) return Response.json(state.conversations[0])
    return Response.json([])
  })
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter
        initialEntries={[
          {
            pathname: '/assistant',
            search: '?c=chat-welcome',
            state: {
              draft: '/clear',
              reference: { documentId: item.id, title: item.title, content: item.content },
            },
          },
        ]}
      >
        <ChatProvider>
          <AssistantPage />
        </ChatProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
  await userEvent.click(await screen.findByRole('button', { name: '发送消息' }))
  await waitFor(() =>
    expect(screen.queryByRole('button', { name: '停止回复' })).not.toBeInTheDocument()
  )
  expect(getGuideProgress()).toMatchObject({ step: 2, status: 'active' })
})
