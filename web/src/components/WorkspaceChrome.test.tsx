import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, test } from 'vitest'
import { WorkspaceChromeProvider, WorkspaceSidebar, PageToolbar } from './WorkspaceChrome'
test('shared rail preserves original icon-only order and toolbar exposes icon theme choices', () => {
  render(
    <MemoryRouter initialEntries={['/today']}>
      <WorkspaceChromeProvider>
        <WorkspaceSidebar />
        <PageToolbar />
      </WorkspaceChromeProvider>
    </MemoryRouter>
  )
  const rail = screen.getByRole('navigation', { name: '主导航' })
  expect(
    within(rail)
      .getAllByRole('link')
      .map((link) => link.getAttribute('aria-label'))
  ).toEqual(['今日', '助手', '资讯', '收件箱', '知识库', '个人计划'])
  expect(rail.textContent).toBe('')
  expect(screen.getByRole('button', { name: '原有主题' }).textContent).toBe('')
  expect(screen.getByRole('button', { name: '山水工作台' }).textContent).toBe('')
})
