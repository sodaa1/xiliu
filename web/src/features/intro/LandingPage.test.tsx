import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { LandingPage } from '../../../../docs/web/src/LandingPage'
vi.mock('../../../../docs/web/src/useLandingMotion', () => ({ useLandingMotion: () => {} }))

test('Intro links, workflow tabs, keyboard navigation and menu remain available', async () => {
  render(<LandingPage />)
  const user = userEvent.setup()
  expect(screen.getByRole('link', { name: '打开本地工作台' })).toHaveAttribute('href', '/today')
  expect(screen.getByRole('link', { name: '打开资讯' })).toHaveAttribute('href', '/feed')
  const tabs = screen.getByRole('tablist', { name: '信息流演示' })
  for (const name of ['收集', '整理', '对话', '行动']) {
    await user.click(within(tabs).getByRole('tab', { name }))
    expect(screen.getByRole('tabpanel', { name })).toBeVisible()
  }
  await user.keyboard('{Home}')
  expect(within(tabs).getByRole('tab', { name: '收集' })).toHaveFocus()
  await user.keyboard('{ArrowRight}')
  expect(screen.getByRole('tabpanel', { name: '整理' })).toBeVisible()
  await user.click(screen.getByRole('button', { name: '打开导航' }))
  expect(screen.getByRole('navigation', { name: '介绍页导航' })).toHaveClass('is-open')
  await user.keyboard('{Escape}')
  expect(screen.getByRole('button', { name: '打开导航' })).toHaveFocus()
})

test('Intro clipboard feedback covers success and refusal', async () => {
  render(<LandingPage />)
  const user = userEvent.setup()
  const write = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue()
  await user.click(screen.getByRole('button', { name: '复制安装命令' }))
  expect(await screen.findByRole('status')).toHaveTextContent('安装命令已复制')
  write.mockRejectedValueOnce(new Error('clipboard denied'))
  await user.click(screen.getByRole('button', { name: '复制安装命令' }))
  expect(await screen.findByRole('status')).toHaveTextContent('请选中下方命令手动复制')
})
