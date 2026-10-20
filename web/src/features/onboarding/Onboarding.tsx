import { useCallback, useEffect, useId, useRef, useSyncExternalStore } from 'react'
import { createPortal } from 'react-dom'
import { useLocation, useNavigate } from 'react-router-dom'
import { X } from 'lucide-react'
import { dismissGuide, finishGuide, getGuideProgress, moveGuide, subscribeGuide } from './progress'
import { tourSteps } from './steps'
import { useSpotlight } from './useSpotlight'
import './onboarding.css'

export function Onboarding() {
  const progress = useSyncExternalStore(subscribeGuide, getGuideProgress)
  const location = useLocation(),
    navigate = useNavigate()
  const running = progress.status === 'new' || progress.status === 'active'
  const step = tourSteps[progress.step]
  const currentLocation = useRef(location),
    returnLocation = useRef(location)
  const navigateRef = useRef(navigate)
  const panel = useRef<HTMLElement>(null)
  const maskId = useId()
  const { box, width: viewportWidth, height: viewportHeight } = useSpotlight(step.target, running)
  useEffect(() => {
    currentLocation.current = location
  }, [location])
  useEffect(() => {
    navigateRef.current = navigate
  }, [navigate])
  const end = useCallback((skipped: boolean) => {
    if (skipped) dismissGuide()
    else finishGuide()
    const origin = returnLocation.current
    navigateRef.current(origin.pathname + origin.search + origin.hash, {
      replace: true,
      state: origin.state,
    })
  }, [])
  useEffect(() => {
    if (!running) return
    returnLocation.current = currentLocation.current
    const previousFocus = document.activeElement as HTMLElement | null
    const root = document.getElementById('root')
    const wasInert = root?.inert ?? false
    if (root) root.inert = true
    document.documentElement.classList.add('onboarding-active')
    document.body.classList.add('onboarding-active')
    const blockScroll = (event: Event) => {
      if (!(event.target instanceof Element) || !event.target.closest('.onboarding-tooltip'))
        event.preventDefault()
    }
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        event.stopPropagation()
        end(true)
      }
      if (['PageDown', 'PageUp', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key))
        event.preventDefault()
      if (event.key !== 'Tab') return
      const controls = [
        ...(panel.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? []),
      ]
      const first = controls[0],
        last = controls.at(-1)
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
    document.addEventListener('keydown', keyboard, true)
    document.addEventListener('wheel', blockScroll, { passive: false })
    document.addEventListener('touchmove', blockScroll, { passive: false })
    return () => {
      if (root) root.inert = wasInert
      document.documentElement.classList.remove('onboarding-active')
      document.body.classList.remove('onboarding-active')
      document.removeEventListener('keydown', keyboard, true)
      document.removeEventListener('wheel', blockScroll)
      document.removeEventListener('touchmove', blockScroll)
      if (previousFocus?.isConnected) previousFocus.focus()
    }
  }, [running, end])
  useEffect(() => {
    if (!running) return
    panel.current?.focus()
    if (step.path)
      navigateRef.current(step.path, {
        replace: true,
        state: step.path.startsWith('/settings')
          ? {
              backgroundLocation: {
                ...returnLocation.current,
                pathname: '/assistant',
                search: '',
                hash: '',
              },
            }
          : null,
      })
  }, [running, step])
  if (!running) return null

  const width = Math.min(360, viewportWidth - 32)
  const height = panel.current?.offsetHeight || 250
  let left = (viewportWidth - width) / 2
  let top = Math.max(16, (viewportHeight - height) / 2)
  if (box) {
    if (box.right + width + 28 <= viewportWidth) {
      left = box.right + 18
      top = box.top
    } else if (box.left - width - 18 >= 16) {
      left = box.left - width - 18
      top = box.top
    } else {
      left = Math.max(16, Math.min(box.left, viewportWidth - width - 16))
      top = box.bottom + height + 26 <= viewportHeight ? box.bottom + 18 : box.top - height - 18
    }
    top = Math.max(16, Math.min(top, viewportHeight - height - 16))
  }
  return createPortal(
    <div className="onboarding-layer">
      <svg className="onboarding-shade" width="100%" height="100%" aria-hidden="true">
        <defs>
          <mask id={maskId}>
            <rect width="100%" height="100%" fill="white" />
            {box && (
              <rect
                x={box.left - 7}
                y={box.top - 7}
                width={box.width + 14}
                height={box.height + 14}
                rx="12"
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          width="100%"
          height="100%"
          fill="rgba(9, 10, 20, .28)"
          mask={'url(#' + maskId + ')'}
        />
      </svg>
      {box && (
        <div
          className="onboarding-spotlight"
          aria-hidden="true"
          style={{
            left: box.left - 7,
            top: box.top - 7,
            width: box.width + 14,
            height: box.height + 14,
          }}
        />
      )}
      <section
        className="onboarding-tooltip"
        role="dialog"
        aria-modal="true"
        aria-label={step.title}
        aria-describedby="onboarding-copy"
        tabIndex={-1}
        ref={panel}
        style={{ left, top, width, maxHeight: viewportHeight - top - 16 }}
      >
        <div className="onboarding-progress">
          <span>
            功能导览 · {progress.step + 1} / {tourSteps.length}
          </span>
          <button className="onboarding-close" aria-label="关闭引导" onClick={() => end(true)}>
            <X size={16} />
          </button>
        </div>
        <div
          className="onboarding-dots"
          role="progressbar"
          aria-label="导览进度"
          aria-valuemin={1}
          aria-valuemax={tourSteps.length}
          aria-valuenow={progress.step + 1}
        >
          {tourSteps.map((entry, index) => (
            <i
              key={entry.title}
              className={
                progress.step === index ? 'is-current' : index < progress.step ? 'is-complete' : ''
              }
            />
          ))}
        </div>
        <h2>{step.title}</h2>
        <p id="onboarding-copy">{step.description}</p>
        <footer className="onboarding-actions">
          <button className="onboarding-skip" onClick={() => end(true)}>
            跳过引导
          </button>
          <div>
            {progress.step > 0 && (
              <button className="secondary-button" onClick={() => moveGuide(-1)}>
                上一步
              </button>
            )}
            {progress.step === tourSteps.length - 1 ? (
              <button className="primary-button" onClick={() => end(false)}>
                开始使用
              </button>
            ) : (
              <button className="primary-button" onClick={() => moveGuide(1)}>
                下一步
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>,
    document.body
  )
}
