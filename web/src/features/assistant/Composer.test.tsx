import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { Composer } from './Composer'
function Harness({ initial = '', send = () => {} }: { initial?: string; send?: () => void }) {
  const [text, setText] = useState(initial)
  return (
    <Composer
      text={text}
      onText={setText}
      onSend={send}
      disabled={false}
      skills={[{ name: 'xiliu-debugging', description: '诊断问题' }]}
      mcp={[{ name: 'aihot', description: 'AI 资讯' }]}
    />
  )
}
test('selecting skill command immediately offers installed skill names', async () => {
  const user = userEvent.setup()
  render(<Harness />)
  await user.type(screen.getByRole('textbox'), '/skill')
  await user.keyboard('{Enter}')
  expect(await screen.findByRole('option', { name: /xiliu-debugging/ })).toBeVisible()
  await user.keyboard('{Enter}')
  expect(screen.getByRole('textbox')).toHaveValue('/skill xiliu-debugging ')
})
test('MCP server name completes with keyboard without sending', async () => {
  const user = userEvent.setup(),
    send = vi.fn()
  render(<Harness send={send} />)
  await user.type(screen.getByRole('textbox'), '/mcp ai')
  expect(await screen.findByRole('option', { name: /aihot/ })).toBeVisible()
  await user.keyboard('{Tab}')
  expect(screen.getByRole('textbox')).toHaveValue('/mcp aihot ')
  expect(send).not.toHaveBeenCalled()
})
test('IME enter and Shift enter do not send a message', async () => {
  const user = userEvent.setup(),
    send = vi.fn()
  render(<Harness initial="你好" send={send} />)
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', code: 'Enter', isComposing: true })
  expect(send).not.toHaveBeenCalled()
  await user.click(screen.getByRole('textbox'))
  await user.keyboard('{Shift>}{Enter}{/Shift}')
  expect(send).not.toHaveBeenCalled()
})
