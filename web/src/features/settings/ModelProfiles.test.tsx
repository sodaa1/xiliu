import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { expect, test, vi } from 'vitest'
import { ModelSettingsPanel } from './SettingsPage'
import { ModelPicker } from '../assistant/ModelPicker'

test('disabled connections are hidden from picker and can be restored without sending a key', async () => {
  const connections = [
    {
      id: 'deepseek:deepseek-v4-flash',
      label: 'Flash',
      provider: 'deepseek' as const,
      model: 'deepseek-v4-flash',
      base_url: 'https://api.deepseek.com',
      api_key_set: true,
    },
    {
      id: 'mimo:mimo-v2.6-pro',
      label: 'MiMo',
      provider: 'mimo' as const,
      model: 'mimo-v2.6-pro',
      base_url: 'https://api.xiaomimimo.com/v1',
      api_key_set: true,
      enabled: true,
    },
  ]
  const settings = { ...connections[0], connections }
  const writes: Record<string, unknown>[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'PUT') {
        const body = JSON.parse(String(init.body))
        writes.push(body)
        connections[1].enabled = body.enabled
      }
      return Response.json(url.includes('catalog') ? {} : settings)
    })
  )
  const view = render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <ModelSettingsPanel />
      </MemoryRouter>
    </QueryClientProvider>
  )
  const user = userEvent.setup()
  expect(await screen.findByRole('switch', { name: '启用 Flash' })).toBeDisabled()
  await user.click(screen.getByRole('switch', { name: '启用 MiMo' }))
  expect(await screen.findByText('已停用（1）')).toBeInTheDocument()
  await user.click(screen.getByText('已停用（1）'))
  expect(screen.getByRole('switch', { name: '启用 MiMo' })).not.toBeChecked()
  await user.click(screen.getByRole('switch', { name: '启用 MiMo' }))
  expect(await screen.findByRole('switch', { name: '启用 MiMo' })).toBeChecked()
  expect(writes.map((w) => w.enabled)).toEqual([false, true])
  expect(writes.every((w) => w.api_key === '' && w.make_default === false)).toBe(true)
  view.unmount()
  render(
    <ModelPicker
      value=""
      defaultModel="Flash"
      models={[]}
      connections={[connections[0], { ...connections[1], enabled: false }]}
      selectionDisabled={false}
      onChange={() => {}}
      onConfigure={() => {}}
    />
  )
  await user.click(screen.getByRole('combobox'))
  expect(screen.queryByRole('option', { name: /MiMo/ })).not.toBeInTheDocument()
})

test('switching providers isolates key draft and restores saved profile fields', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) =>
      Response.json(
        url.includes('catalog')
          ? {
              deepseek: { models: ['deepseek-v4-flash'], base_url: 'https://api.deepseek.com' },
              openai: { models: ['gpt-5.6-terra'], base_url: 'https://api.openai.com/v1' },
            }
          : {
              provider: 'deepseek',
              model: 'deepseek-v4-flash',
              base_url: 'https://api.deepseek.com',
              api_key_set: true,
              profiles: {
                deepseek: {
                  model: 'deepseek-v4-flash',
                  base_url: 'https://api.deepseek.com',
                  api_key_set: true,
                },
                openai: {
                  model: 'gpt-5.6-terra',
                  base_url: 'https://saved.example.test/v1',
                  api_key_set: false,
                },
              },
            }
      )
    )
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <ModelSettingsPanel />
      </MemoryRouter>
    </QueryClientProvider>
  )
  const user = userEvent.setup()
  const key = await screen.findByPlaceholderText('已配置 · 留空保留已有密钥')
  await user.type(key, 'unsaved-test-secret')
  await user.click(screen.getByRole('combobox', { name: 'Provider' }))
  await user.click(screen.getByRole('option', { name: 'OpenAI' }))
  expect(key).toHaveValue('')
  expect(key).toHaveAttribute('placeholder', '输入 API Key')
  expect(screen.getByLabelText('Base URL')).toHaveValue('https://saved.example.test/v1')
  await user.click(screen.getByRole('combobox', { name: 'Provider' }))
  await user.click(screen.getByRole('option', { name: 'DeepSeek' }))
  expect(key).toHaveAttribute('placeholder', '已配置 · 留空保留已有密钥')
})

test('model picker offers configured connections across providers without saving global settings', async () => {
  const changed = vi.fn()
  render(
    <ModelPicker
      value=""
      defaultModel="deepseek-v4-flash"
      models={[]}
      connections={[
        {
          id: 'openai:gpt-5.6-sol',
          label: 'gpt-5.6-sol',
          provider: 'openai',
          model: 'gpt-5.6-sol',
          base_url: 'https://api.openai.com/v1',
          api_key_set: true,
        },
        {
          id: 'mimo:mimo-v2.6-pro',
          label: 'mimo-v2.6-pro',
          provider: 'mimo',
          model: 'mimo-v2.6-pro',
          base_url: 'https://api.xiaomimimo.com/v1',
          api_key_set: true,
        },
      ]}
      selectionDisabled={false}
      onChange={changed}
      onConfigure={() => {}}
    />
  )
  await userEvent.click(screen.getByRole('combobox'))
  await userEvent.click(screen.getByRole('option', { name: /MiMo.*mimo-v2.6-pro/ }))
  expect(changed).toHaveBeenCalledWith('mimo:mimo-v2.6-pro')
  expect(screen.queryByText('API Key')).not.toBeInTheDocument()
})

