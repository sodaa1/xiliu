import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { CompanionPage } from './CompanionPage'

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('fetch', async () => Response.json(null))
})

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
  fireEvent.click(screen.getByRole('button', { name: '新对话' }))
  const input = screen.getByRole('textbox')
  fireEvent.change(input, { target: { value: '别丢掉这句话' } })
  fireEvent.submit(input.closest('form')!)
  expect(await screen.findByRole('alert')).toHaveTextContent('连接失败')
  await waitFor(() => expect(input).toBeEnabled())
  expect(input).toHaveValue('别丢掉这句话')
})

test('switches to the larger standing form using its own saved scale', async () => {
  let settings = {
    enabled: true,
    visible: true,
    height: 96,
    alwaysOnTop: true,
    form: 'chibi',
    chibiScale: 125,
    standingScale: 150,
  }
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
  fireEvent.click(screen.getByRole('button', { name: '更多桌宠操作' }))
  fireEvent.click(screen.getByRole('button', { name: '切换桌宠形态' }))
  await waitFor(() =>
    expect(view.container.querySelector('.pet-avatar img')).toHaveAttribute(
      'src',
      '/companion/standing.png'
    )
  )
  expect(view.container.querySelector('.companion-surface')).toHaveStyle({
    '--pet-height': '252px',
  })
})

test('compact composer keeps its draft when dismissed and has icon-only controls', () => {
  render(
    <MemoryRouter>
      <CompanionPage />
    </MemoryRouter>
  )
  const chat = screen.getByRole('button', { name: '新对话' })
  expect(chat.textContent).toBe('')
  expect(screen.getByRole('button', { name: '收进 Inbox' }).textContent).toBe('')
  fireEvent.click(chat)
  const input = screen.getByRole('textbox', { name: '快速对话内容' })
  expect(input).toHaveAttribute('placeholder', '开始新聊天')
  fireEvent.change(input, { target: { value: '保留草稿' } })
  fireEvent.keyDown(input, { key: 'Escape' })
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '新对话' }))
  expect(screen.getByRole('textbox')).toHaveValue('保留草稿')
  expect(screen.getByRole('button', { name: '发送新对话' }).textContent).toBe('')
})

test('native drag feedback lasts until the OS releases the drag and does not open chat', async () => {
  let finish!: () => void
  const drag = new Promise<void>((resolve) => {
    finish = resolve
  })
  window.__TAURI__ = {
    core: {
      invoke: async (command) => {
        if (command === 'companion_drag') return drag
        if (command === 'companion_snapshot')
          return { revision: 0, phase: 'idle', cid: null, message: '', count: 0 }
        if (command === 'companion_settings')
          return {
            enabled: true,
            visible: true,
            height: 96,
            alwaysOnTop: true,
            form: 'chibi',
            chibiScale: 100,
            standingScale: 100,
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
  const pet = screen.getByRole('button', { name: '打开桌宠快捷操作' })
  fireEvent(
    pet,
    new MouseEvent('pointerdown', {
      bubbles: true,
      button: 0,
      buttons: 1,
      clientX: 50,
      clientY: 50,
    })
  )
  fireEvent(
    pet,
    new MouseEvent('pointermove', { bubbles: true, buttons: 1, clientX: 80, clientY: 60 })
  )
  expect(view.container.querySelector('.companion-stage')).toHaveAttribute('data-dragging', 'true')
  fireEvent(pet, new MouseEvent('pointercancel', { bubbles: true }))
  expect(view.container.querySelector('.companion-stage')).toHaveAttribute('data-dragging', 'true')
  finish()
  await waitFor(() =>
    expect(view.container.querySelector('.companion-stage')).toHaveAttribute(
      'data-dragging',
      'false'
    )
  )
  fireEvent.click(pet, { detail: 1 })
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
})
