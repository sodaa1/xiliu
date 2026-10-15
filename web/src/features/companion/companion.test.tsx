import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { CaptureDialog } from '../content/CaptureDialog'

afterEach(() => vi.unstubAllGlobals())

test('a rapid duplicate capture submit imports only once and preserves failed input', async () => {
  let finish!: (value: Response) => void
  const fetcher = vi.fn(
    () =>
      new Promise<Response>((resolve) => {
        finish = resolve
      })
  )
  vi.stubGlobal('fetch', fetcher)
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}
    >
      <CaptureDialog onClose={() => {}} onSaved={() => {}} />
    </QueryClientProvider>
  )
  fireEvent.change(screen.getByRole('textbox'), { target: { value: '保留这条灵感' } })
  const form = screen.getByRole('textbox').closest('form')!
  act(() => {
    fireEvent.submit(form)
    fireEvent.submit(form)
  })
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
  expect(screen.getByRole('textbox')).toBeDisabled()
  await act(async () =>
    finish(Response.json({ error: { message: '暂时无法保存' } }, { status: 503 }))
  )
  expect(await screen.findByRole('alert')).toHaveTextContent('暂时无法保存')
  expect(screen.getByRole('textbox')).toHaveValue('保留这条灵感')
  expect(screen.getByRole('button', { name: '收进 Inbox' })).toBeEnabled()
})
