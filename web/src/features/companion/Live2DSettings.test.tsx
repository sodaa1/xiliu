import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { Live2DSettings } from './Live2DSettings'
import { CompanionSettings } from './CompanionSettings'
afterEach(() => {
  vi.unstubAllGlobals()
  delete window.__TAURI__
})
test('each Live2D form has its own preview and model import entry', async () => {
  vi.stubGlobal('fetch', async () => Response.json(null))
  const view = render(<Live2DSettings />)
  fireEvent.click(screen.getByRole('button', { name: '常规比例' }))
  await waitFor(() =>
    expect(view.container.querySelector('.pet-avatar img')).toHaveAttribute(
      'src',
      '/companion/standing.png'
    )
  )
  expect(screen.getByLabelText('导入 Live2D 模型文件夹')).toBeEnabled()
  fireEvent.click(screen.getByRole('button', { name: 'Q 版' }))
  expect(view.container.querySelector('.pet-avatar img')).toHaveAttribute(
    'src',
    '/companion/chibi.png'
  )
})
test('native pet settings save the selected form and preserve the small window size', async () => {
  let settings = { enabled: true, visible: true, height: 96, alwaysOnTop: true, form: 'chibi' }
  window.__TAURI__ = {
    core: {
      invoke: async (command, args) => {
        if (command === 'companion_settings') return settings
        if (command === 'companion_configure') {
          settings = args?.settings as typeof settings
          return settings
        }
      },
    },
  }
  render(<CompanionSettings />)
  fireEvent.change(await screen.findByLabelText('桌宠形态'), { target: { value: 'standing' } })
  await waitFor(() => expect(screen.getByLabelText('桌宠形态')).toHaveValue('standing'))
  expect(screen.getByLabelText('桌宠大小')).toHaveValue('96')
})
