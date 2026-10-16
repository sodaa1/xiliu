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
import type { ModelCatalog, ModelConnection, ModelSettings } from '../../lib/types'
import { workspaceApi } from '../../lib/workspace-api'
import { GlideSelect } from '../../components/GlideSelect'
import { PersonalSettings } from './PersonalSettings'
import { AppearanceSettings } from './AppearanceSettings'
import { AutomationsPanel } from '../automations/AutomationsDrawer'
import './settings.css'
import { CompanionSettings } from '../companion/CompanionSettings'
import { isDemo } from '../../lib/runtime-mode'
import { DemoNotice } from '../demo/DemoNotice'

function ModelForm({
  settings,
  catalog,
  connection,
}: {
  settings: ModelSettings
  catalog: ModelCatalog
  connection?: ModelConnection
}) {
  const cache = useQueryClient()
  const [provider, setProvider] = useState(connection?.provider ?? settings.provider),
    [model, setModel] = useState(connection?.model ?? settings.model)
  const [label, setLabel] = useState(connection?.label ?? '')
  const [address, setAddress] = useState(connection?.base_url ?? settings.base_url),
    [key, setKey] = useState('')
  const keySet =
    connection?.api_key_set ??
    settings.profiles?.[provider]?.api_key_set ??
    (provider === settings.provider && settings.api_key_set)
  const save = useMutation({
    mutationFn: () =>
      api.saveSettings({
        provider,
        model,
        base_url: address,
        api_key: key,
        ...(connection
          ? { ...(connection.id ? { profile_id: connection.id } : {}), label, make_default: false }
          : {}),
      }),
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
          <p>
            {connection
              ? '独立保存此连接，可在对话中随时选择。'
              : '默认用于新对话，也可在 Assistant 中单独选择。'}
          </p>
        </div>
      </div>
      <div className="settings-grid">
        <label>
          Provider
          {connection ? (
            <input
              value={
                provider === 'mimo'
                  ? '小米 MiMo'
                  : provider === 'custom'
                    ? '自定义接口'
                    : provider === 'openai'
                      ? 'OpenAI'
                      : 'DeepSeek'
              }
              readOnly
            />
          ) : (
            <GlideSelect
              ariaLabel="Provider"
              value={provider}
              options={Object.keys(catalog).map((value) => ({
                value,
                label:
                  value === 'openai'
                    ? 'OpenAI'
                    : value === 'deepseek'
                      ? 'DeepSeek'
                      : value === 'mimo'
                        ? '小米 MiMo'
                        : '自定义接口',
              }))}
              onChange={(value) => {
                const selected = value as ModelSettings['provider']
                const profile = settings.profiles?.[selected]
                setProvider(selected)
                setModel(profile?.model ?? catalog[selected].models[0])
                setAddress(profile?.base_url ?? catalog[selected].base_url)
                setKey('')
                save.reset()
              }}
            />
          )}
        </label>
        <label>
          Model
          {connection ? (
            <input
              required
              value={model}
              readOnly={!!connection.id}
              onChange={(event) => setModel(event.target.value)}
              placeholder="接口中的模型 ID"
            />
          ) : (
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
          )}
        </label>
        {connection && (
          <label className="full-width">
            显示名称
            <input
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              placeholder="例如：我的研究模型"
            />
          </label>
        )}
        <label className="full-width">
          API Key
          <div className="key-input">
            <KeyRound size={16} />
            <input
              type="password"
              aria-label="API Key"
              autoComplete="new-password"
              spellCheck={false}
              value={key}
              placeholder={keySet ? '已配置 · 留空保留已有密钥' : '输入 API Key'}
              onChange={(event) => setKey(event.target.value)}
            />
          </div>
          <small>
            {keySet ? '已有密钥仅保存在本机，不会返回浏览器。' : '密钥仅保存在本机配置文件。'}
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
          {provider === 'mimo' && (
            <small>普通 API 使用 api.xiaomimimo.com；Token Plan 请填写账户提供的专属地址。</small>
          )}
        </label>
      </div>
      <div className="settings-save">
        {save.isError && <span role="alert">{save.error.message}</span>}
        {save.isSuccess && (
          <span className="saved" role="status">
            <Check size={16} />
            已保存，可在对话中选择
          </span>
        )}
        <button className="primary-button" disabled={save.isPending}>
          {save.isPending ? '保存中…' : '保存设置'}
        </button>
      </div>
    </form>
  )
}
function ConnectionsPanel({
  settings,
  catalog,
}: {
  settings: ModelSettings
  catalog: ModelCatalog
}) {
  const [params] = useSearchParams()
  const connections = settings.connections ?? []
  const [editing, setEditing] = useState(
    () => connections.find((c) => c.provider === params.get('configure'))?.id ?? ''
  )
  const cache = useQueryClient()
  const makeDefault = useMutation({
    mutationFn: (connection: ModelConnection) =>
      api.saveSettings({
        provider: connection.provider,
        model: connection.model,
        base_url: connection.base_url,
        profile_id: connection.id,
        label: connection.label,
        api_key: '',
      }),
    onSuccess: (updated) => cache.setQueryData(['model-settings'], updated),
  })
  const toggle = useMutation({
    mutationFn: (item: ModelConnection) =>
      api.saveSettings({
        provider: item.provider,
        model: item.model,
        base_url: item.base_url,
        profile_id: item.id,
        label: item.label,
        api_key: '',
        make_default: false,
        enabled: item.enabled === false,
      }),
    onSuccess: (updated) => cache.setQueryData(['model-settings'], updated),
  })
  const isDefault = (item: ModelConnection) =>
    item.provider === settings.provider &&
    item.model === settings.model &&
    item.base_url === settings.base_url
  const renderConnection = (item: ModelConnection) => (
    <div className="connection-row" key={item.id}>
      <button
        type="button"
        className="connection-edit"
        aria-label={`编辑 ${item.label}`}
        aria-expanded={editing === item.id}
        onClick={() => setEditing(item.id)}
      >
        <span>
          <strong>{names[item.provider]}</strong>
          <span>{item.label}</span>
        </span>
        <small>{isDefault(item) ? '默认' : item.api_key_set ? '已配置' : '未配置'}</small>
      </button>
      <button
        type="button"
        role="switch"
        aria-checked={item.enabled !== false}
        aria-label={`启用 ${item.label}`}
        className="secondary-button"
        title={isDefault(item) ? '请先更换默认模型，再停用' : '停用后隐藏，保留密钥和配置'}
        disabled={isDefault(item) || toggle.isPending}
        onClick={() => toggle.mutate(item)}
      >
        {item.enabled === false ? '已停用' : '已启用'}
      </button>
      <button
        type="button"
        className="secondary-button"
        disabled={!item.api_key_set || item.enabled === false || makeDefault.isPending}
        onClick={() => makeDefault.mutate(item)}
        aria-label={`设为默认 ${item.label}`}
      >
        设为默认
      </button>
    </div>
  )
  const connection =
    editing === 'new'
      ? {
          id: '',
          provider: 'custom' as const,
          model: '',
          base_url: '',
          label: '',
          api_key_set: false,
        }
      : connections.find((c) => c.id === editing)
  const names = { openai: 'OpenAI', deepseek: 'DeepSeek', mimo: '小米 MiMo', custom: '自定义接口' }
  return (
    <>
      <section className="settings-card connection-list">
        <div className="card-title">
          <SlidersHorizontal size={20} />
          <div>
            <h2>模型与连接</h2>
            <p>每个模型独立保存密钥和地址，切换不会覆盖其他连接。</p>
          </div>
        </div>
        {connections.filter((item) => item.enabled !== false).map(renderConnection)}
        {connections.some((item) => item.enabled === false) && (
          <details className="disabled-connections">
            <summary>
              已停用（{connections.filter((item) => item.enabled === false).length}）
            </summary>
            {connections.filter((item) => item.enabled === false).map(renderConnection)}
          </details>
        )}
        <button
          type="button"
          className="secondary-button add-connection"
          onClick={() => setEditing('new')}
        >
          添加其他模型接口
        </button>
        {makeDefault.isError && <p role="alert">{makeDefault.error.message}</p>}
        {toggle.isError && <p role="alert">{toggle.error.message}</p>}
        <p className="settings-hint">
          密钥只保存到本机配置文件，不返回浏览器，不保存到浏览器缓存。
        </p>
      </section>
      {connection && (
        <ModelForm key={editing} settings={settings} catalog={catalog} connection={connection} />
      )}
    </>
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
  if (isDemo)
    return (
      <DemoNotice title="本地演示模板" guide="models">
        这里不调用真实模型，也不接收 API Key。安装或运行正常应用后，可配置自己的模型连接。
      </DemoNotice>
    )
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
    settings.data.connections?.length ? (
      <ConnectionsPanel settings={settings.data} catalog={catalog.data} />
    ) : (
      <ModelForm settings={settings.data} catalog={catalog.data} />
    )
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
        {current.id === 'appearance' && (
          <>
            <AppearanceSettings />
            {isDemo ? (
              <DemoNotice title="桌面伴侣与 Live2D" guide="appearance-companion">
                演示版不创建原生桌宠窗口或导入模型。使用指南介绍了形态、缩放、快捷聊天与使用条件。
              </DemoNotice>
            ) : (
              <CompanionSettings />
            )}
          </>
        )}
        {current.id === 'model' && <ModelSettingsPanel />}
        {current.id === 'automations' && (
          <div className="settings-card">
            {isDemo ? (
              <DemoNotice title="自动任务与扩展" guide="automations-extensions">
                游客演示不执行后台任务或外部工具。正常应用可按时区设置计划，并查看运行结果。
              </DemoNotice>
            ) : (
              <AutomationsPanel />
            )}
          </div>
        )}
        {current.id === 'data' && <DataSettings />}
      </div>
    </section>
  )
}
