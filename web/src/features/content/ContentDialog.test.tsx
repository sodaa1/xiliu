import { render, screen, fireEvent } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { ContentDialog } from './ContentDialog'
test('dialog Escape and Tab work when a pending button loses focus to body', () => {
  const close = vi.fn()
  render(
    <ContentDialog title="收藏" onClose={close}>
      <button disabled>保存中</button>
    </ContentDialog>
  )
  const closeButton = screen.getByRole('button', { name: '关闭弹窗' })
  closeButton.focus()
  closeButton.blur()
  expect(document.body).toHaveFocus()
  fireEvent.keyDown(document.body, { key: 'Tab' })
  expect(screen.getByRole('button', { name: '关闭弹窗' })).toHaveFocus()
  fireEvent.keyDown(document.body, { key: 'Escape' })
  expect(close).toHaveBeenCalledOnce()
})
