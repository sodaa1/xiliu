import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { Check, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import { statusLabels, taskStatus, type PlanStatus } from '../plan-utils'
import type { TaskActions } from './PlanTaskItem'
import type { Task } from '../../../lib/workspace-api'
import './task-menu.css'

const states: PlanStatus[] = ['not_started', 'in_progress', 'completed']
export function TaskMenu({
  task,
  busy,
  onStatus,
  onEdit,
  onDelete,
}: Pick<TaskActions, 'busy' | 'onStatus' | 'onEdit' | 'onDelete'> & { task: Task }) {
  const [open, setOpen] = useState(false),
    [position, setPosition] = useState({ left: 0, top: 0 })
  const trigger = useRef<HTMLButtonElement>(null),
    panel = useRef<HTMLDivElement>(null),
    id = useId()
  const anchor = useRef({ top: 0, left: 0 })
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
    panel.current?.querySelector<HTMLButtonElement>('button')?.focus({ preventScroll: true })
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
    const dismiss = () => setOpen(false)
    const scroll = (event: Event) => {
      if (panel.current?.contains(event.target as Node)) return
      const rect = trigger.current?.getBoundingClientRect()
      // Ignore an already queued scroll event from bringing the trigger into view.
      if (
        !rect ||
        Math.abs(rect.top - anchor.current.top) > 1 ||
        Math.abs(rect.left - anchor.current.left) > 1
      )
        dismiss()
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('scroll', scroll, true)
    window.addEventListener('resize', dismiss)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('scroll', scroll, true)
      window.removeEventListener('resize', dismiss)
    }
  }, [open])
  function keyboard(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      close(true)
    } else if (event.key === 'Tab') close(true)
    else if (
      ['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)
    ) {
      event.preventDefault()
      const nodes = [
          ...panel.current!.querySelectorAll<HTMLButtonElement>('button:not(:disabled)'),
        ],
        current = nodes.indexOf(document.activeElement as HTMLButtonElement)
      const next =
        event.key === 'Home'
          ? 0
          : event.key === 'End'
            ? nodes.length - 1
            : (current +
                (['ArrowDown', 'ArrowRight'].includes(event.key) ? 1 : -1) +
                nodes.length) %
              nodes.length
      nodes[next]?.focus()
    }
  }
  return (
    <>
      <span
        className={`plan-state-dot state-${taskStatus(task)}`}
        role="img"
        aria-label={`任务状态：${statusLabels[taskStatus(task)]}`}
        title={statusLabels[taskStatus(task)]}
      />
      <button
        ref={trigger}
        type="button"
        className="plan-task-more"
        aria-label={`任务操作：${task.title}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        disabled={busy}
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
            aria-label={`任务操作：${task.title}`}
            className="plan-task-menu"
            style={position}
            onKeyDown={keyboard}
          >
            <div className="task-menu-colors" role="group" aria-label="任务状态">
              {states.map((status) => (
                <button
                  key={status}
                  type="button"
                  role="menuitemradio"
                  aria-checked={taskStatus(task) === status}
                  aria-label={statusLabels[status]}
                  title={statusLabels[status]}
                  tabIndex={-1}
                  className={`task-state-choice state-${status}`}
                  disabled={busy}
                  onClick={() => {
                    close(true)
                    onStatus(task, status)
                  }}
                >
                  {taskStatus(task) === status && <Check size={16} strokeWidth={3} />}
                </button>
              ))}
            </div>
            <p className="task-menu-current">{statusLabels[taskStatus(task)]}</p>
            <div className="task-menu-divider" />
            <button
              type="button"
              role="menuitem"
              tabIndex={-1}
              disabled={busy}
              onClick={() => {
                close(true)
                onEdit(task)
              }}
            >
              <Pencil size={17} />
              编辑任务
            </button>
            <button
              type="button"
              role="menuitem"
              tabIndex={-1}
              disabled={busy}
              className="task-menu-delete"
              onClick={() => {
                close(true)
                onDelete(task)
              }}
            >
              <Trash2 size={17} />
              删除任务
            </button>
          </div>,
          document.body
        )}
    </>
  )
}
