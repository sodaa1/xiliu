import {
  Children,
  cloneElement,
  isValidElement,
  useId,
  useLayoutEffect,
  useEffect,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { MoreHorizontal } from 'lucide-react'

/** Compact row actions; native buttons/links keep their existing handlers. */
export function ActionMenu({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState({ left: 0, top: 0 })
  const trigger = useRef<HTMLButtonElement>(null),
    panel = useRef<HTMLDivElement>(null)
  const anchor = useRef({ top: 0, left: 0 }),
    id = useId()
  const close = (focus = false) => {
    setOpen(false)
    if (focus) trigger.current?.focus({ preventScroll: true })
  }
  useLayoutEffect(() => {
    if (!open) return
    const rect = trigger.current!.getBoundingClientRect(),
      height = panel.current!.offsetHeight
    anchor.current = { top: rect.top, left: rect.left }
    setPosition({
      left: Math.max(12, Math.min(rect.right - 220, innerWidth - 232)),
      top: Math.max(12, Math.min(rect.bottom + 8, innerHeight - height - 12)),
    })
    panel.current
      ?.querySelector<HTMLElement>('[role="menuitem"]:not(:disabled)')
      ?.focus({ preventScroll: true })
  }, [open])
  useEffect(() => {
    if (!open) return
    const outside = (event: PointerEvent) => {
      if (
        !panel.current?.contains(event.target as Node) &&
        !trigger.current?.contains(event.target as Node)
      )
        setOpen(false)
    }
    const scroll = (event: Event) => {
      if (panel.current?.contains(event.target as Node)) return
      const rect = trigger.current?.getBoundingClientRect()
      if (
        !rect ||
        Math.abs(rect.top - anchor.current.top) > 1 ||
        Math.abs(rect.left - anchor.current.left) > 1
      )
        setOpen(false)
    }
    const resize = () => setOpen(false)
    document.addEventListener('pointerdown', outside)
    document.addEventListener('scroll', scroll, true)
    window.addEventListener('resize', resize)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('scroll', scroll, true)
      window.removeEventListener('resize', resize)
    }
  }, [open])
  return (
    <>
      <button
        ref={trigger}
        type="button"
        className="ui-row-more"
        aria-label={label}
        title={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen(!open)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') {
            event.preventDefault()
            setOpen(true)
          }
        }}
      >
        <MoreHorizontal size={19} />
      </button>
      {open &&
        createPortal(
          <div
            ref={panel}
            id={id}
            role="menu"
            aria-label={label}
            className="ui-overflow-menu"
            style={position}
            onClick={(event) => {
              if ((event.target as HTMLElement).closest('button:not(:disabled),a')) close(true)
            }}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                event.preventDefault()
                event.stopPropagation()
                close(true)
              } else if (event.key === 'Tab') close(true)
              else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
                event.preventDefault()
                const nodes = [
                    ...panel.current!.querySelectorAll<HTMLElement>(
                      '[role="menuitem"]:not(:disabled)'
                    ),
                  ],
                  current = nodes.indexOf(document.activeElement as HTMLElement)
                nodes[
                  event.key === 'Home'
                    ? 0
                    : event.key === 'End'
                      ? nodes.length - 1
                      : (current + (event.key === 'ArrowDown' ? 1 : -1) + nodes.length) %
                        nodes.length
                ]?.focus()
              }
            }}
          >
            {Children.map(children, (child) =>
              isValidElement(child)
                ? cloneElement(child as ReactElement<{ role?: string; tabIndex?: number }>, {
                    role: 'menuitem',
                    tabIndex: -1,
                  })
                : child
            )}
          </div>,
          document.body
        )}
    </>
  )
}
