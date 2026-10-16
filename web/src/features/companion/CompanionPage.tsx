import { PetAvatar } from './PetAvatar'
import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Inbox,
  SquarePen,
  MoreHorizontal,
  ArrowUp,
  Plus,
  Settings,
  RefreshCw,
  House,
  LoaderCircle,
} from 'lucide-react'
import { isDesktop } from '../../desktop/bridge'
import {
  acceptSnapshot,
  companionCall,
  companionListen,
  petHeight,
  previewSettings,
  savePreviewSettings,
  idleStatus,
  type CompanionSettings,
  type CompanionSnapshot,
  type QuickRequest,
} from '../../desktop/companion'
import './companion.css'

export function CompanionPage() {
  const navigate = useNavigate()
  const [compose, setCompose] = useState(false)
  const [menu, setMenu] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [pixelRatio, setPixelRatio] = useState(() => window.devicePixelRatio || 1)
  const [position, setPosition] = useState({ right: 24, bottom: 24 })
  const stage = useRef<HTMLDivElement>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [settings, setSettings] = useState<CompanionSettings>(previewSettings)
  const height = petHeight(settings)
  const [snapshot, setSnapshot] = useState<CompanionSnapshot>({ ...idleStatus, revision: 0 })
  const requestId = useRef<string | null>(null)
  const alive = useRef(true)
  const pointer = useRef({ x: 0, y: 0, right: 24, bottom: 24, active: false, moved: false })
  const invoke = async (command: string, args: Record<string, unknown> = {}) => {
    try {
      return await companionCall(command, args)
    } catch (error) {
      setError(String(error))
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
          setCompose(true)
          void companionCall('take_compose').catch(() => {})
        })
        const value = await companionCall<CompanionSnapshot>('snapshot')
        if (!stopped) {
          setSnapshot((old) => acceptSnapshot(old, value))
          setSettings(await companionCall<CompanionSettings>('settings'))
          if (await companionCall<boolean>('take_compose')) {
            setCompose(true)
          }
        }
      })().catch((error) => {
        if (!stopped) {
          setError(String(error))
        }
      })
    return () => {
      stopped = true
      alive.current = false
      stops.forEach((stop) => stop())
      delete document.documentElement.dataset.companion
    }
  }, [])
  useEffect(() => {
    const update = () => setPixelRatio(window.devicePixelRatio || 1)
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])
  const bubble = snapshot.phase !== 'idle'
  useEffect(() => {
    if (isDesktop())
      void companionCall('layout', { expanded: compose, bubble: bubble || !!error, menu }).catch(
        (failure) => setError(String(failure))
      )
  }, [compose, bubble, error, menu, height])
  useEffect(() => {
    if (isDesktop()) return
    const refresh = () => setSettings(previewSettings())
    window.addEventListener('storage', refresh)
    window.addEventListener('companion-preview-settings', refresh)
    return () => {
      window.removeEventListener('storage', refresh)
      window.removeEventListener('companion-preview-settings', refresh)
    }
  }, [])
  useEffect(() => {
    if (isDesktop()) return
    const clamp = () => {
      const rect = stage.current?.getBoundingClientRect()
      if (!rect) return
      setPosition((old) => ({
        right: Math.max(12, Math.min(old.right, window.innerWidth - rect.width - 12)),
        bottom: Math.max(12, Math.min(old.bottom, window.innerHeight - rect.height - 12)),
      }))
    }
    clamp()
    window.addEventListener('resize', clamp)
    return () => window.removeEventListener('resize', clamp)
  }, [height, compose, menu, bubble, error])
  const switchForm = async () => {
    const form = settings.form === 'standing' ? 'chibi' : 'standing'
    if (isDesktop()) {
      try {
        setSettings(await companionCall<CompanionSettings>('set_form', { form }))
        setError('')
      } catch (failure) {
        setError(String(failure))
      }
    } else setSettings(savePreviewSettings({ ...settings, form }))
    setMenu(false)
  }
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
      data-native={isDesktop()}
      style={
        {
          '--pet-height': `${height}px`,
          '--pet-lift-near': `${-Math.round(2 * pixelRatio) / pixelRatio}px`,
          '--pet-lift-far': `${-Math.round(4 * pixelRatio) / pixelRatio}px`,
        } as CSSProperties
      }
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          setCompose(false)
          setMenu(false)
        }
      }}
    >
      <div
        ref={stage}
        className="companion-stage"
        data-dragging={dragging}
        style={!isDesktop() ? { right: position.right, bottom: position.bottom } : undefined}
      >
        {(bubble || error) && (
          <div className="companion-notice">
            {error ? (
              <p role="alert" className="companion-error">
                {error}
              </p>
            ) : (
              <button
                className="companion-bubble"
                aria-live="polite"
                title="查看对话"
                onClick={() =>
                  openMain(
                    snapshot.cid ? `/assistant?c=${encodeURIComponent(snapshot.cid)}` : '/assistant'
                  )
                }
              >
                {snapshot.message}
                {snapshot.count > 1 && <small>{snapshot.count} 个任务进行中</small>}
              </button>
            )}
          </div>
        )}
        <button
          className="companion-character"
          aria-label="打开桌宠快捷操作"
          aria-expanded={compose}
          onPointerDown={(event) => {
            if (event.button !== 0) return
            pointer.current = {
              x: event.clientX,
              y: event.clientY,
              ...position,
              active: true,
              moved: false,
            }
            if (!isDesktop()) event.currentTarget.setPointerCapture(event.pointerId)
          }}
          onPointerMove={(event) => {
            const start = pointer.current
            if (!start.active || event.buttons !== 1) return
            const dx = event.clientX - start.x,
              dy = event.clientY - start.y
            if (!start.moved && Math.hypot(dx, dy) <= 5) return
            if (!start.moved) {
              start.moved = true
              setDragging(true)
              if (isDesktop()) {
                void invoke('drag').finally(() => {
                  pointer.current.active = false
                  setDragging(false)
                })
                return
              }
            }
            if (!isDesktop()) {
              const rect = stage.current?.getBoundingClientRect()
              if (rect)
                setPosition({
                  right: Math.max(
                    12,
                    Math.min(start.right - dx, window.innerWidth - rect.width - 12)
                  ),
                  bottom: Math.max(
                    12,
                    Math.min(start.bottom - dy, window.innerHeight - rect.height - 12)
                  ),
                })
            }
          }}
          onPointerUp={() => {
            pointer.current.active = false
            if (!isDesktop()) setDragging(false)
          }}
          onPointerCancel={() => {
            pointer.current.active = false
            if (!isDesktop()) setDragging(false)
          }}
          onLostPointerCapture={() => {
            if (!isDesktop()) {
              pointer.current.active = false
              setDragging(false)
            }
          }}
          onClick={(event) => {
            if (event.detail === 0 || !pointer.current.moved) {
              setCompose(!compose)
              setMenu(false)
            }
          }}
        >
          <PetAvatar
            key={settings.form ?? 'chibi'}
            form={settings.form ?? 'chibi'}
            phase={snapshot.phase}
            dragging={dragging}
            active={compose}
            onError={setError}
          />
        </button>
        <div className="companion-dock">
          {compose ? (
            <form
              className="companion-compose"
              aria-label="桌宠快速对话"
              onSubmit={(event) => {
                event.preventDefault()
                void send()
              }}
            >
              <button
                type="button"
                className="companion-icon"
                aria-label="更多桌宠操作"
                title="更多"
                aria-expanded={menu}
                onClick={() => setMenu(!menu)}
              >
                <Plus size={20} />
              </button>
              <input
                autoFocus
                aria-label="快速对话内容"
                placeholder="开始新聊天"
                value={draft}
                disabled={pending || !!requestId.current}
                onChange={(event) => setDraft(event.target.value)}
                maxLength={20000}
              />
              <button
                className="companion-send companion-icon"
                aria-label={
                  pending ? '正在发送' : requestId.current ? '检查发送状态' : '发送新对话'
                }
                title="发送"
                disabled={pending || !draft.trim()}
              >
                {pending ? (
                  <LoaderCircle size={18} className="companion-spinner" />
                ) : (
                  <ArrowUp size={20} />
                )}
              </button>
            </form>
          ) : (
            <div className="companion-toolbar" role="toolbar" aria-label="桌宠快捷操作">
              <button
                className="companion-icon"
                aria-label="新对话"
                title="新对话"
                onClick={() => {
                  setCompose(true)
                  setMenu(false)
                }}
              >
                <SquarePen size={19} />
              </button>
              <button
                className="companion-icon"
                aria-label="收进收件箱"
                title="收进收件箱"
                onClick={() => {
                  if (isDesktop()) void invoke('open_capture')
                  else navigate('/desktop/capture')
                }}
              >
                <Inbox size={19} />
              </button>
              <button
                className="companion-icon"
                aria-label="更多桌宠操作"
                title="更多"
                aria-expanded={menu}
                onClick={() => setMenu(!menu)}
              >
                <MoreHorizontal size={20} />
              </button>
            </div>
          )}
          {menu && (
            <div className="companion-more" role="toolbar" aria-label="更多桌宠操作">
              <button
                className="companion-icon"
                aria-label="切换桌宠形态"
                title="切换形态"
                onClick={() => void switchForm()}
              >
                <RefreshCw size={18} />
              </button>
              {compose && (
                <button
                  className="companion-icon"
                  aria-label="收进收件箱"
                  title="收进收件箱"
                  onClick={() => {
                    if (isDesktop()) void invoke('open_capture')
                    else navigate('/desktop/capture')
                  }}
                >
                  <Inbox size={18} />
                </button>
              )}
              <button
                className="companion-icon"
                aria-label="打开息流"
                title="打开息流"
                onClick={() => openMain('/today')}
              >
                <House size={18} />
              </button>
              <button
                className="companion-icon"
                aria-label="桌宠设置"
                title="设置"
                onClick={() => openMain('/settings?section=appearance')}
              >
                <Settings size={18} />
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
