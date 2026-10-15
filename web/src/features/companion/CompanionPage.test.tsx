import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { CompanionPage } from './CompanionPage'

beforeEach(() => vi.stubGlobal('fetch', async () => Response.json(null)))

afterEach(() => {
  vi.unstubAllGlobals()
  delete window.__TAURI__
})

test('tray new-conversation intent survives a newly created companion window', async () => {
  window.__TAURI__ = {
    core: {
      invoke: async (command) => {
        if (command === 'companion_snapshot')
          return { revision: 0, phase: 'idle', cid: null, message: '', count: 0 }
        if (command === 'companion_settings')
          return { enabled: true, visible: true, height: 96, alwaysOnTop: true }
        if (command === 'companion_take_compose') return true
      },
    },
    event: { listen: async () => () => {} },
  }
  render(
    <MemoryRouter>
      <CompanionPage />
    </MemoryRouter>
  )
  expect(await screen.findByRole('textbox', { name: '快速对话内容' })).toBeVisible()
})

test('failed quick conversation preserves editable draft', async () => {
  window.__TAURI__ = {
    core: {
      invoke: async (command) => {
        if (command === 'companion_snapshot')
          return { revision: 0, phase: 'idle', cid: null, message: '', count: 0 }
        if (command === 'companion_settings')
          return { enabled: true, visible: true, height: 96, alwaysOnTop: true }
        if (command === 'companion_submit') return { status: 'failed', error: '连接失败' }
        return false
      },
    },
    event: { listen: async () => () => {} },
  }
  render(
    <MemoryRouter>
      <CompanionPage />
    </MemoryRouter>
  )
  fireEvent.click(screen.getByRole('button', { name: '打开桌宠快捷操作' }))
  fireEvent.click(screen.getByRole('button', { name: '新对话' }))
  const input = screen.getByRole('textbox')
  fireEvent.change(input, { target: { value: '别丢掉这句话' } })
  fireEvent.submit(input.closest('form')!)
  expect(await screen.findByRole('alert')).toHaveTextContent('连接失败')
  await waitFor(() => expect(input).toBeEnabled())
  expect(input).toHaveValue('别丢掉这句话')
})

test('switches the independent pet to standing form without changing the configured height', async () => {
  let settings = { enabled: true, visible: true, height: 96, alwaysOnTop: true, form: 'chibi' }
  window.__TAURI__ = {
    core: {
      invoke: async (command, args) => {
        if (command === 'companion_snapshot')
          return { revision: 0, phase: 'idle', cid: null, message: '', count: 0 }
        if (command === 'companion_settings') return settings
        if (command === 'companion_set_form') {
          settings = { ...settings, form: String(args?.form) }
          return settings
        }
        return false
      },
    },
    event: { listen: async () => () => {} },
  }
  const view = render(
    <MemoryRouter>
      <CompanionPage />
    </MemoryRouter>
  )
  fireEvent.click(screen.getByRole('button', { name: '打开桌宠快捷操作' }))
  fireEvent.click(screen.getByRole('button', { name: '切换桌宠形态' }))
  await waitFor(() =>
    expect(view.container.querySelector('.pet-avatar img')).toHaveAttribute(
      'src',
      '/companion/standing.png'
    )
  )
  expect(view.container.querySelector('.companion-surface')).toHaveStyle({ '--pet-height': '96px' })
})
