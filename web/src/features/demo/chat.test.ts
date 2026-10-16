import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { readNDJSON } from '../../lib/api'
import { startDemoChat, stopDemoChat, cancelAllDemoChats } from './chat'
import { mutateDemo, readDemoState, resetDemoState } from './store'

beforeEach(async () => {
  await resetDemoState()
  vi.useFakeTimers()
})
afterEach(() => {
  cancelAllDemoChats()
  vi.useRealTimers()
})
async function collect(response: Response) {
  const events = []
  for await (const event of readNDJSON(response)) events.push(event)
  return events
}
test('template replies use the supplied reference and are clearly labelled', async () => {
  const response = await startDemoChat('chat-welcome', {
    text: '总结资料',
    context: '标题：我的方法\n\n先阅读，再记录。',
  })
  const pending = collect(response)
  await vi.runAllTimersAsync()
  const events = await pending
  expect(events.at(-1)?.text).toContain('演示回复')
  expect(events.at(-1)?.text).toContain('先阅读，再记录')
  expect((await readDemoState()).messages.at(-1)?.content).toContain('演示回复')
})
test('stopping one conversation does not stop another', async () => {
  await mutateDemo((state) => {
    state.conversations.push({ ...state.conversations[0], id: 'chat-other' })
  })
  const one = collect(await startDemoChat('chat-welcome', { text: '有哪些功能' }))
  const two = collect(await startDemoChat('chat-other', { text: '有哪些功能' }))
  expect(stopDemoChat('chat-welcome')).toBe(true)
  await vi.runAllTimersAsync()
  expect((await one).at(-1)?.metadata?.cancelled).toBe(true)
  expect((await two).at(-1)?.metadata?.cancelled).not.toBe(true)
})
test.each(['reset', 'delete', 'abort'])(
  '%s during a reply prevents late persistence',
  async (action) => {
    const controller = new AbortController()
    const pending = collect(
      await startDemoChat('chat-welcome', { text: '有哪些功能' }, controller.signal)
    )
    if (action === 'reset') {
      cancelAllDemoChats()
      await resetDemoState()
    } else if (action === 'delete')
      await mutateDemo((state) => {
        state.conversations = []
        state.messages = []
      })
    else controller.abort()
    await vi.runAllTimersAsync()
    await pending
    const state = await readDemoState()
    expect(
      state.messages.some(
        (message) => message.role === 'assistant' && message.content.includes('功能包括')
      )
    ).toBe(false)
  }
)
