import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { GlideSelect } from './GlideSelect'
import { Modal } from './Modal'

test('keyboard selects an option, Escape preserves it and returns focus', async () => {
  const change = vi.fn()
  render(
    <GlideSelect
      ariaLabel="导出格式"
      defaultValue="png"
      onChange={change}
      options={[
        { value: 'png', label: 'PNG' },
        { value: 'pdf', label: 'PDF' },
      ]}
    />
  )
  const user = userEvent.setup()
  const trigger = screen.getByRole('combobox', { name: '导出格式' })
  await user.click(trigger)
  await user.keyboard('{End}{Enter}')
  expect(trigger).toHaveTextContent('PDF')
  expect(change).toHaveBeenCalledWith('pdf', { value: 'pdf', label: 'PDF' })
  await user.click(trigger)
  await user.keyboard('{Home}{Escape}')
  expect(trigger).toHaveFocus()
  expect(trigger).toHaveTextContent('PDF')
  expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
})

test('Tab stays in the modal and Escape closes the menu before the modal', async () => {
  const close = vi.fn()
  render(
    <Modal title="偏好" onClose={close}>
      <GlideSelect ariaLabel="模式" options={[{ value: 'a', label: 'A' }]} />
      <button>保存</button>
    </Modal>
  )
  const user = userEvent.setup()
  const trigger = screen.getByRole('combobox', { name: '模式' })
  await user.click(trigger)
  await user.tab()
  expect(screen.getByRole('button', { name: '保存' })).toHaveFocus()
  await user.click(trigger)
  await user.keyboard('{Escape}')
  expect(close).not.toHaveBeenCalled()
  await user.keyboard('{Escape}')
  expect(close).toHaveBeenCalledOnce()
})
