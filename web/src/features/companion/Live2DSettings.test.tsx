import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
test('native pet settings keep independent form scales across form switches', async () => {
  let settings = {
    enabled: true,
    visible: true,
    height: 96,
    alwaysOnTop: true,
    form: 'chibi',
    chibiScale: 100,
    standingScale: 100,
  }
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
  fireEvent.click(screen.getByRole('button', { name: '常规比例 150%' }))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: '常规比例 150%' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  )
  fireEvent.click(screen.getByRole('button', { name: 'Q 版 125%' }))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Q 版 125%' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  )
  fireEvent.change(screen.getByLabelText('桌宠形态'), { target: { value: 'chibi' } })
  await waitFor(() => expect(screen.getByLabelText('桌宠形态')).toHaveValue('chibi'))
  expect(screen.getByRole('button', { name: '常规比例 150%' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  expect(screen.getByRole('button', { name: 'Q 版 125%' })).toHaveAttribute('aria-pressed', 'true')
})

test('browser preview restores both scale choices after settings remount', async () => {
  localStorage.clear()
  const view = render(<CompanionSettings />)
  fireEvent.click(screen.getByRole('button', { name: 'Q 版 125%' }))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Q 版 125%' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  )
  fireEvent.click(screen.getByRole('button', { name: '常规比例 175%' }))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: '常规比例 175%' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  )
  view.unmount()
  render(<CompanionSettings />)
  expect(screen.getByRole('button', { name: 'Q 版 125%' })).toHaveAttribute('aria-pressed', 'true')
  expect(screen.getByRole('button', { name: '常规比例 175%' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  localStorage.clear()
})

test('settings follow pet form changes from another window before saving a scale', async () => {
  let settings = {
    enabled: true,
    visible: true,
    height: 96,
    alwaysOnTop: true,
    form: 'chibi',
    chibiScale: 100,
    standingScale: 100,
  }
  let notify: (event: { payload: unknown }) => void = () => {}
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
    event: {
      listen: async (_name, callback) => {
        notify = (event) => callback({ payload: event.payload as never })
        return () => {}
      },
    },
  }
  render(<CompanionSettings />)
  await screen.findByLabelText('桌宠形态')
  settings = { ...settings, form: 'standing', height: 168, visible: false }
  act(() => notify({ payload: settings }))
  expect(screen.getByLabelText('桌宠形态')).toHaveValue('standing')
  fireEvent.click(screen.getByRole('button', { name: '常规比例 150%' }))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: '常规比例 150%' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
  )
  expect(screen.getByLabelText('桌宠形态')).toHaveValue('standing')
  expect(settings.visible).toBe(false)
})
