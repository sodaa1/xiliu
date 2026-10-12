import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { LandingPage } from './LandingPage'

vi.mock('./useLandingMotion', () => ({ useLandingMotion: () => undefined }))

test('the product demo supports arrow-key navigation without sending an API request', () => {
  const fetchSpy = vi.spyOn(window, 'fetch')
  render(<LandingPage />)
  const collect = screen.getByRole('tab', { name: '收集' })
  collect.focus()
  fireEvent.keyDown(collect, { key: 'ArrowRight' })
  expect(screen.getByRole('tab', { name: '整理' })).toHaveAttribute('aria-selected', 'true')
  expect(screen.getByRole('tab', { name: '整理' })).toHaveFocus()
  expect(screen.getByRole('tabpanel')).toHaveTextContent('Knowledge')
  fireEvent.keyDown(screen.getByRole('tab', { name: '整理' }), { key: 'End' })
  expect(screen.getByRole('tab', { name: '行动' })).toHaveAttribute('aria-selected', 'true')
  expect(fetchSpy).not.toHaveBeenCalled()
})

test('installation copy reports success only after the clipboard accepts the commands', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  render(<LandingPage />)
  fireEvent.click(screen.getByRole('button', { name: '复制安装命令' }))
  expect(await screen.findByRole('status')).toHaveTextContent('安装命令已复制')
  expect(writeText.mock.calls[0][0]).toContain('uv sync --dev')
})

test('clipboard failure offers manual copying instead of a false success', async () => {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
  })
  render(<LandingPage />)
  fireEvent.click(screen.getByRole('button', { name: '复制安装命令' }))
  expect(await screen.findByRole('status')).toHaveTextContent('请选中下方命令手动复制')
})

test('the public introduction uses the current repository and source installation commands', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  render(<LandingPage publicShowcase />)
  expect(screen.getByRole('link', { name: 'GitHub · xiliu' })).toHaveAttribute('href', 'https://github.com/sodaa1/xiliu')
  expect(screen.getByRole('link', { name: '查看 GitHub 项目' })).toHaveAttribute('href', 'https://github.com/sodaa1/xiliu')
  expect(screen.getByText(/个人信息与 AI 助手 · 0.3.0/)).toBeInTheDocument()
  expect(screen.getByText(/Windows 已完成 0.3.0/)).toBeInTheDocument()
  expect(document.querySelector('a[href="/today"]')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '复制安装命令' }))
  expect(await screen.findByRole('status')).toHaveTextContent('安装命令已复制')
  expect(writeText.mock.calls[0][0]).toContain('git clone https://github.com/sodaa1/xiliu.git\ncd xiliu\nuv sync --dev')
})
