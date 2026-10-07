import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, KeyRound, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../../lib/api'
import type { ModelCatalog, ModelSettings } from '../../lib/types'

function ModelForm({ settings, catalog }: { settings: ModelSettings; catalog: ModelCatalog }) {
  const cache = useQueryClient()
  const [provider, setProvider] = useState(settings.provider),
    [model, setModel] = useState(settings.model)
  const [address, setAddress] = useState(settings.base_url),
    [key, setKey] = useState('')
  const save = useMutation({
    mutationFn: () => api.saveSettings({ provider, model, base_url: address, api_key: key }),
    onSuccess: async (updated) => {
      setKey('')
      cache.setQueryData(['model-settings'], updated)
      await cache.invalidateQueries({ queryKey: ['conversation'] })
    },
  })
  return (
    <form
      className="settings-card"
      onSubmit={(event) => {
        event.preventDefault()
        save.mutate()
      }}
    >
      <div className="card-title">
        <SlidersHorizontal size={20} />
        <div>
          <h2>模型接口</h2>
          <p>默认用于新对话，也可在 Assistant 中单独选择。</p>
        </div>
      </div>
      <div className="settings-grid">
        <label>
          Provider
          <select
            value={provider}
            onChange={(event) => {
              const value = event.target.value as ModelSettings['provider']
              setProvider(value)
              setModel(catalog[value].models[0])
              setAddress(catalog[value].base_url)
            }}
          >
            <option value="openai">OpenAI</option>
            <option value="deepseek">DeepSeek</option>
          </select>
        </label>
        <label>
          Model
          <select value={model} onChange={(event) => setModel(event.target.value)}>
            {!catalog[provider].models.includes(model) && (
              <option value={model}>{model}（现有配置）</option>
            )}
            {catalog[provider].models.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="full-width">
          API Key
          <div className="key-input">
            <KeyRound size={16} />
            <input
              type="password"
              autoComplete="new-password"
              value={key}
              placeholder={settings.api_key_set ? '已配置 · 留空保留已有密钥' : '输入 API Key'}
              onChange={(event) => setKey(event.target.value)}
            />
          </div>
          <small>
            {settings.api_key_set
              ? '已有密钥仅保存在本机，不会返回浏览器。'
              : '密钥仅保存在本机配置文件。'}
          </small>
        </label>
        <label className="full-width">
          Base URL
          <input
            type="url"
            required
            value={address}
            onChange={(event) => setAddress(event.target.value)}
          />
        </label>
      </div>
      <div className="settings-save">
        {save.isError && <span role="alert">{save.error.message}</span>}
        {save.isSuccess && (
          <span className="saved" role="status">
            <Check size={16} />
            已保存，下次对话生效
          </span>
        )}
        <button className="primary-button" disabled={save.isPending}>
          {save.isPending ? '保存中…' : '保存设置'}
        </button>
      </div>
    </form>
  )
}
export function SettingsPage() {
  const settings = useQuery({ queryKey: ['model-settings'], queryFn: api.settings })
  const catalog = useQuery({ queryKey: ['model-catalog'], queryFn: api.catalog })
  return (
    <section className="settings-page">
      <Link to="/assistant" className="back-link">
        <ArrowLeft size={17} />
        返回 Assistant
      </Link>
      <h1>Settings</h1>
      <p className="page-description">让息流以你习惯的方式工作。</p>
      {settings.error || catalog.error ? (
        <p role="alert">无法加载设置，请刷新重试。</p>
      ) : settings.data && catalog.data ? (
        <ModelForm settings={settings.data} catalog={catalog.data} />
      ) : (
        <p>正在加载设置…</p>
      )}
      <div className="settings-card appearance-card">
        <h2>外观</h2>
        <p>Light · 轻盈的浅色界面</p>
        <span className="appearance-swatch" aria-hidden="true" />
      </div>
    </section>
  )
}
