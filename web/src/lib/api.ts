import { appFetch } from './app-fetch'
import type {
  Capability,
  Command,
  Conversation,
  Message,
  ModelCatalog,
  ModelSettings,
  WebEvent,
} from './types'

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}
async function httpError(response: Response): Promise<ApiError> {
  try {
    const payload = await response.json()
    return new ApiError(
      payload.error?.code ?? 'request_failed',
      payload.error?.message ?? '请求失败，请重试。'
    )
  } catch {
    return new ApiError('request_failed', `请求失败（${response.status}）。`)
  }
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await appFetch(`/api${path}`, {
    ...init,
    headers: { ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
  })
  if (!response.ok) throw await httpError(response)
  if (response.status === 204) return undefined as T
  return response.json()
}
export async function* readNDJSON(response: Response): AsyncGenerator<WebEvent> {
  if (!response.ok) throw await httpError(response)
  if (!response.body) throw new ApiError('invalid_stream', '对话流不可用。')
  const reader = response.body.getReader(),
    decoder = new TextDecoder()
  let pending = ''
  function parse(line: string): WebEvent {
    try {
      const event = JSON.parse(line)
      if (!['status', 'progress', 'final', 'error'].includes(event.type)) throw new Error()
      return event as WebEvent
    } catch {
      throw new ApiError('invalid_stream', '对话流格式不正确，请重试。')
    }
  }
  try {
    while (true) {
      const { value, done } = await reader.read()
      pending += done ? decoder.decode() : decoder.decode(value, { stream: true })
      let newline: number
      while ((newline = pending.indexOf('\n')) >= 0) {
        const line = pending.slice(0, newline).trim()
        pending = pending.slice(newline + 1)
        if (line) yield parse(line)
      }
      if (done) {
        if (pending.trim()) yield parse(pending.trim())
        break
      }
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
export const api = {
  confirmAction: (session_id: string, confirmation_id: string) =>
    request<{ ok: boolean }>('/app/confirm', {
      method: 'POST',
      body: JSON.stringify({ session_id, confirmation_id }),
    }),
  archiveJob: (job_id: string) =>
    request<{ status: string; counts?: Record<string, number> }>(
      `/inbox/archive-jobs/${encodeURIComponent(job_id)}`
    ),
  conversations: () => request<Conversation[]>('/conversations'),
  create: () => request<Conversation>('/conversations', { method: 'POST' }),
  conversation: (id: string) => request<Conversation>(`/conversations/${encodeURIComponent(id)}`),
  messages: (id: string) => request<Message[]>(`/conversations/${encodeURIComponent(id)}/messages`),
  patch: (id: string, body: Partial<Pick<Conversation, 'title' | 'model_override'>>) =>
    request<Conversation>(`/conversations/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  stop: (id: string) =>
    request<{ stopping: boolean }>(`/conversations/${encodeURIComponent(id)}/stop`, {
      method: 'POST',
    }),
  settings: () => request<ModelSettings>('/settings/model'),
  catalog: () => request<ModelCatalog>('/models/catalog'),
  saveSettings: (
    body: Pick<ModelSettings, 'provider' | 'model' | 'base_url'> & {
      api_key: string
      profile_id?: string
      label?: string
      make_default?: boolean
      enabled?: boolean
    }
  ) => request<ModelSettings>('/settings/model', { method: 'PUT', body: JSON.stringify(body) }),
  commands: () => request<Command[]>('/commands'),
  skills: () => request<Capability[]>('/capabilities/skills'),
  mcp: () => request<Capability[]>('/capabilities/mcp'),
  async chat(
    id: string,
    text: string,
    signal: AbortSignal,
    onEvent: (event: WebEvent) => void,
    context?: string
  ) {
    const response = await appFetch(`/api/conversations/${encodeURIComponent(id)}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, ...(context ? { context } : {}) }),
      signal,
    })
    let final = false
    for await (const event of readNDJSON(response)) {
      onEvent(event)
      if (event.type === 'final' || event.type === 'error') final = true
    }
    if (!final) throw new ApiError('incomplete_stream', '连接已中断，请查看历史后重试。')
  },
}
