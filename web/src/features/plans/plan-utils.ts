import type { Task } from '../../lib/workspace-api'

export type PlanScope = 'day' | 'week' | 'goal'
export const scopeLabels: Record<PlanScope, string> = {
  day: '日待办',
  week: '周计划',
  goal: '长期目标',
}
export const rank: Record<PlanScope, number> = { goal: 0, week: 1, day: 2 }
export const weekdays = ['一', '二', '三', '四', '五', '六', '日']

export function dateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
export function addDays(date: Date, amount: number) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + amount)
}
export function startOfWeek(date: Date) {
  return addDays(date, -((date.getDay() + 6) % 7))
}
export function moveMonth(date: Date, amount: number) {
  const first = new Date(date.getFullYear(), date.getMonth() + amount, 1)
  return new Date(
    first.getFullYear(),
    first.getMonth(),
    Math.min(date.getDate(), new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate())
  )
}
export function calendarDays(date: Date) {
  const first = new Date(date.getFullYear(), date.getMonth(), 1)
  const start = startOfWeek(first)
  const offset = (first.getDay() + 6) % 7
  const count =
    Math.ceil((offset + new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()) / 7) * 7
  return Array.from({ length: count }, (_, i) => addDays(start, i))
}
export function parsePlanDate(value: string | null | undefined) {
  if (!value) return null
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value)
  return Number.isNaN(date.getTime()) ? null : date
}
export function taskDate(task: Task) {
  return parsePlanDate(task.starts_at ?? task.due_at)
}
export type PlanStatus = 'not_started' | 'in_progress' | 'completed'
export const statusLabels: Record<PlanStatus, string> = {
  not_started: '未开始',
  in_progress: '进行中',
  completed: '已完成',
}
export const categories = ['学习', '工作', '健康', '生活', '整理']
export function taskStatus(task: Task): PlanStatus {
  return task.completed
    ? 'completed'
    : task.status === 'in_progress'
      ? 'in_progress'
      : 'not_started'
}
export function plansInWeek(tasks: Task[], date: Date) {
  const start = startOfWeek(date),
    end = addDays(start, 7)
  return tasks.filter((task) => {
    if (task.scope !== 'week') return false
    const finished = task.completed ? parsePlanDate(task.completed_at) : null
    if (finished && finished >= start && finished < end) return true
    const from = taskDate(task),
      to = parsePlanDate(task.due_at) ?? from
    if (!from && !to) return true
    return Boolean(from && from < end && to && to >= start)
  })
}
export function completionDays(tasks: Task[], date: Date) {
  return Array.from({ length: 7 }, (_, i) => {
    const day = dateKey(addDays(startOfWeek(date), i))
    return tasks.filter((task) => {
      const finished = task.completed ? parsePlanDate(task.completed_at) : null
      return finished && dateKey(finished) === day
    }).length
  })
}
export function completionStreak(tasks: Task[], date: Date) {
  const days = new Set(
    tasks.flatMap((task) => {
      const finished = task.completed ? parsePlanDate(task.completed_at) : null
      return finished ? [dateKey(finished)] : []
    })
  )
  if (!days.size) return null
  let cursor = days.has(dateKey(date)) ? date : addDays(date, -1),
    count = 0
  while (days.has(dateKey(cursor))) {
    count++
    cursor = addDays(cursor, -1)
  }
  return count
}
export function tasksOnDate(tasks: Task[], date: Date) {
  const key = dateKey(date)
  return tasks.filter((task) => {
    const due = taskDate(task)
    return (task.scope ?? 'day') === 'day' && due && dateKey(due) === key
  })
}
export function weekTasks(tasks: Task[], date: Date) {
  const start = startOfWeek(date),
    end = addDays(start, 7)
  return tasks.filter((task) => {
    const due = taskDate(task)
    return (task.scope ?? 'day') === 'day' && due && due >= start && due < end
  })
}
export function completion(tasks: Task[]) {
  const total = tasks.length,
    done = tasks.filter((task) => task.completed).length
  return { done, total, percent: total ? Math.round((done / total) * 100) : 0 }
}
export function linkedProgress(tasks: Task[], parentId: string) {
  return completion(tasks.filter((task) => task.parent_id === parentId))
}
export function dateLabel(date: Date) {
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}
export function inputDate(date: Date | null) {
  if (!date) return ''
  return `${dateKey(date)}T${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
