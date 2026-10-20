import { describe, expect, test } from 'vitest'
import type { Task } from '../../lib/workspace-api'
import {
  calendarDays,
  dateKey,
  moveMonth,
  startOfWeek,
  tasksOnDate,
  completion,
  linkedProgress,
  weekTasks,
  plansInWeek,
  taskStatus,
  completionDays,
  completionStreak,
  parsePlanDate,
} from './plan-utils'

test('date-only completion records remain on their local calendar day in every timezone', () => {
  const row = task('date-only', '2026-10-18', true, 'week')
  row.completed_at = '2026-10-18'
  expect(parsePlanDate(row.completed_at)?.getHours()).toBe(0)
  expect(completionDays([row], new Date(2026, 9, 18))).toEqual([0, 0, 0, 0, 0, 0, 1])
  expect(completionStreak([row], new Date(2026, 9, 18))).toBe(1)
})

test('current-week plans include overlapping intervals and unscheduled backlog consistently', () => {
  const rows = [
    task('overlap', new Date(2026, 9, 20).toISOString(), false, 'week'),
    task('none', null, false, 'week'),
    task('next', new Date(2026, 9, 26).toISOString(), false, 'week'),
  ]
  Object.assign(rows[0], { starts_at: new Date(2026, 9, 12).toISOString() })
  expect(plansInWeek(rows, new Date(2026, 9, 18)).map((row) => row.id)).toEqual(['overlap', 'none'])
  expect(taskStatus(rows[0])).toBe('not_started')
})

test('completion-day chart uses actual completion dates instead of scheduled dates', () => {
  const rows = [
    task('a', new Date(2026, 9, 12).toISOString(), true, 'week'),
    task('b', null, true, 'week'),
  ]
  Object.assign(rows[0], { completed_at: new Date(2026, 9, 17, 20).toISOString() })
  expect(completionDays(rows, new Date(2026, 9, 18))).toEqual([0, 0, 0, 0, 0, 1, 0])
})

test('an overdue weekly plan completed this week belongs to the same weekly list and chart', () => {
  const overdue = task('overdue', new Date(2026, 9, 10).toISOString(), true, 'week')
  Object.assign(overdue, { completed_at: new Date(2026, 9, 18, 10).toISOString() })
  const current = plansInWeek([overdue], new Date(2026, 9, 18))
  expect(current.map((row) => row.id)).toEqual(['overdue'])
  expect(completionDays(current, new Date(2026, 9, 18))).toEqual([0, 0, 0, 0, 0, 0, 1])
})

const task = (
  id: string,
  due_at: string | null,
  completed = false,
  scope: Task['scope'] = 'day',
  parent_id: string | null = null
): Task => ({ id, title: id, due_at, completed, scope, parent_id, created_at: '', updated_at: '' })

describe('local planning dates', () => {
  test('calendar starts on Monday, includes all month days and crosses a year', () => {
    const days = calendarDays(new Date(2027, 0, 15))
    expect(dateKey(days[0])).toBe('2026-12-28')
    expect(dateKey(days.at(-1)!)).toBe('2027-01-31')
    expect(days).toHaveLength(35)
    expect(calendarDays(new Date(2026, 2, 1))).toHaveLength(42)
    expect(dateKey(startOfWeek(new Date(2027, 0, 3)))).toBe('2026-12-28')
  })
  test('month navigation clamps the day instead of skipping February', () => {
    expect(dateKey(moveMonth(new Date(2026, 0, 31), 1))).toBe('2026-02-28')
    expect(dateKey(moveMonth(new Date(2024, 0, 31), 1))).toBe('2024-02-29')
    expect(dateKey(moveMonth(new Date(2026, 11, 31), 1))).toBe('2027-01-31')
  })
  test('tasks match local dates, exclude undated and non-daily plans', () => {
    const due = new Date(2026, 9, 18, 0, 15).toISOString()
    const tasks = [
      task('today', due),
      task('undated', null),
      task('goal', due, false, 'goal'),
      task('invalid', 'invalid'),
    ]
    expect(tasksOnDate(tasks, new Date(2026, 9, 18)).map((t) => t.id)).toEqual(['today'])
    expect(tasksOnDate(tasks, new Date(2026, 9, 17))).toEqual([])
  })
})

test('weekly totals include Monday through Sunday once and exclude unscheduled tasks', () => {
  const tasks = [
    task('sun', new Date(2027, 0, 3, 23, 59).toISOString(), true),
    task('mon', new Date(2026, 11, 28).toISOString()),
    task('next', new Date(2027, 0, 4).toISOString()),
    task('none', null),
  ]
  expect(weekTasks(tasks, new Date(2027, 0, 3)).map((t) => t.id)).toEqual(['sun', 'mon'])
  expect(completion(weekTasks(tasks, new Date(2027, 0, 3)))).toEqual({
    done: 1,
    total: 2,
    percent: 50,
  })
})

test('parent progress uses direct children and never invents empty progress', () => {
  const tasks = [
    task('week', null, false, 'week', 'goal'),
    task('day', null, true, 'day', 'week'),
    task('other', null, true),
  ]
  expect(linkedProgress(tasks, 'week')).toEqual({ done: 1, total: 1, percent: 100 })
  expect(linkedProgress(tasks, 'goal')).toEqual({ done: 0, total: 1, percent: 0 })
  expect(linkedProgress(tasks, 'empty')).toEqual({ done: 0, total: 0, percent: 0 })
})
