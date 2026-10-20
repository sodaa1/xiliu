import { render, screen, fireEvent } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { ConversationList } from './ConversationList'
test('conversation search and date filters retain create select and delete controls', () => {
  const select = vi.fn(),
    remove = vi.fn(),
    create = vi.fn(),
    now = new Date().toISOString()
  render(
    <ConversationList
      items={[
        {
          id: 'new',
          title: '学习计划',
          created_at: now,
          updated_at: now,
          context_cutoff_seq: 0,
          compressed_through_seq: 0,
          context_summary: '',
          model_override: null,
        },
        {
          id: 'old',
          title: '旧的阅读笔记',
          created_at: '2020-01-01T00:00:00Z',
          updated_at: '2020-01-01T00:00:00Z',
          context_cutoff_seq: 0,
          compressed_through_seq: 0,
          context_summary: '',
          model_override: null,
        },
      ]}
      selected="new"
      creating={false}
      busyIds={[]}
      onCreate={create}
      onSelect={select}
      onDelete={remove}
    />
  )
  fireEvent.change(screen.getByRole('searchbox', { name: '搜索对话' }), {
    target: { value: '学习' },
  })
  expect(screen.queryByRole('button', { name: '旧的阅读笔记' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '学习计划' }))
  expect(select).toHaveBeenCalledWith('new')
  fireEvent.change(screen.getByRole('searchbox', { name: '搜索对话' }), { target: { value: '' } })
  fireEvent.click(screen.getByRole('button', { name: '今天' }))
  expect(screen.queryByRole('button', { name: '旧的阅读笔记' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '全部' }))
  expect(screen.getByRole('button', { name: '旧的阅读笔记' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: '对话操作：学习计划' }))
  fireEvent.click(screen.getByRole('button', { name: '删除对话' }))
  expect(remove).toHaveBeenCalledWith('new')
  fireEvent.click(screen.getByRole('button', { name: '创建新对话' }))
  expect(create).toHaveBeenCalledOnce()
})
