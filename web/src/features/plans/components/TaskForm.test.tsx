import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { TaskForm } from './TaskForm'
import type { Task } from '../../../lib/workspace-api'

test('editing an overnight daily task preserves both endpoint dates', async () => {
  const submit = vi.fn(),
    user = userEvent.setup()
  const task: Task = {
    id: 'overnight',
    title: '跨午夜任务',
    scope: 'day',
    completed: false,
    starts_at: new Date(2026, 9, 17, 23).toISOString(),
    due_at: new Date(2026, 9, 18, 1).toISOString(),
    parent_id: null,
    created_at: '',
    updated_at: '',
  }
  render(
    <TaskForm
      task={task}
      tasks={[task]}
      initialScope="day"
      busy={false}
      error={null}
      onSubmit={submit}
      onCancel={() => {}}
    />
  )
  await user.type(screen.getByLabelText('任务标题'), '更新')
  await user.click(screen.getByRole('button', { name: '保存修改' }))
  expect(submit).toHaveBeenCalledWith(
    expect.objectContaining({
      starts_at: task.starts_at,
      due_at: task.due_at,
      title: '跨午夜任务更新',
    })
  )
})

test('new daily task inherits selected date and submits category, metadata and status', async () => {
  const submit = vi.fn(),
    user = userEvent.setup()
  render(
    <TaskForm
      tasks={[]}
      initialScope="day"
      initialDate={new Date(2026, 9, 23)}
      busy={false}
      error={null}
      onSubmit={submit}
      onCancel={() => {}}
    />
  )
  expect(screen.getByLabelText('任务日期')).toHaveValue('2026-10-23')
  await user.type(screen.getByLabelText('任务标题'), '阅读')
  await user.type(screen.getByLabelText('任务描述（可选）'), '记录要点')
  await user.click(screen.getByRole('radio', { name: '学习' }))
  await user.click(screen.getByRole('radio', { name: '重要' }))
  await user.click(screen.getByRole('radio', { name: '进行中' }))
  await user.type(screen.getByLabelText('任务标签（可选）'), '书籍{Enter}')
  await user.click(screen.getByRole('button', { name: '创建任务' }))
  expect(submit.mock.calls[0][0]).toMatchObject({
    category: '学习',
    description: '记录要点',
    priority: 'important',
    status: 'in_progress',
    completed: false,
    tags: ['书籍'],
    starts_at: new Date(2026, 9, 23, 9).toISOString(),
    due_at: new Date(2026, 9, 23, 9).toISOString(),
  })
})

test('weekly planning uses an interval and rejects an end before its start', async () => {
  const submit = vi.fn(),
    user = userEvent.setup()
  render(
    <TaskForm
      tasks={[]}
      initialScope="week"
      initialDate={new Date(2026, 9, 23)}
      busy={false}
      error={null}
      onSubmit={submit}
      onCancel={() => {}}
    />
  )
  await user.type(screen.getByLabelText('任务标题'), '本周阅读')
  fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '2026-10-23T09:00' } })
  fireEvent.change(screen.getByLabelText('截止日期'), { target: { value: '2026-10-22T09:00' } })
  await user.click(screen.getByRole('button', { name: '创建任务' }))
  expect(submit).not.toHaveBeenCalled()
  expect(screen.getByRole('alert')).toHaveTextContent('截止时间不能早于开始时间')
})
