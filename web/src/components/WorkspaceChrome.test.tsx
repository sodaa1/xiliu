import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, test } from 'vitest'
import { WorkspaceSidebar, WorkspaceControls } from './WorkspaceChrome'

test.each(['/assistant', '/feed', '/inbox', '/knowledge', '/plans'])(
  'shared chrome has no top search or home switch on %s',
  (path) => {
    render(
      <MemoryRouter initialEntries={[path]}>
        <WorkspaceSidebar />
        <WorkspaceControls />
      </MemoryRouter>
    )
    expect(screen.queryByRole('group', { name: '首页主题' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /搜索/ })).not.toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: '主导航' }).closest('aside')).toHaveClass(
      'workspace-sidebar'
    )
  }
)
test('workspace navigation keeps only accessible icons without sidebar search', () => {
  render(
    <MemoryRouter initialEntries={['/today']}>
      <WorkspaceSidebar />
      <WorkspaceControls />
    </MemoryRouter>
  )
  const rail = screen.getByRole('navigation', { name: '主导航' })
  expect(
    within(rail)
      .getAllByRole('link')
      .map((link) => link.getAttribute('aria-label'))
  ).toEqual(['今日', '助手', '资讯', '收件箱', '知识库', '个人计划'])
  expect(rail.textContent).toBe('')
  expect(screen.getByRole('group', { name: '首页主题' })).toBeVisible()
  expect(screen.queryByRole('button', { name: /搜索/ })).not.toBeInTheDocument()
})
