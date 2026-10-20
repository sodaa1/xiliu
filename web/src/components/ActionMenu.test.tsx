import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { test, expect, vi } from 'vitest'
import { ActionMenu } from './ActionMenu'

test('row action menu keeps keyboard navigation disabled actions and return focus', async () => {
  const user = userEvent.setup(),
    edit = vi.fn()
  render(
    <ActionMenu label="内容操作：阅读笔记">
      <button disabled>暂不可用</button>
      <button onClick={edit}>编辑</button>
      <a href="#source">原文</a>
    </ActionMenu>
  )
  const trigger = screen.getByRole('button', { name: '内容操作：阅读笔记' })
  trigger.focus()
  await user.keyboard('{ArrowDown}')
  expect(screen.getByRole('menuitem', { name: '编辑' })).toHaveFocus()
  await user.keyboard('{ArrowDown}')
  expect(screen.getByRole('menuitem', { name: '原文' })).toHaveFocus()
  await user.keyboard('{Home}{Enter}')
  expect(edit).toHaveBeenCalledOnce()
  expect(trigger).toHaveFocus()
  await user.click(trigger)
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  expect(trigger).toHaveFocus()
})
