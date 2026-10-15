import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test } from 'vitest'
import { CompanionPage } from './CompanionPage'

afterEach(() => {
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
