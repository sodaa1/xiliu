import { useRef, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { Task } from '../../../lib/workspace-api'
import {
  addDays,
  calendarDays,
  dateKey,
  dateLabel,
  moveMonth,
  startOfWeek,
  tasksOnDate,
  weekdays,
} from '../plan-utils'
import { PlanEmpty, PlanTaskItem, type TaskActions } from './PlanTaskItem'

export function PlanCalendar({
  tasks,
  allTasks,
  selected,
  today,
  onSelect,
  actions,
  loading,
}: {
  tasks: Task[]
  allTasks: Task[]
  selected: Date
  today: Date
  onSelect: (date: Date) => void
  actions: TaskActions
  loading: boolean
}) {
  const [mode, setMode] = useState<'day' | 'week' | 'month'>('month')
  const grid = useRef<HTMLDivElement>(null)
  const days =
    mode === 'month'
      ? calendarDays(selected)
      : mode === 'week'
        ? Array.from({ length: 7 }, (_, i) => addDays(startOfWeek(selected), i))
        : [selected]
  const selectedTasks = tasksOnDate(tasks, selected)
  const navigate = (direction: number) =>
    onSelect(
      mode === 'month'
        ? moveMonth(selected, direction)
        : addDays(selected, direction * (mode === 'week' ? 7 : 1))
    )
  return (
    <section className="plan-card plan-calendar-card" aria-label="日历与当日计划">
      <header className="plan-calendar-toolbar">
        <h2>
          {selected.getFullYear()} 年 {selected.getMonth() + 1} 月
        </h2>
        <div className="plan-calendar-arrows">
          <button
            aria-label={mode === 'month' ? '上个月' : mode === 'week' ? '上一周' : '前一天'}
            onClick={() => navigate(-1)}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            aria-label={mode === 'month' ? '下个月' : mode === 'week' ? '下一周' : '后一天'}
            onClick={() => navigate(1)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
        <button
          className="plan-today-button"
          onClick={() => onSelect(new Date(today.getFullYear(), today.getMonth(), today.getDate()))}
        >
          今天
        </button>
        <div className="plan-calendar-modes" aria-label="日历视图">
          {(['day', 'week', 'month'] as const).map((value, i) => (
            <button
              key={value}
              aria-label={`${['日', '周', '月'][i]}视图`}
              aria-pressed={mode === value}
              onClick={() => setMode(value)}
            >
              {['日', '周', '月'][i]}
            </button>
          ))}
        </div>
      </header>
      <div className={`plan-calendar-view is-${mode}`}>
        {mode !== 'day' && (
          <div className="plan-weekdays" aria-hidden="true">
            {weekdays.map((day) => (
              <span key={day}>{day}</span>
            ))}
          </div>
        )}
        <div
          className="plan-date-grid"
          aria-label={mode === 'month' ? '月历日期' : mode === 'week' ? '周历日期' : '单日视图'}
          ref={grid}
        >
          {days.map((date) => {
            const selectedDay = dateKey(date) === dateKey(selected),
              isToday = dateKey(date) === dateKey(today)
            const dayTasks = tasksOnDate(allTasks, date)
            const active = dayTasks.some((task) => !task.completed),
              done = dayTasks.some((task) => task.completed)
            return (
              <button
                key={dateKey(date)}
                className={`plan-date ${selectedDay ? 'selected' : ''} ${isToday ? 'is-today' : ''} ${date.getMonth() !== selected.getMonth() ? 'outside-month' : ''}`}
                aria-label={dateLabel(date)}
                aria-pressed={selectedDay}
                aria-current={isToday ? 'date' : undefined}
                tabIndex={selectedDay ? 0 : -1}
                onClick={() => onSelect(date)}
                onKeyDown={(event) => {
                  const offset = (
                    { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 } as Record<
                      string,
                      number
                    >
                  )[event.key]
                  let next: Date | undefined
                  if (offset) next = addDays(date, offset)
                  if (event.key === 'Home') next = startOfWeek(date)
                  if (event.key === 'End') next = addDays(startOfWeek(date), 6)
                  if (event.key === 'PageUp' || event.key === 'PageDown')
                    next = moveMonth(date, event.key === 'PageUp' ? -1 : 1)
                  if (next) {
                    event.preventDefault()
                    onSelect(next)
                    const label = dateLabel(next)
                    requestAnimationFrame(() =>
                      grid.current
                        ?.querySelector<HTMLButtonElement>(`[aria-label="${label}"]`)
                        ?.focus()
                    )
                  }
                }}
              >
                <span className="plan-date-number">{date.getDate()}</span>
                {mode === 'day' && (
                  <span className="plan-single-weekday">
                    星期{weekdays[(date.getDay() + 6) % 7]}
                  </span>
                )}
                <span className="plan-date-dots" aria-hidden="true">
                  {active && <i />}
                  {done && <i className="done" />}
                </span>
                {dayTasks.length > 0 && <span className="sr-only">{dayTasks.length} 项任务</span>}
              </button>
            )
          })}
        </div>
        {mode === 'week' && (
          <p className="plan-calendar-note">
            {dateLabel(days[0])} — {days[6].getMonth() + 1}月{days[6].getDate()}日
          </p>
        )}
      </div>
      <section className="plan-date-agenda" aria-label="所选日期计划">
        <header>
          <h3>
            {selected.getMonth() + 1} 月 {selected.getDate()} 日 · 星期
            {weekdays[(selected.getDay() + 6) % 7]}
          </h3>
          <span>{selectedTasks.length} 项</span>
        </header>
        {loading ? (
          <p className="plan-panel-note">正在读取计划…</p>
        ) : selectedTasks.length ? (
          <ul className="plan-task-rows">
            {selectedTasks.map((task) => (
              <PlanTaskItem
                key={task.id}
                task={task}
                parent={allTasks.find((p) => p.id === task.parent_id)}
                compact
                {...actions}
              />
            ))}
          </ul>
        ) : (
          <PlanEmpty>这一天还没有安排，留一点空间给自己。</PlanEmpty>
        )}
      </section>
    </section>
  )
}