test('connections panel opens MiMo password form and saves only its connection', async () => {
  const connections = [
    {
      id: 'deepseek:deepseek-v4-flash',
      label: 'deepseek-v4-flash',
      provider: 'deepseek',
      model: 'deepseek-v4-flash',
      base_url: 'https://api.deepseek.com',
      api_key_set: true,
    },
    {
      id: 'mimo:mimo-v2.6-pro',
      label: 'mimo-v2.6-pro',
      provider: 'mimo',
      model: 'mimo-v2.6-pro',
      base_url: 'https://api.xiaomimimo.com/v1',
      api_key_set: false,
    },
  ]
  const saved: unknown[] = []
  const settings = {
    provider: 'deepseek',
    model: 'deepseek-v4-flash',
    base_url: 'https://api.deepseek.com',
    api_key_set: true,
    connections,
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options?: RequestInit) => {
      if (options?.method === 'PUT') saved.push(JSON.parse(String(options.body)))
      return Response.json(
        url.includes('catalog')
          ? {
              deepseek: { models: ['deepseek-v4-flash'], base_url: 'https://api.deepseek.com' },
              mimo: { models: ['mimo-v2.6-pro'], base_url: 'https://api.xiaomimimo.com/v1' },
              custom: { models: [], base_url: '' },
            }
          : settings
      )
    })
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <ModelSettingsPanel />
      </MemoryRouter>
    </QueryClientProvider>
  )
  await userEvent.click(await screen.findByRole('button', { name: '编辑 mimo-v2.6-pro' }))
  const key = screen.getByPlaceholderText('输入 API Key')
  expect(screen.getByText(/普通 API 使用 api.xiaomimimo.com/)).toBeVisible()
  expect(key).toHaveAttribute('type', 'password')
  await userEvent.type(key, 'mimo-test-only')
  await userEvent.click(screen.getByRole('button', { name: '保存设置' }))
  expect(saved).toEqual([
    {
      provider: 'mimo',
      model: 'mimo-v2.6-pro',
      base_url: 'https://api.xiaomimimo.com/v1',
      api_key: 'mimo-test-only',
      profile_id: 'mimo:mimo-v2.6-pro',
      label: 'mimo-v2.6-pro',
      make_default: false,
    },
  ])
})

test('custom interface draft saves an independent model and key', async () => {
  const saved: unknown[] = []
  const settings = {
    provider: 'deepseek',
    model: 'deepseek-v4-flash',
    base_url: 'https://api.deepseek.com',
    api_key_set: true,
    connections: [
      {
        id: 'deepseek:deepseek-v4-flash',
        label: 'deepseek-v4-flash',
        provider: 'deepseek',
        model: 'deepseek-v4-flash',
        base_url: 'https://api.deepseek.com',
        api_key_set: true,
      },
    ],
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options?: RequestInit) => {
      if (options?.method === 'PUT') saved.push(JSON.parse(String(options.body)))
      return Response.json(
        url.includes('catalog') ? { custom: { models: [], base_url: '' } } : settings
      )
    })
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <ModelSettingsPanel />
      </MemoryRouter>
    </QueryClientProvider>
  )
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: '添加其他模型接口' }))
  await user.type(screen.getByLabelText('Model'), 'private-research-model')
  await user.type(screen.getByLabelText('显示名称'), '研究接口')
  await user.type(screen.getByLabelText('Base URL'), 'https://private.example.test/v1')
  await user.type(screen.getByLabelText('API Key'), 'custom-test-only')
  await user.click(screen.getByRole('button', { name: '保存设置' }))
  expect(saved).toEqual([
    {
      provider: 'custom',
      model: 'private-research-model',
      label: '研究接口',
      base_url: 'https://private.example.test/v1',
      api_key: 'custom-test-only',
      make_default: false,
    },
  ])
})

test('default selection respects configuration and sends no stored key', async () => {
  const saved: unknown[] = []
  const settings = {
    provider: 'deepseek',
    model: 'deepseek-v4-flash',
    base_url: 'https://api.deepseek.com',
    api_key_set: true,
    connections: [
      {
        id: 'deepseek:deepseek-v4-flash',
        label: 'deepseek-v4-flash',
        provider: 'deepseek',
        model: 'deepseek-v4-flash',
        base_url: 'https://api.deepseek.com',
        api_key_set: true,
      },
      {
        id: 'mimo:mimo-v2.6-pro',
        label: 'mimo-v2.6-pro',
        provider: 'mimo',
        model: 'mimo-v2.6-pro',
        base_url: 'https://api.xiaomimimo.com/v1',
        api_key_set: false,
      },
    ],
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options?: RequestInit) => {
      if (options?.method === 'PUT') saved.push(JSON.parse(String(options.body)))
      return Response.json(url.includes('catalog') ? {} : settings)
    })
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <ModelSettingsPanel />
      </MemoryRouter>
    </QueryClientProvider>
  )
  expect(await screen.findByRole('button', { name: '设为默认 mimo-v2.6-pro' })).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: '设为默认 deepseek-v4-flash' }))
  expect(saved).toEqual([
    {
      provider: 'deepseek',
      model: 'deepseek-v4-flash',
      base_url: 'https://api.deepseek.com',
      profile_id: 'deepseek:deepseek-v4-flash',
      label: 'deepseek-v4-flash',
      api_key: '',
    },
  ])
})

test('legacy bare model override displays its saved connection', () => {
  render(
    <ModelPicker
      value="deepseek-v4-pro"
      defaultModel="deepseek-v4-flash"
      provider="deepseek"
      models={[]}
      connections={[
        {
          id: 'deepseek:deepseek-v4-pro',
          label: '独立 Pro',
          provider: 'deepseek',
          model: 'deepseek-v4-pro',
          base_url: 'https://pro.example.test/v1',
          api_key_set: true,
        },
      ]}
      selectionDisabled={false}
      onChange={() => {}}
      onConfigure={() => {}}
    />
  )
  expect(screen.getByRole('combobox')).toHaveTextContent('DeepSeek · 独立 Pro')
})
