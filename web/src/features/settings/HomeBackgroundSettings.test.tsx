import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { HomeBackgroundSettings } from './HomeBackgroundSettings'
afterEach(() => vi.unstubAllGlobals())
test('background selection persists through the media service and invalid imports preserve it', async () => {
  let settings = { mode: 'blank', selected: null }
  vi.stubGlobal('fetch', async (_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') settings = JSON.parse(String(init.body))
    return Response.json(init?.method === 'PUT' ? settings : { settings, images: [] })
  })
  render(<HomeBackgroundSettings />)
  await waitFor(() => expect(screen.getByRole('button', { name: '纯色留白' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: '内置背景' }))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: '内置背景' })).toHaveAttribute('aria-pressed', 'true')
  )
  fireEvent.change(screen.getByLabelText('导入主页背景'), {
    target: { files: [new File(['<html>bad'], 'fake.png', { type: 'image/png' })] },
  })
  expect(await screen.findByRole('alert')).toHaveTextContent('图片格式不支持')
  expect(screen.getByRole('button', { name: '内置背景' })).toHaveAttribute('aria-pressed', 'true')
  fireEvent.click(screen.getByRole('button', { name: '纯色留白' }))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: '纯色留白' })).toHaveAttribute('aria-pressed', 'true')
  )
})
