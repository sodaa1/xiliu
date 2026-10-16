import { render, screen, waitFor, cleanup, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import { Onboarding } from './Onboarding'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { resetGuide, startGuide } from './progress'
function Location() {
  const location = useLocation()
  return (
    <output aria-label="当前地址">
      {location.pathname}
      {location.search}
    </output>
  )
}
function mount(path = '/plans') {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <Location />
        <Onboarding />
      </MemoryRouter>
    </QueryClientProvider>
  )
}
beforeEach(() => {
  localStorage.clear()
  resetGuide()
})
test('first visit opens automatically; skipping persists and restores the original route', async () => {
  const request = vi.spyOn(globalThis, 'fetch')
  mount()
  expect(screen.getByRole('dialog', { name: '欢迎使用息流' })).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: '下一步' }))
  await waitFor(() => expect(screen.getByLabelText('当前地址')).toHaveTextContent('/today'))
  await userEvent.click(screen.getByRole('button', { name: '跳过引导' }))
  await waitFor(() => expect(screen.getByLabelText('当前地址')).toHaveTextContent('/plans'))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  cleanup()
  mount()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(request).not.toHaveBeenCalled()
  request.mockRestore()
})
test('all modules can be introduced with next/back alone and replay is explicit', async () => {
  mount('/feed')
  const seen = new Set<string>()
  for (let step = 0; step < 20; step++) {
    seen.add(screen.getByRole('dialog').getAttribute('aria-label')!)
    const finish = screen.queryByRole('button', { name: '开始使用' })
    if (finish) {
      await userEvent.click(finish)
      break
    }
    await userEvent.click(screen.getByRole('button', { name: '下一步' }))
    if (step === 1) {
      await userEvent.click(screen.getByRole('button', { name: '上一步' }))
      await userEvent.click(screen.getByRole('button', { name: '下一步' }))
    }
  }
  expect([...seen]).toEqual(
    expect.arrayContaining([
      '资讯',
      '收件箱',
      '知识库',
      '助手',
      '个人计划',
      '模型连接',
      '外观与桌宠',
      '自动任务',
      '个人资料与数据',
    ])
  )
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  cleanup()
  mount()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  act(() => startGuide())
  await screen.findByRole('dialog', { name: '欢迎使用息流' })
})
test('Escape skips the tour and releases document scroll locking', async () => {
  mount()
  await userEvent.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(document.documentElement).not.toHaveClass('onboarding-active')
})
