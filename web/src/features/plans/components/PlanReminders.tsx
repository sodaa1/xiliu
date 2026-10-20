import { useEffect, useState } from 'react'
import { Bell, X } from 'lucide-react'
import type { Task } from '../../../lib/workspace-api'
import { parsePlanDate } from '../plan-utils'

export function PlanReminders({ tasks }: { tasks: Task[] }) {
  const [clock, setClock] = useState(Date.now)
  const [dismissed, setDismissed] = useState<string[]>([])
  useEffect(() => {
    const tick = () => setClock(Date.now())
    const timer = setInterval(tick, 30000)
    window.addEventListener('focus', tick)
    return () => {
      clearInterval(timer)
      window.removeEventListener('focus', tick)
    }
  }, [])
  const reminders = tasks
    .filter((task) => {
      const anchor = task.starts_at ?? task.due_at
      const scheduled = parsePlanDate(anchor)
      return (
        !task.completed &&
        task.reminder_minutes != null &&
        scheduled &&
        scheduled.getTime() - task.reminder_minutes * 60000 <= clock &&
        !dismissed.includes(`${task.id}:${anchor}:${task.reminder_minutes}`)
      )
    })
    .slice(0, 3)
  if (!reminders.length) return null
  return (
    <section className="plan-reminders" role="status" aria-label="任务提醒">
      {reminders.map((task) => (
        <div key={task.id}>
          <Bell size={16} />
          <span>任务提醒：{task.title}</span>
          <button
            aria-label={`关闭提醒 ${task.title}`}
            onClick={() =>
              setDismissed([
                ...dismissed,
                `${task.id}:${task.starts_at ?? task.due_at}:${task.reminder_minutes}`,
              ])
            }
          >
            <X size={15} />
          </button>
        </div>
      ))}
    </section>
  )
}
