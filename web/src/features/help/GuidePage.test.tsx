import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { expect, test } from 'vitest'
import { GuidePage } from './GuidePage'

function mount(path = '/guide') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/guide" element={<GuidePage />} />
        <Route path="/guide/:slug" element={<GuidePage />} />
      </Routes>
    </MemoryRouter>
  )
}
test('guide searches feature introductions and offers a clear empty state', async () => {
  mount()
  const user = userEvent.setup()
  await user.type(screen.getByRole('searchbox', { name: '搜索功能与指南' }), '批量归类')
  expect(screen.getByRole('link', { name: /批量归类/ })).toHaveAttribute(
    'href',
    expect.stringContaining('/guide/inbox#')
  )
  await user.clear(screen.getByRole('searchbox'))
  await user.type(screen.getByRole('searchbox'), 'nothing-matches-123')
  expect(screen.getByText('没有找到对应功能')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '清空搜索' }))
  expect(screen.getByRole('heading', { name: '从一条资讯，开始使用息流' })).toBeInTheDocument()
})
test('deep link reads an offline article with a working feature entry', () => {
  mount('/guide/assistant')
  expect(screen.getByRole('heading', { name: '停止回复' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '前往 助手' })).toHaveAttribute('href', '/assistant')
})
test('desktop-only features are labelled and invalid articles recover to the directory', () => {
  const view = mount('/guide/appearance-companion')
  expect(screen.getAllByText('桌面专属').length).toBeGreaterThan(0)
  view.unmount()
  mount('/guide/not-an-article')
  expect(screen.getByText('未找到这篇指南，请从目录重新选择。')).toBeInTheDocument()
})
