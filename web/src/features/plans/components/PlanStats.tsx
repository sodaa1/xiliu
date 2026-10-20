import { useLayoutEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { Flame, Target } from 'lucide-react'
import type { Task } from '../../../lib/workspace-api'
import {
  completion,
  completionDays,
  completionStreak,
  dateKey,
  plansInWeek,
  tasksOnDate,
  type PlanScope,
} from '../plan-utils'

function Count({ value, reduced }: { value: number; reduced: boolean }) {
  const node = useRef<HTMLSpanElement>(null)
  const previous = useRef(value)
  useLayoutEffect(() => {
    const element = node.current
    const target = { value: previous.current }
    previous.current = value
    if (element) element.textContent = String(value)
    if (reduced || !element) return
    const tween = gsap.to(target, {
      value,
      duration: 0.4,
      ease: 'power2.out',
      onUpdate: () => {
        element.textContent = String(Math.round(target.value))
      },
    })
    return () => {
      tween.kill()
      element.textContent = String(value)
    }
  }, [value, reduced])
  return (
    <span ref={node} aria-hidden="true">
      {value}
    </span>
  )
}

export function PlanStats({
  tasks,
  today,
  loading,
  unavailable,
  reduced,
  referenceDate = today,
  onOpenScope,
}: {
  tasks: Task[]
  today: Date
  loading: boolean
  unavailable: boolean
  reduced: boolean
  referenceDate?: Date
  onOpenScope?: (scope: PlanScope) => void
}) {
  const daily = completion(tasksOnDate(tasks, referenceDate)),
    weeklyPlans = plansInWeek(tasks, referenceDate),
    weekly = completion(weeklyPlans)
  const goals = tasks.filter((task) => task.scope === 'goal').length
  const week = completionDays(weeklyPlans, referenceDate)
  const maximum = Math.max(1, ...week)
  const streak = completionStreak(tasks, today)
  const dayTitle =
    dateKey(referenceDate) === dateKey(today)
      ? '今日待办'
      : `${referenceDate.getMonth() + 1}/${referenceDate.getDate()} 待办`
  const placeholder = loading ? '读取中' : unavailable ? '暂不可用' : null
  return (
    <section className="plan-stats" aria-label="计划统计" aria-busy={loading}>
      <article
        className="plan-card plan-stat"
        role="button"
        tabIndex={0}
        onClick={() => onOpenScope?.('day')}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onOpenScope?.('day')
          }
        }}
        aria-label={
          placeholder
            ? `${dayTitle}：${placeholder}`
            : `${dayTitle}：已完成 ${daily.done}，共 ${daily.total} 项`
        }
      >
        <div>
          <h2>{dayTitle}</h2>
          <p>
            {placeholder || (
              <>
                <strong>
                  <Count value={daily.done} reduced={reduced} />
                </strong>
                <span> / {daily.total}</span>
              </>
            )}
          </p>
        </div>
        <svg
          className="plan-ring"
          viewBox="0 0 48 48"
          role="img"
          aria-label={
            placeholder || (daily.total ? `今日完成率 ${daily.percent}%` : '今日暂无安排')
          }
        >
          <circle className="plan-ring-track" cx="24" cy="24" r="19" />
          <circle
            className="plan-ring-value"
            cx="24"
            cy="24"
            r="19"
            pathLength="100"
            strokeDasharray="100"
            strokeDashoffset={100 - (placeholder ? 0 : daily.percent)}
          />
        </svg>
      </article>
      <article
        className="plan-card plan-stat"
        role="button"
        tabIndex={0}
        onClick={() => onOpenScope?.('week')}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onOpenScope?.('week')
          }
        }}
        aria-label={
          placeholder
            ? `本周进度：${placeholder}`
            : `本周进度：已完成 ${weekly.done}，共 ${weekly.total} 项`
        }
      >
        <div>
          <h2>本周进度</h2>
          <p>
            {placeholder || (
              <>
                <strong>
                  <Count value={weekly.done} reduced={reduced} />
                </strong>
                <span> / {weekly.total}</span>
              </>
            )}
          </p>
        </div>
        <div
          className="plan-week-chart"
          role="img"
          aria-label={placeholder || '本周每日完成的周计划数量，按实际完成日期统计'}
        >
          {week.map((day, i) => (
            <span
              key={i}
              title={`${['周一', '周二', '周三', '周四', '周五', '周六', '周日'][i]}：完成 ${day} 项周计划`}
              style={{ height: `${Math.max(3, (day / maximum) * 44)}px` }}
            >
              <i style={{ height: `${day ? 100 : 0}%` }} />
            </span>
          ))}
        </div>
      </article>
      <article
        className="plan-card plan-stat"
        role="button"
        tabIndex={0}
        onClick={() => onOpenScope?.('goal')}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onOpenScope?.('goal')
          }
        }}
        aria-label={placeholder ? `长期目标：${placeholder}` : `长期目标：共 ${goals} 个`}
      >
        <div>
          <h2>长期目标</h2>
          <p>
            {placeholder || (
              <strong>
                <Count value={goals} reduced={reduced} />
              </strong>
            )}
          </p>
        </div>
        <span className="plan-stat-icon">
          <Target size={29} strokeWidth={1.7} />
        </span>
      </article>
      <article className="plan-card plan-stat">
        <div>
          <h2>连续完成</h2>
          <p className="plan-no-streak" title="按有实际完成时间的记录计算，旧任务不会补造历史">
            {streak === null ? '暂无记录' : `${streak} 天`}
          </p>
        </div>
        <span className="plan-stat-icon flame">
          <Flame size={28} strokeWidth={1.7} />
        </span>
      </article>
    </section>
  )
}
