import { useEffect, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'

export function Modal({
  title,
  onClose,
  children,
  className = '',
  headerContent,
}: {
  title: string
  onClose: () => void
  children: ReactNode
  className?: string
  headerContent?: ReactNode
}) {
  const panel = useRef<HTMLElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    panel.current?.focus()
    function keyboard(event: KeyboardEvent) {
      if (event.defaultPrevented) return
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
      if (event.key === 'Tab') {
        const controls = [
          ...(panel.current?.querySelectorAll<HTMLElement>(
            'button:not(:disabled),input:not(:disabled),textarea:not(:disabled),a[href],[tabindex="0"]'
          ) ?? []),
        ]
        const first = controls[0],
          last = controls[controls.length - 1]
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
      className="task-modal-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section
        className={`task-modal ${className}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={panel}
      >
        <header className="section-heading">
          {headerContent ?? <h2>{title}</h2>}
          <button className="icon-button" aria-label={`关闭${title}`} onClick={onClose}>
            <X size={20} />
          </button>
        </header>
        {children}
      </section>
    </div>
  )
}
