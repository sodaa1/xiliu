import { TaskMenu } from './TaskMenu'
import { CalendarCheck2, Check } from 'lucide-react'
import type { Task } from '../../../lib/workspace-api'
import { categories, taskDate, taskStatus, type PlanStatus } from '../plan-utils'

export interface TaskActions {
  onStatus: (task: Task, status: PlanStatus) => void
  onToggle: (task: Task) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
  busy: boolean
}

export function PlanTaskItem({
  task,
  parent,
  compact = false,
  onToggle,
  onStatus,
  onEdit,
  onDelete,
  busy,
}: TaskActions & { task: Task; parent?: Task; compact?: boolean }) {
  const due = taskDate(task)
  return (
    <li
      className={`plan-task-row state-${taskStatus(task)} ${task.completed ? 'is-complete' : ''}`}
      data-plan-task={task.id}
    >
      <label className="plan-check">
        <input
          type="checkbox"
          checked={task.completed}
          disabled={busy}
          aria-label={`${task.completed ? '恢复' : '完成'} ${task.title}`}
          onChange={() => onToggle(task)}
        />
        <span aria-hidden="true">
          <Check size={12} strokeWidth={3} />
        </span>
      </label>
      <div className="plan-task-copy">
        <button
          className="plan-task-title"
          disabled={busy}
          onClick={() => onEdit(task)}
          title={`编辑 ${task.title}`}
        >
          {task.title}
        </button>
        <div className="plan-task-meta">
          {due ? (
            <time dateTime={task.due_at!}>
              {compact || (task.scope ?? 'day') === 'day'
                ? due.toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false,
                  })
                : due.toLocaleString('zh-CN', {
                    month: 'numeric',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false,
                  })}
            </time>
          ) : (
            <span>未设时间</span>
          )}
          {task.starts_at && task.due_at && task.starts_at !== task.due_at && (
            <span>
              —{' '}
              {new Date(task.due_at).toLocaleString(
                'zh-CN',
                task.scope === 'day'
                  ? { hour: '2-digit', minute: '2-digit', hour12: false }
                  : { month: 'numeric', day: 'numeric' }
              )}
            </span>
          )}
        </div>
      </div>
      <span
        className={`plan-status-tag plan-category-badge category-${categories.indexOf(task.category ?? '')}`}
        title={parent ? `上级计划：${parent.title}` : undefined}
      >
        {task.category || '未分类'}
      </span>
      <TaskMenu task={task} busy={busy} onStatus={onStatus} onEdit={onEdit} onDelete={onDelete} />
    </li>
  )
}

export function PlanEmpty({ children }: { children: React.ReactNode }) {
  return (
    <div className="plan-empty">
      <CalendarCheck2 size={26} strokeWidth={1.4} />
      <p>{children}</p>
    </div>
  )
}
