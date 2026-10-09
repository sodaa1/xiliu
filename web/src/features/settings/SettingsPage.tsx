import { useState, type CSSProperties } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Check,
  KeyRound,
  SlidersHorizontal,
  Database,
  UserRound,
  Palette,
  Clock3,
  Copy,
} from 'lucide-react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { api } from '../../lib/api'
import type { ModelCatalog, ModelSettings } from '../../lib/types'
import { workspaceApi } from '../../lib/workspace-api'
import { GlideSelect } from '../../components/GlideSelect'
import { PersonalSettings } from './PersonalSettings'
import { AppearanceSettings } from './AppearanceSettings'
import { AutomationsPanel } from '../automations/AutomationsDrawer'
import './settings.css'

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
          <GlideSelect
            ariaLabel="Provider"
            value={provider}
            options={Object.keys(catalog).map((value) => ({
              value,
              label: value === 'openai' ? 'OpenAI' : 'DeepSeek',
            }))}
            onChange={(value) => {
              const selected = value as ModelSettings['provider']
              setProvider(selected)
              setModel(catalog[selected].models[0])
              setAddress(catalog[selected].base_url)
              save.reset()
            }}
          />
        </label>
        <label>
          Model
          <GlideSelect
            ariaLabel="Model"
            value={model}
            menuWidth={290}
            options={[...new Set([model, ...catalog[provider].models])].map((value) => ({
              value,
              label: value,
            }))}
            onChange={(value) => {
              setModel(value)
              save.reset()
            }}
          />
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
const sections = [
  { id: 'profile', label: '个人信息', icon: UserRound },
  { id: 'appearance', label: '外观', icon: Palette },
  { id: 'model', label: '模型与连接', icon: SlidersHorizontal },
  { id: 'automations', label: '自动化', icon: Clock3 },
  { id: 'data', label: '数据与存储', icon: Database },
]
export function ModelSettingsPanel() {
  const settings = useQuery({ queryKey: ['model-settings'], queryFn: api.settings })
  const catalog = useQuery({ queryKey: ['model-catalog'], queryFn: api.catalog })
  if (settings.error || catalog.error)
    return (
      <div className="workspace-error" role="alert">
        无法加载模型设置。
        <button
          className="secondary-button"
          onClick={() => {
            void settings.refetch()
            void catalog.refetch()
          }}
        >
          重新加载
        </button>
      </div>
    )
  return settings.data && catalog.data ? (
    <ModelForm settings={settings.data} catalog={catalog.data} />
  ) : (
    <p className="settings-hint" role="status">
      正在加载模型设置…
    </p>
  )
}
function DataSettings() {
  const data = useQuery({ queryKey: ['data-settings'], queryFn: workspaceApi.dataSettings })
  const [notice, setNotice] = useState('')
  return (
    <section className="settings-card data-settings">
      <div className="card-title">
        <Database size={20} />
        <div>
          <h2>数据与存储</h2>
          <p>你的内容、原文件与模型配置保存在本机。</p>
        </div>
      </div>
      {data.isLoading ? (
        <p className="settings-hint">正在加载存储信息…</p>
      ) : data.error ? (
        <div className="workspace-error" role="alert">
          {data.error.message}
          <button className="secondary-button" onClick={() => void data.refetch()}>
            重新加载
          </button>
        </div>
      ) : (
        data.data && (
          <>
            <dl>
              <div>
                <dt>数据位置</dt>
                <dd>{data.data.data_dir}</dd>
              </div>
              <div>
                <dt>数据库</dt>
                <dd>
                  {data.data.database}
                  <span className="database-status">已连接</span>
                </dd>
              </div>
              <div>
                <dt>收藏内容</dt>
                <dd>{data.data.content_count} 项</dd>
              </div>
              <div>
                <dt>自动任务调度</dt>
                <dd>{data.data.scheduler_active ? '正在运行' : '尚未运行'}</dd>
              </div>
            </dl>
            <button
              className="secondary-button copy-data-path"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(data.data!.data_dir)
                  setNotice('数据位置已复制')
                } catch {
                  setNotice('无法自动复制，请选中上方路径手动复制。')
                }
              }}
            >
              <Copy size={14} />
              复制数据位置
            </button>
            {notice && (
              <p className="settings-hint" role="status">
                {notice}
              </p>
            )}
          </>
        )
      )}
      <p className="settings-hint">
        网页版将个人资料与外观偏好保存在当前浏览器，清除浏览器数据会重置偏好；桌面版另存本机备份，重启后恢复。以上操作不会删除内容数据库。
      </p>
      <div className="settings-about">
        <strong>xiliu · 息流</strong>
        <span>v0.1</span>
        <p>属于你的信息空间。</p>
      </div>
    </section>
  )
}
export function SettingsPage({ embedded = false }: { embedded?: boolean }) {
  const location = useLocation()
  const [params, setParams] = useSearchParams()
  const index = Math.max(
    0,
    sections.findIndex((item) => item.id === params.get('section'))
  )
  const current = sections[index]
  function select(value: number) {
    setParams({ section: sections[value].id }, { replace: true, state: location.state })
  }
  return (
    <section className="settings-page">
      {!embedded && (
        <Link to="/assistant" className="back-link">
          <ArrowLeft size={17} />
          返回 Assistant
        </Link>
      )}
      {!embedded && (
        <header className="settings-heading">
          <h1>Settings</h1>
          <p className="page-description">让息流以你习惯的方式工作。</p>
          <span className="settings-local-label">本机设置</span>
        </header>
      )}
      <div
        className="settings-section-tabs"
        role="tablist"
        aria-label="设置分类"
        style={{ '--settings-index': index } as CSSProperties}
      >
        <span className="settings-tab-highlight" aria-hidden="true" />
        {sections.map(({ id, label, icon: Icon }, position) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`settings-tab-${id}`}
            aria-selected={position === index}
            aria-controls={`settings-panel-${id}`}
            tabIndex={position === index ? 0 : -1}
            onClick={() => select(position)}
            onKeyDown={(event) => {
              const target =
                event.key === 'ArrowRight'
                  ? (index + 1) % sections.length
                  : event.key === 'ArrowLeft'
                    ? (index + sections.length - 1) % sections.length
                    : event.key === 'Home'
                      ? 0
                      : event.key === 'End'
                        ? sections.length - 1
                        : -1
              if (target >= 0) {
                event.preventDefault()
                select(target)
                document.getElementById(`settings-tab-${sections[target].id}`)?.focus()
              }
            }}
          >
            <Icon size={16} />
            <span>{label}</span>
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id={`settings-panel-${current.id}`}
        aria-labelledby={`settings-tab-${current.id}`}
        tabIndex={0}
        className="settings-panel"
      >
        {current.id === 'profile' && <PersonalSettings />}
        {current.id === 'appearance' && <AppearanceSettings />}
        {current.id === 'model' && <ModelSettingsPanel />}
        {current.id === 'automations' && (
          <div className="settings-card">
            <AutomationsPanel />
          </div>
        )}
        {current.id === 'data' && <DataSettings />}
      </div>
    </section>
  )
}
