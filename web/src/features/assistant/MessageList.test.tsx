import { render, screen, fireEvent } from '@testing-library/react'
import { test, expect, vi } from 'vitest'
import { MessageList } from './MessageList'
test('reference welcome shortcuts fill real prompts without sending a request', () => {
  const prompt = vi.fn()
  render(<MessageList messages={[]} loading={false} onPrompt={prompt} />)
  expect(screen.getByRole('heading', { name: '息流 AI 助手' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: /拆解计划/ }))
  expect(prompt).toHaveBeenLastCalledWith('请帮我把以下目标拆成可以执行的计划：')
  fireEvent.click(screen.getByRole('button', { name: /工具与连接/ }))
  expect(prompt).toHaveBeenLastCalledWith('/mcp ')
})
