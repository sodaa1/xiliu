import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { X, FileText } from 'lucide-react'
import { api } from '../../lib/api'
import { useChat } from './chat-context'
import { Composer } from './Composer'
import { ConversationList } from './ConversationList'
import { MessageList } from './MessageList'
import type { AssistantReference } from '../content/useAskAI'
import { Modal } from '../../components/Modal'
import { ModelSettingsPanel } from '../settings/SettingsPage'
import { ModelPicker } from './ModelPicker'

export function AssistantPage() {
  const cache = useQueryClient(),
    [params, setParams] = useSearchParams()
  const location = useLocation(),
    navigate = useNavigate()
  const incoming = location.state as { draft?: string; reference?: AssistantReference } | null
  const [draft, setDraft] = useState(incoming?.draft ?? ''),
    [error, setError] = useState<string | null>(null)
  const [reference, setReference] = useState<AssistantReference | undefined>(incoming?.reference)
  const [configOpen, setConfigOpen] = useState(false)
  const closeConfig = useCallback(() => setConfigOpen(false), [])
  useEffect(() => {
    if (location.state)
      navigate(location.pathname + location.search, { replace: true, state: null })
  }, [location.state, location.pathname, location.search, navigate])
  const { runs, errors, selected, select, dismiss, send: sendTurn, stop } = useChat()
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const list = useQuery({ queryKey: ['conversations'], queryFn: api.conversations })
  const cid = params.get('c') ?? selected ?? list.data?.[0]?.id
  const run = runs[cid ?? '']
  useEffect(() => {
    if (cid) select(cid)
  }, [cid, select])
  const conversation = useQuery({
    queryKey: ['conversation', cid],
    queryFn: () => api.conversation(cid!),
    enabled: !!cid && run?.cid !== cid,
  })
  const messages = useQuery({
    queryKey: ['messages', cid],
    queryFn: () => api.messages(cid!),
    enabled: !!cid && run?.cid !== cid,
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
      select(created.id)
      setParams({ c: created.id })
      setDraft('')
      setReference(undefined)
      setError(null)
    },
    onError: (error) => setError(error.message),
  })
  const remove = useMutation({
    mutationFn: api.remove,
    onSuccess: async (_, id) => {
      cache.removeQueries({ queryKey: ['messages', id] })
      cache.removeQueries({ queryKey: ['conversation', id] })
      if (id === cid) {
        select(null)
        setParams({})
      }
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
    if (!draft.trim() || run) return
    setError(null)
    const text = draft.trim()
    const context = reference ? `标题：${reference.title}\n\n${reference.content}` : undefined
    setDraft('')
    setReference(undefined)
    await sendTurn(
      cid,
      text,
      (id) => {
        if (mounted.current) setParams({ c: id })
      },
      context
    )
  }
  const failure =
    error ??
    errors[cid ?? ''] ??
    list.error?.message ??
    conversation.error?.message ??
    messages.error?.message ??
    settings.error?.message
  const models = settings.data ? (catalog.data?.[settings.data.provider]?.models ?? []) : []
  return (
    <>
      <div className="assistant-layout" inert={configOpen || undefined}>
        <ConversationList
          items={list.data ?? []}
          selected={cid}
          creating={create.isPending}
          busyIds={Object.keys(runs)}
          onCreate={() => create.mutate()}
          onSelect={(id) => {
            setParams({ c: id })
            setDraft('')
            setReference(undefined)
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
          </header>
          {failure && (
            <div className="error-banner" role="alert">
              <span>{failure}</span>
              <button
                className="icon-button"
                aria-label="关闭提示"
                onClick={() => {
                  setError(null)
                  dismiss(cid ?? '')
                  void cache.invalidateQueries()
                }}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {settings.data && !settings.data.api_key_set && (
            <div className="setup-banner">
              开始前，先连接你使用的模型。
              <button type="button" onClick={() => setConfigOpen(true)}>
                连接模型
              </button>
            </div>
          )}
          <MessageList
            messages={messages.data ?? []}
            run={run && (run.cid === cid || !cid) ? run : undefined}
            loading={!!cid && messages.isLoading}
            onPrompt={setDraft}
          />
          {reference && (
            <div className="assistant-reference">
              <FileText size={16} />
              <span>
                本次参考：{reference.title}
                {reference.truncated ? ' · 已截取前段内容' : ''}
              </span>
              <button
                className="icon-button"
                aria-label="移除参考内容"
                onClick={() => setReference(undefined)}
              >
                <X size={15} />
              </button>
            </div>
          )}
          <Composer
            text={draft}
            onText={setDraft}
            onSend={() => void send()}
            disabled={!!run || create.isPending}
            onStop={run ? () => void stop(run.cid) : undefined}
            stopping={run?.stopping}
            commands={commands.data}
            skills={skills.data}
            mcp={mcp.data}
            modelPicker={
              <ModelPicker
                value={conversation.data?.model_override ?? ''}
                defaultModel={settings.data?.model ?? ''}
                models={models}
                provider={settings.data?.provider}
                selectionDisabled={!cid || model.isPending || !!run}
                onChange={(value) => model.mutate({ id: cid!, value })}
                onConfigure={() => setConfigOpen(true)}
              />
            }
          />
        </section>
      </div>
      {configOpen && (
        <Modal
          title="模型配置"
          onClose={closeConfig}
          className="model-config-dialog settings-dialog"
        >
          <div className="settings-page model-settings-panel">
            <ModelSettingsPanel />
          </div>
        </Modal>
      )}
    </>
  )
}
