import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { Inbox, MessageSquare, Sparkles, X, House } from 'lucide-react'
import { isDesktop } from '../../desktop/bridge'
import {
  acceptSnapshot,
  companionCall,
  companionListen,
  DEFAULT_PET_HEIGHT,
  idleStatus,
  type CompanionSettings,
  type CompanionSnapshot,
  type QuickRequest,
} from '../../desktop/companion'
import './companion.css'

export function CompanionPage() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [compose, setCompose] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [settings, setSettings] = useState<CompanionSettings>({
    enabled: true,
    visible: true,
    height: DEFAULT_PET_HEIGHT,
    alwaysOnTop: true,
  })
  const [snapshot, setSnapshot] = useState<CompanionSnapshot>({ ...idleStatus, revision: 0 })
  const requestId = useRef<string | null>(null)
  const alive = useRef(true)
  const pointer = useRef({ x: 0, y: 0, dragging: false })
  const invoke = async (command: string, args: Record<string, unknown> = {}) => {
    try {
      return await companionCall(command, args)
    } catch (error) {
      setError(String(error))
      setOpen(true)
    }
  }
  useEffect(() => {
    alive.current = true
    document.documentElement.dataset.companion = 'true'
    const stops: (() => void)[] = []
    let stopped = false
    if (isDesktop())
      void (async () => {
        const listen = async <T,>(name: string, callback: (value: T) => void) => {
          const stop = await companionListen<T>(name, callback)
          if (stopped) stop()
          else stops.push(stop)
        }
        await listen<CompanionSnapshot>('snapshot', (value) =>
          setSnapshot((old) => acceptSnapshot(old, value))
        )
        await listen<CompanionSettings>('settings', setSettings)
        await listen<null>('compose', () => {
          setOpen(true)
          setCompose(true)
          void companionCall('take_compose').catch(() => {})
        })
        const value = await companionCall<CompanionSnapshot>('snapshot')
        if (!stopped) {
          setSnapshot((old) => acceptSnapshot(old, value))
          setSettings(await companionCall<CompanionSettings>('settings'))
          if (await companionCall<boolean>('take_compose')) {
            setOpen(true)
            setCompose(true)
          }
        }
      })().catch((error) => {
        if (!stopped) {
          setError(String(error))
          setOpen(true)
        }
      })
    return () => {
      stopped = true
      alive.current = false
      stops.forEach((stop) => stop())
      delete document.documentElement.dataset.companion
    }
  }, [])
  const bubble = snapshot.phase !== 'idle'
  useEffect(() => {
    if (isDesktop())
      void companionCall('layout', { expanded: open, bubble }).catch((error) =>
        setError(String(error))
      )
  }, [open, bubble, settings.height])
  const openMain = (path: string) => {
    if (isDesktop()) void invoke('open_main', { path })
    else navigate(path)
  }
  const send = async () => {
    if (!draft.trim() || pending) return
    if (!isDesktop()) {
      navigate('/assistant', { state: { draft: draft.trim() } })
      return
    }
    setPending(true)
    setError('')
    const id = requestId.current ?? crypto.randomUUID()
    requestId.current = id
    try {
      let result = await companionCall<QuickRequest>('submit', {
        requestId: id,
        text: draft.trim(),
      })
      for (let count = 0; result.status === 'pending' && count < 60 && alive.current; count++) {
        await new Promise((resolve) => window.setTimeout(resolve, 300))
        result = await companionCall<QuickRequest>('result', { requestId: id })
      }
      if (!alive.current) return
      if (result.status === 'accepted') {
        requestId.current = null
        setDraft('')
        setCompose(false)
        setOpen(false)
      } else if (result.status === 'failed') {
        requestId.current = null
        setError(result.error ?? '发送失败，请重试。')
      } else setError('仍在等待主窗口接收，点击检查发送状态。')
    } catch (error) {
      setError(String(error))
    } finally {
      if (alive.current) setPending(false)
    }
  }
  return (
    <main
      className="companion-surface"
      style={{ '--pet-height': `${settings.height}px` } as CSSProperties}
      onKeyDown={(event) => {
        if (event.key === 'Escape') setOpen(false)
      }}
    >
      {open && (
        <section className="companion-panel" aria-label="桌宠快捷操作">
          <header>
            <strong>
              <Sparkles size={15} />
              息流在这里
            </strong>
            <button aria-label="收起快捷面板" onClick={() => setOpen(false)}>
              <X size={16} />
            </button>
          </header>
          <div className="companion-shortcuts">
            <button onClick={() => setCompose(true)}>
              <MessageSquare size={15} />
              新对话
            </button>
            <button
              onClick={() => {
                if (isDesktop()) void invoke('open_capture')
                else navigate('/desktop/capture')
              }}
            >
              <Inbox size={15} />
              收进 Inbox
            </button>
            <button aria-label="打开息流" onClick={() => openMain('/today')}>
              <House size={15} />
            </button>
          </div>
          {compose && (
            <form
              className="companion-compose"
              onSubmit={(event) => {
                event.preventDefault()
                void send()
              }}
            >
              <textarea
                autoFocus
                aria-label="快速对话内容"
                placeholder="聊聊你正在想的事…"
                value={draft}
                disabled={pending || !!requestId.current}
                onChange={(event) => setDraft(event.target.value)}
                maxLength={20000}
              />
              <button disabled={pending || !draft.trim()}>
                {pending ? '正在发送…' : requestId.current ? '检查发送状态' : '发送新对话'}
              </button>
            </form>
          )}
          {error && (
            <p role="alert" className="companion-error">
              {error}
            </p>
          )}
        </section>
      )}
      {!open && bubble && (
        <button
          className="companion-bubble"
          aria-live="polite"
          onClick={() =>
            openMain(
              snapshot.cid ? `/assistant?c=${encodeURIComponent(snapshot.cid)}` : '/assistant'
            )
          }
        >
          {snapshot.message}
          <small>{snapshot.count > 1 ? `共 ${snapshot.count} 个任务 · ` : ''}点击查看对话</small>
        </button>
      )}
      <button
        className="companion-character"
        aria-label="打开桌宠快捷操作"
        aria-expanded={open}
        onPointerDown={(event) => {
          pointer.current = { x: event.clientX, y: event.clientY, dragging: false }
        }}
        onPointerMove={(event) => {
          if (
            event.buttons === 1 &&
            !pointer.current.dragging &&
            Math.hypot(event.clientX - pointer.current.x, event.clientY - pointer.current.y) > 5
          ) {
            pointer.current.dragging = true
            if (isDesktop()) void invoke('drag')
          }
        }}
        onClick={(event) => {
          if (event.detail === 0 || !pointer.current.dragging) setOpen(!open)
        }}
      >
        <img src="/companion/chibi.png" alt="" draggable={false} width="1254" height="1254" />
      </button>
    </main>
  )
}
