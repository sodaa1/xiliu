import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock3, History, Plus, Trash2, X } from 'lucide-react'
import { workspaceApi, type Automation } from '../../lib/workspace-api'

function RunHistory({ id }: { id: string }) {
  const runs = useQuery({ queryKey: ['automation-runs', id], queryFn: () => workspaceApi.runs(id) })
  return (
    <div className="automation-runs">
      {runs.isLoading ? (
        <p>正在加载记录…</p>
      ) : runs.error ? (
        <p role="alert">{runs.error.message}</p>
      ) : runs.data?.length ? (
        runs.data.map((run) => (
          <article key={run.run_id}>
            <div>
              <strong>
                {['success', 'completed', 'succeeded', 'done'].includes(run.status)
                  ? '已完成'
                  : ['failed', 'error'].includes(run.status)
                    ? '未完成'
                    : ['running', 'pending'].includes(run.status)
                      ? '进行中'
                      : run.status}
              </strong>
              <time dateTime={run.started_at}>
                {new Date(run.started_at).toLocaleString('zh-CN')}
              </time>
            </div>
            {run.result_preview && <p>{run.result_preview}</p>}
            {run.error && <p className="workspace-error">{run.error}</p>}
          </article>
        ))
      ) : (
        <p>还没有运行记录。下次运行后会显示在这里。</p>
      )}
    </div>
  )
}
export function AutomationsPanel() {
  const cache = useQueryClient()
  const [name, setName] = useState(''),
    [prompt, setPrompt] = useState(''),
    [time, setTime] = useState('09:00'),
    [history, setHistory] = useState<string | null>(null),
    [adding, setAdding] = useState(false)
  const automations = useQuery({ queryKey: ['automations'], queryFn: workspaceApi.automations })
  const invalidate = () => {
    void cache.invalidateQueries({ queryKey: ['automations'] })
    void cache.invalidateQueries({ queryKey: ['data-settings'] })
  }
  const create = useMutation({
    mutationFn: () => {
      const [hour, minute] = time.split(':').map(Number)
      return workspaceApi.createAutomation({
        name: name.trim(),
        prompt: prompt.trim(),
        hour,
        minute,
        timezone: 'Asia/Shanghai',
      })
    },
    onSuccess: () => {
      setName('')
      setPrompt('')
      setAdding(false)
      invalidate()
    },
  })
  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      workspaceApi.toggleAutomation(id, enabled),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: workspaceApi.deleteAutomation, onSuccess: invalidate })
  const error = create.error ?? toggle.error ?? remove.error
  return (
    <section className="automations-panel" aria-labelledby="automations-title">
      <header className="drawer-header">
        <div>
          <span className="eyebrow">让息流按时帮你</span>
          <h2 id="automations-title">自动化</h2>
        </div>
      </header>
      <p className="section-description">每天一个固定时间，让信息与想法持续汇聚。</p>
      <button
        className="secondary-button automation-add"
        onClick={() => setAdding(!adding)}
        aria-expanded={adding}
      >
        <Plus size={17} />
        创建每日任务
      </button>
      {adding && (
        <form
          className="automation-form"
          onSubmit={(event) => {
            event.preventDefault()
            create.mutate()
          }}
        >
          <label>
            任务名称
            <input
              required
              maxLength={120}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：我的每日简报"
            />
          </label>
          <label>
            让息流做什么
            <textarea
              required
              rows={4}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="写下希望定时完成的事…"
            />
          </label>
          <label>
            每天运行时间
            <input
              type="time"
              required
              value={time}
              onChange={(event) => setTime(event.target.value)}
            />
          </label>
          <small>北京时间 · Asia/Shanghai</small>
          <button
            className="primary-button"
            disabled={create.isPending || !name.trim() || !prompt.trim()}
          >
            {create.isPending ? '创建中…' : '创建任务'}
          </button>
        </form>
      )}
      {error && (
        <p role="alert" className="workspace-error">
          {error.message}
        </p>
      )}
      {automations.isLoading ? (
        <p className="workspace-empty">正在加载自动任务…</p>
      ) : automations.error ? (
        <div className="workspace-empty">
          <p role="alert">{automations.error.message}</p>
          <button className="secondary-button" onClick={() => void automations.refetch()}>
            重新加载
          </button>
        </div>
      ) : !automations.data?.length ? (
        <div className="workspace-empty">
          <Clock3 size={32} />
          <h2>让一件小事自动发生</h2>
          <p>创建每日任务，按你的节奏获取简报、跟进主题。</p>
        </div>
      ) : (
        <div className="automation-list">
          {automations.data.map((item) => (
            <article className="automation-card" key={item.id}>
              <div className="section-heading">
                <h2>{item.name}</h2>
                <button
                  role="switch"
                  aria-label={`${item.name} 启用`}
                  aria-checked={item.enabled}
                  disabled={toggle.isPending}
                  className={`automation-switch ${item.enabled ? 'enabled' : ''}`}
                  onClick={() => toggle.mutate({ id: item.id, enabled: !item.enabled })}
                >
                  <span />
                </button>
              </div>
              <p>{item.prompt}</p>
              <div className="automation-schedule">
                <Clock3 size={14} />
                <span>
                  {formatSchedule(item)} ·{' '}
                  {item.timezone === 'Asia/Shanghai' ? '北京时间' : item.timezone}
                </span>
                <span>{item.enabled ? '已启用' : '已暂停'}</span>
              </div>
              <div className="row-actions">
                <button
                  aria-expanded={history === item.id}
                  onClick={() => setHistory(history === item.id ? null : item.id)}
                >
                  <History size={14} />
                  运行记录
                </button>
                <button
                  className="delete-action"
                  disabled={remove.isPending}
                  aria-label={`删除自动任务 ${item.name}`}
                  onClick={() => remove.mutate(item.id)}
                >
                  <Trash2 size={14} />
                  删除
                </button>
              </div>
              {history === item.id && <RunHistory id={item.id} />}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
function formatSchedule({ trigger_type, schedule }: Automation) {
  if (trigger_type === 'cron')
    return `每天 ${String(schedule.hour).padStart(2, '0')}:${String(schedule.minute).padStart(2, '0')}`
  if (trigger_type === 'interval') {
    const seconds = Number(schedule.seconds)
    return seconds % 3600 === 0
      ? `每 ${seconds / 3600} 小时`
      : seconds % 60 === 0
        ? `每 ${seconds / 60} 分钟`
        : `每 ${seconds} 秒`
  }
  return new Date(String(schedule.at)).toLocaleString('zh-CN')
}

export function AutomationsDrawer({ onClose }: { onClose: () => void }) {
  const panel = useRef<HTMLElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    panel.current?.focus()
    function keyboard(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
      if (event.key === 'Tab') {
        const focusables = [
          ...(panel.current?.querySelectorAll<HTMLElement>(
            'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), a[href]'
          ) ?? []),
        ]
        const first = focusables[0],
          last = focusables[focusables.length - 1]
        if (
          event.shiftKey &&
          (document.activeElement === first || document.activeElement === panel.current)
        ) {
          event.preventDefault()
          last?.focus()
        } else if (
          !event.shiftKey &&
          (document.activeElement === last || document.activeElement === panel.current)
        ) {
          event.preventDefault()
          first?.focus()
        }
      }
    }
    document.addEventListener('keydown', keyboard)
    return () => {
      document.removeEventListener('keydown', keyboard)
      previous?.focus()
    }
  }, [onClose])
  return (
    <div
      className="drawer-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section
        className="automations-drawer"
        ref={panel}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="automations-title"
      >
        <button className="icon-button drawer-close" aria-label="关闭自动任务" onClick={onClose}>
          <X size={21} />
        </button>
        <AutomationsPanel />
      </section>
    </div>
  )
}
