import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { TaskMenu } from './TaskMenu'
test('task menu supports color states edit delete and Escape focus restoration', async () => {
  const user = userEvent.setup(),
    status = vi.fn(),
    edit = vi.fn(),
    remove = vi.fn()
  const task = {
    id: 't',
    title: '整理资料',
    completed: false,
    status: 'not_started' as const,
    due_at: null,
    created_at: '',
    updated_at: '',
  }
  render(<TaskMenu task={task} busy={false} onStatus={status} onEdit={edit} onDelete={remove} />)
  const trigger = screen.getByRole('button', { name: '任务操作：整理资料' })
  await user.click(trigger)
  expect(screen.getByRole('menuitemradio', { name: '未开始' })).toHaveFocus()
  fireEvent.scroll(document)
  expect(screen.getByRole('menu')).toBeInTheDocument()
  await user.keyboard('{ArrowRight}{Enter}')
  expect(status).toHaveBeenCalledWith(task, 'in_progress')
  expect(trigger).toHaveFocus()
  await user.click(trigger)
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  expect(trigger).toHaveFocus()
  await user.click(trigger)
  await user.click(screen.getByRole('menuitem', { name: '编辑任务' }))
  expect(edit).toHaveBeenCalledWith(task)
  expect(trigger).toHaveFocus()
  await user.click(trigger)
  await user.click(screen.getByRole('menuitem', { name: '删除任务' }))
  expect(remove).toHaveBeenCalledWith(task)
})
