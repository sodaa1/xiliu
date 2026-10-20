import { useState } from 'react'
import {
  Bell,
  CalendarDays,
  Check,
  ChevronDown,
  Clock3,
  Flag,
  Link2,
  Sun,
  Tag,
  Target,
  X,
} from 'lucide-react'
import type { Task, TaskInput } from '../../../lib/workspace-api'
import { publicAsset } from '../../../lib/deployment'
import {
  addDays,
  categories,
  dateKey,
  inputDate,
  parsePlanDate,
  rank,
  scopeLabels,
  startOfWeek,
  statusLabels,
  taskDate,
  taskStatus,
  type PlanScope,
  type PlanStatus,
} from '../plan-utils'

export interface PlanDraft extends TaskInput {
  title: string
  scope: PlanScope
  parent_id: string | null
  due_at: string | null
}
const priorityOptions = [
  { value: 'normal', label: '普通' },
  { value: 'important', label: '重要' },
  { value: 'urgent', label: '紧急' },
  { value: 'low', label: '低优先' },
] as const

export function TaskForm({
  task,
  tasks,
  initialScope,
  initialTitle = '',
  initialParent = '',
  initialDate = new Date(),
  busy,
  error,
  onSubmit,
  onCancel,
}: {
  task?: Task
  tasks: Task[]
  initialScope: PlanScope
  initialTitle?: string
  initialParent?: string
  initialDate?: Date
  busy: boolean
  error: Error | null
  onSubmit: (draft: PlanDraft) => void
  onCancel: () => void
}) {
  const initial = task ? taskDate(task) : initialDate
  const [title, setTitle] = useState(task?.title ?? initialTitle)
  const [scope, setScope] = useState<PlanScope>(task?.scope ?? initialScope)
  const [parent, setParent] = useState(task ? (task.parent_id ?? '') : initialParent)
  const [description, setDescription] = useState(task?.description ?? '')
  const [category, setCategory] = useState(task?.category ?? '')
  const [priority, setPriority] = useState<NonNullable<Task['priority']>>(
    task?.priority ?? 'normal'
  )
  const [status, setStatus] = useState<PlanStatus>(task ? taskStatus(task) : 'not_started')
  const [tags, setTags] = useState(task?.tags ?? [])
  const [tagText, setTagText] = useState('')
  const [reminder, setReminder] = useState(
    task?.reminder_minutes == null ? '' : String(task.reminder_minutes)
  )
  const [day, setDay] = useState(initial ? dateKey(initial) : '')
  const [time, setTime] = useState(initial && task ? inputDate(initial).slice(11) : '09:00')
  const [endTime, setEndTime] = useState(
    task?.starts_at && task.due_at && task.starts_at !== task.due_at
      ? inputDate(parsePlanDate(task.due_at)).slice(11)
      : ''
  )
  const [endDay, setEndDay] = useState(() => {
    const end = parsePlanDate(task?.due_at)
    return end && initial && dateKey(end) !== dateKey(initial) ? dateKey(end) : ''
  })
  const initialStart = initialScope === 'week' ? startOfWeek(initialDate) : initialDate
  const initialEnd = addDays(initialStart, initialScope === 'week' ? 6 : 30)
  const [starts, setStarts] = useState(task ? inputDate(initial) : `${dateKey(initialStart)}T09:00`)
  const [ends, setEnds] = useState(
    task ? inputDate(parsePlanDate(task.due_at)) : `${dateKey(initialEnd)}T18:00`
  )
  const [completedAt, setCompletedAt] = useState(inputDate(parsePlanDate(task?.completed_at)))
  const [localError, setLocalError] = useState('')
  const parents = tasks.filter(
    (item) =>
      item.id !== task?.id &&
      rank[item.scope ?? 'day'] < rank[scope] &&
      (!item.completed || item.id === task?.parent_id)
  )
  const validParent = parents.some((item) => item.id === parent) ? parent : ''
  const addTag = () => {
    const value = tagText.trim()
    if (value && tags.length < 10 && !tags.includes(value)) setTags([...tags, value.slice(0, 32)])
    setTagText('')
  }
  return (
    <form
      className="plan-rich-form"
      onSubmit={(event) => {
        event.preventDefault()
        if (!title.trim() || busy) return
        const from =
          scope === 'day'
            ? day
              ? new Date(`${day}T${time || '00:00'}`).toISOString()
              : null
            : starts
              ? new Date(starts).toISOString()
              : null
        const to =
          scope === 'day'
            ? day
              ? new Date(`${endDay || day}T${endTime || time || '00:00'}`).toISOString()
              : null
            : ends
              ? new Date(ends).toISOString()
              : null
        if (from && to && Date.parse(to) < Date.parse(from)) {
          setLocalError('截止时间不能早于开始时间。')
          return
        }
        if (reminder && !from && !to) {
          setLocalError('请先设置任务时间，再添加提醒。')
          return
        }
        setLocalError('')
        const pendingTag = tagText.trim().slice(0, 32)
        onSubmit({
          title: title.trim(),
          scope,
          parent_id: validParent || null,
          starts_at: from,
          due_at: to,
          description: description.trim(),
          category: category.trim(),
          priority,
          tags: [...new Set([...tags, ...(pendingTag ? [pendingTag] : [])])].slice(0, 10),
          reminder_minutes: reminder === '' ? null : Number(reminder),
          status,
          completed: status === 'completed',
          completed_at:
            status === 'completed' && completedAt ? new Date(completedAt).toISOString() : null,
          ...(task?.demo_revision ? { demo_revision: task.demo_revision } : {}),
        })
      }}
    >
      <div className="plan-rich-columns">
        <div className="plan-form-main">
          <label className="plan-rich-field">
            任务标题
            <input
              name="title"
              required
              maxLength={500}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="写下一件想完成的事…"
            />
          </label>
          <fieldset className="plan-type-field">
            <legend>任务类型</legend>
            <div className="plan-type-options">
              {(['day', 'week', 'goal'] as const).map((value, i) => {
                const Icon = [Sun, CalendarDays, Target][i]
                return (
                  <label
                    className={`plan-type-option ${scope === value ? 'selected' : ''}`}
                    key={value}
                  >
                    <input
                      type="radio"
                      name="task-scope"
                      value={value}
                      checked={scope === value}
                      onChange={() => {
                        setScope(value)
                        setParent('')
                        if (!task && value !== 'day') {
                          const from = value === 'week' ? startOfWeek(initialDate) : initialDate
                          setStarts(`${dateKey(from)}T09:00`)
                          setEnds(`${dateKey(addDays(from, value === 'week' ? 6 : 30))}T18:00`)
                        }
                      }}
                    />
                    <Icon size={25} strokeWidth={1.7} />
                    <span>
                      <strong>{scopeLabels[value]}</strong>
                      <small>{['今天或某一天完成', '在一个星期内完成', '更长周期的目标'][i]}</small>
                    </span>
                    {scope === value && <Check className="plan-type-check" size={14} />}
                  </label>
                )
              })}
            </div>
          </fieldset>
          <label className="plan-rich-field">
            任务描述（可选）
            <span className="plan-description-box">
              <textarea
                aria-label="任务描述（可选）"
                maxLength={500}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="补充一些细节，让这件事更清晰…"
              />
              <small>{description.length}/500</small>
            </span>
          </label>
          <fieldset className="plan-date-fields">
            <legend>任务时间（可选）</legend>
            {scope === 'day' ? (
              <div className="plan-day-date-row">
                <label className="plan-date-control">
                  <CalendarDays size={17} />
                  <input
                    aria-label="任务日期"
                    type="date"
                    value={day}
                    onChange={(event) => setDay(event.target.value)}
                  />
                  <button type="button" aria-label="清除任务日期" onClick={() => setDay('')}>
                    <X size={14} />
                  </button>
                </label>
                <label className="plan-date-control">
                  <Clock3 size={17} />
                  <input
                    aria-label="开始时间"
                    type="time"
                    value={time}
                    onChange={(event) => setTime(event.target.value)}
                  />
                  <button type="button" aria-label="清除开始时间" onClick={() => setTime('')}>
                    <X size={14} />
                  </button>
                </label>
              </div>
            ) : (
              <div className="plan-range-row">
                <label>
                  开始日期
                  <input
                    type="datetime-local"
                    value={starts}
                    onChange={(event) => setStarts(event.target.value)}
                  />
                </label>
                <span>至</span>
                <label>
                  截止日期
                  <input
                    type="datetime-local"
                    value={ends}
                    onChange={(event) => setEnds(event.target.value)}
                  />
                </label>
              </div>
            )}
          </fieldset>
          {scope !== 'goal' && (
            <label className="plan-rich-field">
              <span>
                <Link2 size={16} />
                关联上级计划
              </span>
              <select value={validParent} onChange={(event) => setParent(event.target.value)}>
                <option value="">独立计划（不关联）</option>
                {parents.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title}
                  </option>
                ))}
              </select>
            </label>
          )}
          {status === 'completed' && (
            <label className="plan-rich-field">
              实际完成时间
              <input
                type="datetime-local"
                value={completedAt}
                onChange={(event) => setCompletedAt(event.target.value)}
              />
              <small>旧任务无完成记录时可留空，不补造历史时间。</small>
            </label>
          )}
        </div>
        <aside className="plan-form-aside">
          <fieldset className="plan-priority-field">
            <legend>
              <Flag size={16} />
              优先级
            </legend>
            <div className="plan-priority-options">
              {priorityOptions.map((item) => (
                <label
                  key={item.value}
                  className={`plan-priority-option priority-${item.value} ${priority === item.value ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name="task-priority"
                    checked={priority === item.value}
                    onChange={() => setPriority(item.value)}
                  />
                  <Flag size={19} fill="currentColor" strokeWidth={1.4} />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset className="plan-state-field">
            <legend>任务状态</legend>
            <div className="plan-state-options">
              {(['not_started', 'in_progress', 'completed'] as const).map((value) => (
                <label
                  key={value}
                  className={`plan-state-option state-${value} ${status === value ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name="task-status"
                    checked={status === value}
                    onChange={() => {
                      setStatus(value)
                      if (value === 'completed' && !completedAt && !task?.completed)
                        setCompletedAt(inputDate(new Date()))
                    }}
                  />
                  <i aria-hidden="true" />
                  {statusLabels[value]}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset className="plan-category-field">
            <legend>
              <Tag size={16} />
              任务类别
            </legend>
            <div className="plan-category-options">
              {[
                ...categories,
                ...(category && !categories.includes(category) ? [category] : []),
              ].map((value, i) => (
                <label
                  key={value}
                  className={`plan-category-option category-${i % 5} ${category === value ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name="task-category"
                    checked={category === value}
                    onChange={() => setCategory(value)}
                  />
                  {value}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="plan-rich-field">
            任务标签（可选）
            <input
              aria-label="任务标签（可选）"
              maxLength={32}
              value={tagText}
              onChange={(event) => setTagText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  addTag()
                }
              }}
              placeholder="添加标签，按回车确认…"
            />
          </label>
          {tags.length > 0 && (
            <div className="plan-tag-values">
              {tags.map((tag) => (
                <span key={tag}>
                  {tag}
                  <button
                    type="button"
                    aria-label={`移除标签 ${tag}`}
                    onClick={() => setTags(tags.filter((value) => value !== tag))}
                  >
                    <X size={11} />
                  </button>
                </span>
              ))}
            </div>
          )}
          <label className="plan-rich-field">
            <span>
              <Bell size={16} />
              提醒（可选）
            </span>
            <select value={reminder} onChange={(event) => setReminder(event.target.value)}>
              <option value="">不提醒</option>
              <option value="0">到时提醒</option>
              <option value="5">提前 5 分钟</option>
              <option value="15">提前 15 分钟</option>
              <option value="30">提前 30 分钟</option>
              <option value="60">提前 1 小时</option>
              <option value="1440">提前 1 天</option>
            </select>
            <small>打开个人计划页面时提供页内提醒。</small>
          </label>
          <div className="plan-form-illustration">
            <img src={publicAsset('plans/task-calendar-illustration.webp')} alt="" />
            <p>
              让每一个小任务，
              <br />
              都靠近更好的自己。
            </p>
          </div>
        </aside>
      </div>
      <footer className="plan-rich-footer">
        <details className="plan-more-options">
          <summary>
            更多选项
            <ChevronDown size={14} />
          </summary>
          <div>
            {scope === 'day' && (
              <label>
                结束日期（可选）
                <input
                  type="date"
                  value={endDay}
                  onChange={(event) => setEndDay(event.target.value)}
                />
              </label>
            )}
            {scope === 'day' && (
              <label>
                结束时间（可选）
                <input
                  type="time"
                  value={endTime}
                  onChange={(event) => setEndTime(event.target.value)}
                />
              </label>
            )}
            <label>
              自定义类别
              <input
                maxLength={32}
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                placeholder="可留空"
              />
            </label>
          </div>
        </details>
        <div>
          {(localError || error) && (
            <p role="alert" className="plan-error">
              {localError || error?.message}
            </p>
          )}
          <button type="button" className="plan-secondary" onClick={onCancel} disabled={busy}>
            取消
          </button>
          <button className="plan-primary" disabled={busy || !title.trim()}>
            {busy ? '正在保存…' : task ? '保存修改' : '创建任务'}
          </button>
        </div>
      </footer>
    </form>
  )
}
