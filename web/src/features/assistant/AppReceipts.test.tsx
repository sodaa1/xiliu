import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { AppReceipts } from './AppReceipts'

test('review requires human click and refreshes persisted result', async () => {
  const fetch = vi.fn<(input: string, init?: RequestInit) => Promise<Response>>(async () =>
    Response.json({ ok: true })
  )
  vi.stubGlobal('fetch', fetch)
  const metadata = JSON.stringify({
    app_receipts: [
      {
        status: 'confirmation_required',
        confirmation_id: 'token',
        description: '删除待办',
        arguments: { task_id: 'task-id' },
      },
    ],
  })
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AppReceipts sessionId="session" metadata={metadata} />
    </QueryClientProvider>
  )
  expect(fetch).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: '审核操作' }))
  expect(screen.getByRole('dialog')).toHaveTextContent('删除待办')
  expect(fetch).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: '确认执行' }))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('操作已完成'))
  expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({
    session_id: 'session',
    confirmation_id: 'token',
  })
})

test('closing review leaves the operation untouched', async () => {
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AppReceipts
        sessionId="s"
        metadata={JSON.stringify({
          app_receipts: [{ status: 'confirmation_required', confirmation_id: 't' }],
        })}
      />
    </QueryClientProvider>
  )
  await userEvent.click(screen.getByRole('button', { name: '审核操作' }))
  await userEvent.click(screen.getByRole('button', { name: '取消' }))
  expect(fetch).not.toHaveBeenCalled()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

afterEach(() => vi.unstubAllGlobals())

function renderArchive() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AppReceipts
        sessionId="s"
        metadata={JSON.stringify({
          app_receipts: [{ status: 'pending', data: { job_id: 'archive/id' } }],
        })}
      />
    </QueryClientProvider>
  )
}

test('archive progress polls until persisted completion then stops polling', async () => {
  let reads = 0
  const fetch = vi.fn<(input: string, init?: RequestInit) => Promise<Response>>(async () =>
    Response.json({ status: ++reads === 1 ? 'pending' : 'completed' })
  )
  vi.stubGlobal('fetch', fetch)
  renderArchive()
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1))
  expect(screen.getByRole('status')).toHaveTextContent('正在生成标签')
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('已归档到知识库'), {
    timeout: 3000,
  })
  expect(fetch.mock.calls[0][0]).toBe('/api/inbox/archive-jobs/archive%2Fid')
  const finishedReads = fetch.mock.calls.length
  await new Promise((resolve) => setTimeout(resolve, 1700))
  expect(fetch).toHaveBeenCalledTimes(finishedReads)
})

test.each([
  ['running', '正在归档'],
  ['conflict', '保留修改'],
  ['failed', '归档未完成'],
  ['cancelled', '已停止自动归档'],
])(
  'archive progress shows the persisted %s state without claiming completion',
  async (status, label) => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Response.json({ status }))
    )
    renderArchive()
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(label))
    expect(screen.getByRole('status')).not.toHaveTextContent('已归档到知识库')
  }
)

test('archive progress reports read failure without claiming completion', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      Response.json({ error: { code: 'offline', message: 'unavailable' } }, { status: 503 })
    )
  )
  renderArchive()
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('归档进度暂不可用'), {
    timeout: 4000,
  })
  expect(screen.getByRole('status')).not.toHaveTextContent('已归档到知识库')
})

test.each([
  ['pending', { total: 3, completed: 1, failed: 1, pending: 1 }, '已归档 1/3'],
  ['partial', { total: 3, completed: 1, failed: 1, conflict: 1 }, '未完成 2'],
  ['completed', { total: 3, completed: 3, failed: 0 }, '已归档 3/3'],
])('batch progress shows persisted counts for %s', async (status, counts, label) => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ status, counts })))
  renderArchive()
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(label))
  expect(screen.getByRole('status')).not.toHaveTextContent('指定文件夹')
})
