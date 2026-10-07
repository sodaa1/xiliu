import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { Settings, X } from 'lucide-react'
import { api } from '../../lib/api'
import type { Message } from '../../lib/types'
import { Composer } from './Composer'
import { ConversationList } from './ConversationList'
import { MessageList } from './MessageList'

export function AssistantPage() {
  const cache = useQueryClient(),
    [params, setParams] = useSearchParams()
  const [draft, setDraft] = useState(''),
    [error, setError] = useState<string | null>(null)
  const [run, setRun] = useState<{ cid: string; status: string } | null>(null)
  const abort = useRef<AbortController | null>(null)
  const sending = useRef(false),
    mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      abort.current?.abort()
    }
  }, [])
  const list = useQuery({ queryKey: ['conversations'], queryFn: api.conversations })
  const cid = params.get('c') ?? list.data?.[0]?.id
  const conversation = useQuery({
    queryKey: ['conversation', cid],
    queryFn: () => api.conversation(cid!),
    enabled: !!cid,
  })
  const messages = useQuery({
    queryKey: ['messages', cid],
    queryFn: () => api.messages(cid!),
    enabled: !!cid,
  })
  const settings = useQuery({ queryKey: ['model-settings'], queryFn: api.settings })
  const catalog = useQuery({ queryKey: ['model-catalog'], queryFn: api.catalog })
  const commands = useQuery({ queryKey: ['commands'], queryFn: api.commands, retry: false })
  const skills = useQuery({ queryKey: ['skills'], queryFn: api.skills, retry: false })
  const mcp = useQuery({ queryKey: ['mcp'], queryFn: api.mcp, retry: false })
  const create = useMutation({
    mutationFn: api.create,
    onSuccess: async (created) => {
      await cache.invalidateQueries({ queryKey: ['conversations'] })
      setParams({ c: created.id })
      setDraft('')
      setError(null)
    },
    onError: (error) => setError(error.message),
  })
  const remove = useMutation({
    mutationFn: api.remove,
    onSuccess: async (_, id) => {
      cache.removeQueries({ queryKey: ['messages', id] })
      cache.removeQueries({ queryKey: ['conversation', id] })
      if (id === cid) setParams({})
      await cache.invalidateQueries({ queryKey: ['conversations'] })
    },
    onError: (error) => setError(error.message),
  })
  const model = useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) =>
      api.patch(id, { model_override: value || null }),
    onSuccess: async (updated) => {
      cache.setQueryData(['conversation', updated.id], updated)
      await cache.invalidateQueries({ queryKey: ['conversations'] })
    },
    onError: (error) => setError(error.message),
  })
  async function send() {
    if (!draft.trim() || sending.current) return
    sending.current = true
    const controller = new AbortController()
    abort.current = controller
    setRun({ cid: cid ?? '', status: '正在处理…' })
    setError(null)
    let target = cid
    const text = draft.trim()
    try {
      if (!target) {
        const created = await api.create()
        target = created.id
        if (!mounted.current || controller.signal.aborted) return
        setParams({ c: target })
        await cache.invalidateQueries({ queryKey: ['conversations'] })
      }
      if (!mounted.current || controller.signal.aborted) return
      const turnCid = target
      setDraft('')
      setRun({ cid: turnCid, status: '正在处理…' })
      const previous = cache.getQueryData<Message[]>(['messages', turnCid]) ?? []
      cache.setQueryData(
        ['messages', turnCid],
        [
          ...previous,
          {
            id: crypto.randomUUID(),
            conversation_id: turnCid,
            seq: previous.length + 1,
            role: 'user',
            content: text,
            created_at: new Date().toISOString(),
            metadata_json: '{}',
          },
        ]
      )
      await api.chat(turnCid, text, controller.signal, (event) => {
        if (!mounted.current || controller.signal.aborted) return
        if (event.type === 'error') setError(event.message ?? '本次对话失败，请重试。')
        else if (event.type === 'final') {
          cache.setQueryData<Message[]>(['messages', turnCid], (items = []) => [
            ...items,
            {
              id: event.message_id!,
              conversation_id: turnCid,
              seq: items.length + 1,
              role: event.role ?? 'assistant',
              content: event.text ?? '',
              created_at: new Date().toISOString(),
              metadata_json: '{}',
            },
          ])
        } else setRun({ cid: turnCid, status: event.message ?? '正在处理…' })
      })
    } catch (failure) {
      if (mounted.current && !controller.signal.aborted)
        setError(failure instanceof Error ? failure.message : '连接失败，请重试。')
    } finally {
      if (mounted.current) setRun(null)
      abort.current = null
      if (target) {
        await cache.invalidateQueries({ queryKey: ['messages', target] })
        await cache.invalidateQueries({ queryKey: ['conversation', target] })
      }
      await cache.invalidateQueries({ queryKey: ['conversations'] })
      sending.current = false
    }
  }
  const failure =
    error ??
    list.error?.message ??
    conversation.error?.message ??
    messages.error?.message ??
    settings.error?.message
  const models = settings.data ? (catalog.data?.[settings.data.provider]?.models ?? []) : []
  return (
    <div className="assistant-layout">
      <ConversationList
        items={list.data ?? []}
        selected={cid}
        creating={create.isPending}
        busy={!!run}
        onCreate={() => create.mutate()}
        onSelect={(id) => {
          setParams({ c: id })
          setDraft('')
          setError(null)
        }}
        onDelete={(id) => remove.mutate(id)}
      />
      <section className="chat-panel">
        <header className="chat-header">
          <div>
            <h1>Assistant</h1>
            <p>把想法交给息流，一起往前走。</p>
          </div>
          <div className="header-actions">
            <select
              aria-label="当前对话模型"
              value={conversation.data?.model_override ?? ''}
              disabled={!cid || model.isPending || !!run}
              onChange={(event) => model.mutate({ id: cid!, value: event.target.value })}
            >
              <option value="">{settings.data?.model ?? '选择模型'} · 默认</option>
              {models.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
            <Link to="/settings" className="icon-button" aria-label="打开模型设置">
              <Settings size={20} />
            </Link>
          </div>
        </header>
        {failure && (
          <div className="error-banner" role="alert">
            <span>{failure}</span>
            <button
              className="icon-button"
              aria-label="关闭提示"
              onClick={() => {
                setError(null)
                void cache.invalidateQueries()
              }}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {settings.data && !settings.data.api_key_set && (
          <div className="setup-banner">
            开始前，先连接你使用的模型。<Link to="/settings">打开 Settings</Link>
          </div>
        )}
        <MessageList
          messages={messages.data ?? []}
          status={run && run.cid === cid ? run.status : undefined}
          loading={!!cid && messages.isLoading}
          onPrompt={setDraft}
        />
        <Composer
          text={draft}
          onText={setDraft}
          onSend={() => void send()}
          disabled={!!run || create.isPending}
          commands={commands.data}
          skills={skills.data}
          mcp={mcp.data}
        />
      </section>
    </div>
  )
}
