import type { Message, WebEvent } from '../../lib/types'
import { mutateDemo, readDemoState } from './store'
import { DemoError } from './types'
const active = new Map<string, () => void>()
export function stopDemoChat(cid: string) {
  const stop = active.get(cid)
  stop?.()
  return Boolean(stop)
}
export function cancelAllDemoChats() {
  for (const stop of [...active.values()]) stop()
}
function reply(text: string, context?: string): string {
  if (context)
    return `**演示回复**\n\n以下仅整理本轮参考，没有调用真实模型：\n\n${context.slice(0, 1800)}\n\n可以先提炼一个要点，补上自己的理解，再把下一步行动放进个人计划。`
  if (/功能|息流|怎么用|开始/.test(text))
    return '**演示回复**\n\n息流的功能包括：资讯发现资讯，收件箱收集文字和链接，知识库整理和检索，助手围绕资料提问，个人计划安排下一步。\n\n先收藏一条资讯，再归档并点击引用提问。使用指南逐项介绍了所有功能。'
  return '**演示回复**\n\n这里使用本地示例模板，无法回答任意问题或执行 AI 操作。\n\n试试“息流有哪些功能？”，或在知识库点击引用提问，再问“请总结这份资料”。完整应用可连接自己的模型。'
}
export async function startDemoChat(
  cid: string,
  body: { text: string; context?: string },
  signal?: AbortSignal
): Promise<Response> {
  if (
    !body.text?.trim() ||
    body.text.length > 40000 ||
    (body.context && body.context.length > 40000)
  )
    throw new DemoError('消息为空或过长。')
  if (signal?.aborted) throw new DOMException('请求已停止', 'AbortError')
  if (active.has(cid)) throw new DemoError('当前会话正在回复，请先停止。', 'conversation_busy', 409)
  let cancelled = false,
    finished = false,
    generation = '',
    timer: ReturnType<typeof setTimeout> | undefined
  let controller: ReadableStreamDefaultController<Uint8Array> | undefined
  const encoder = new TextEncoder()
  const emit = (event: WebEvent) =>
    controller?.enqueue(encoder.encode(`${JSON.stringify(event)}\n`))
  const finish = async () => {
    if (finished) return
    finished = true
    clearTimeout(timer)
    const text = cancelled ? '**演示回复**\n\n本次回复已停止。' : reply(body.text, body.context)
    let message: Message | undefined
    try {
      message = await mutateDemo((draft) => {
        if (
          signal?.aborted ||
          draft.generation !== generation ||
          !draft.conversations.some((item) => item.id === cid)
        )
          return undefined
        const item: Message = {
          id: crypto.randomUUID(),
          conversation_id: cid,
          seq:
            Math.max(
              0,
              ...draft.messages
                .filter((item) => item.conversation_id === cid)
                .map((item) => item.seq)
            ) + 1,
          role: 'assistant',
          content: text,
          created_at: new Date().toISOString(),
          metadata_json: JSON.stringify({ cancelled }),
        }
        draft.messages.push(item)
        return item
      })
      emit({
        type: 'final',
        message_id: message?.id ?? crypto.randomUUID(),
        text: message?.content ?? '演示回复已结束。',
        metadata: { cancelled: cancelled || !message },
      })
    } catch (error) {
      emit({
        type: 'error',
        message: error instanceof Error ? error.message : '演示回复未能保存。',
      })
    } finally {
      controller?.close()
      if (active.get(cid) === stop) active.delete(cid)
      signal?.removeEventListener('abort', stop)
    }
  }
  const stop = () => {
    cancelled = true
    if (controller) void finish()
  }
  if (active.has(cid)) throw new DemoError('当前会话正在回复。', 'conversation_busy', 409)
  active.set(cid, stop)
  try {
    generation = (await readDemoState()).generation
    await mutateDemo((draft) => {
      if (cancelled || signal?.aborted || draft.generation !== generation)
        throw new DOMException('请求已停止，请重新发送。', 'AbortError')
      const conversation = draft.conversations.find((item) => item.id === cid)
      if (!conversation) throw new DemoError('会话不存在。', 'not_found', 404)
      if (body.text.trim() === '/clear')
        draft.messages = draft.messages.filter((item) => item.conversation_id !== cid)
      else
        draft.messages.push({
          id: crypto.randomUUID(),
          conversation_id: cid,
          seq:
            Math.max(
              0,
              ...draft.messages
                .filter((item) => item.conversation_id === cid)
                .map((item) => item.seq)
            ) + 1,
          role: 'user',
          content: body.text,
          created_at: new Date().toISOString(),
          metadata_json: '{}',
        })
      if (conversation.title === '新对话') conversation.title = body.text.slice(0, 30)
      conversation.updated_at = new Date().toISOString()
    })
  } catch (error) {
    if (active.get(cid) === stop) active.delete(cid)
    throw error
  }
  signal?.addEventListener('abort', stop, { once: true })
  const stream = new ReadableStream<Uint8Array>({
    start(value) {
      controller = value
      if (body.text.trim() === '/clear') {
        emit({
          type: 'final',
          role: 'event',
          text: '演示会话已清除。',
          reset_messages: true,
          message_id: crypto.randomUUID(),
        })
        finished = true
        active.delete(cid)
        signal?.removeEventListener('abort', stop)
        controller.close()
        return
      }
      emit({ type: 'status', message: '正在准备本地演示回复…' })
      timer = setTimeout(() => {
        void finish()
      }, 900)
      if (signal?.aborted || cancelled) stop()
    },
    cancel() {
      controller = undefined
      cancelled = true
      void finish()
    },
  })
  return new Response(stream, { headers: { 'Content-Type': 'application/x-ndjson' } })
}
