import { HomeThemeSwitch } from '../today/HomeThemeSwitch'
import { Live2DSettings } from '../companion/Live2DSettings'
import { HomeBackgroundSettings } from './HomeBackgroundSettings'
import { useState } from 'react'
import { isDemo } from '../../lib/runtime-mode'
import { Palette, RotateCcw } from 'lucide-react'
import { GlideSelect } from '../../components/GlideSelect'
import {
  defaultPreferences,
  savePreferences,
  usePreferences,
  type Preferences,
} from '../../lib/preferences'

export function AppearanceSettings() {
  const preferences = usePreferences(),
    [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [saving, setSaving] = useState(false)
  async function change(changes: Partial<Preferences>) {
    setSaving(true)
    setNotice('正在保存…')
    setError('')
    try {
      await savePreferences(changes)
      setError('')
      setNotice('已保存，立即生效')
    } catch (failure) {
      setError((failure as Error).message)
      setNotice('')
    } finally {
      setSaving(false)
    }
  }
  return (
    <>
      <section className="settings-card">
        <div className="card-title">
          <Palette size={20} />
          <div>
            <h2>外观与阅读</h2>
            <p>保留息流的轻盈，调整到适合你的节奏。</p>
          </div>
        </div>
        <div className="settings-grid">
          <div className="settings-field">
            <span>主题</span>
            <div className="settings-theme-options" role="radiogroup" aria-label="主题">
              {(
                [
                  ['light', '浅色模式'],
                  ['dark', '深色模式'],
                  ['system', '跟随系统'],
                ] as const
              ).map(([value, label], index, choices) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-label={label}
                  aria-checked={preferences.theme === value}
                  tabIndex={preferences.theme === value ? 0 : -1}
                  aria-disabled={saving}
                  onClick={() => {
                    if (!saving) void change({ theme: value })
                  }}
                  onKeyDown={(event) => {
                    const target =
                      event.key === 'ArrowRight' || event.key === 'ArrowDown'
                        ? (index + 1) % 3
                        : event.key === 'ArrowLeft' || event.key === 'ArrowUp'
                          ? (index + 2) % 3
                          : -1
                    if (target >= 0) {
                      event.preventDefault()
                      if (saving) return
                      const next = choices[target][0]
                      ;(event.currentTarget.parentElement?.children[target] as HTMLElement)?.focus()
                      void change({ theme: next })
                    }
                  }}
                >
                  <span className={`theme-option-preview theme-${value}`} aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="settings-field">
            <span>字体大小</span>
            <GlideSelect
              ariaLabel="字体大小"
              disabled={saving}
              value={preferences.fontSize}
              showTags
              options={[
                { value: 'small', label: '小', tag: '14 px · 默认' },
                { value: 'medium', label: '中', tag: '16 px' },
                { value: 'large', label: '大', tag: '18 px' },
              ]}
              onChange={(fontSize) => change({ fontSize: fontSize as Preferences['fontSize'] })}
            />
          </div>
          <div className="settings-field">
            <span>字体</span>
            <GlideSelect
              ariaLabel="字体"
              disabled={saving}
              value={preferences.fontFamily}
              showTags
              options={[
                { value: 'system', label: '默认字体', tag: '清晰' },
                { value: 'rounded', label: '系统字体', tag: '柔和' },
                { value: 'serif', label: '宋体', tag: '阅读' },
              ]}
              onChange={(fontFamily) =>
                change({ fontFamily: fontFamily as Preferences['fontFamily'] })
              }
            />
            <small>使用本机字体，无需联网下载。</small>
          </div>
          <div className="settings-field">
            <span>内容密度</span>
            <GlideSelect
              ariaLabel="内容密度"
              disabled={saving}
              value={preferences.density}
              options={[
                { value: 'comfortable', label: '舒适' },
                { value: 'compact', label: '紧凑' },
              ]}
              onChange={(density) => change({ density: density as Preferences['density'] })}
            />
          </div>
        </div>
        <div className="settings-toggle-row">
          <div>
            <strong>减少动态效果</strong>
            <p>关闭滑动与循环动画，专注内容。系统偏好也会生效。</p>
          </div>
          <button
            role="switch"
            disabled={saving}
            aria-label="减少动态效果"
            aria-checked={preferences.reducedMotion}
            className={`automation-switch ${preferences.reducedMotion ? 'enabled' : ''}`}
            onClick={() => change({ reducedMotion: !preferences.reducedMotion })}
          >
            <span />
          </button>
        </div>
        <div className="reading-preview">
          <span className="preview-label">阅读预览</span>
          <h3>百川归海，让灵感慢慢汇聚。</h3>
          <p>留住值得记下的发现，也为下一次思考留出空间。</p>
          <span className="preview-tag"># 灵感</span>
        </div>
        <div className="settings-save">
          {error && <span role="alert">{error}</span>}
          {notice && (
            <span className="saved" role="status">
              {notice}
            </span>
          )}
          <button
            className="secondary-button"
            disabled={saving}
            onClick={() =>
              change({
                theme: defaultPreferences.theme,
                fontSize: defaultPreferences.fontSize,
                fontFamily: defaultPreferences.fontFamily,
                density: defaultPreferences.density,
                reducedMotion: defaultPreferences.reducedMotion,
              })
            }
          >
            <RotateCcw size={14} />
            恢复默认外观
          </button>
        </div>
      </section>
      <section className="settings-card">
        <div className="card-title">
          <Palette size={20} />
          <div>
            <h2>首页主题</h2>
            <p>原有首页与山水工作台，随心切换。</p>
          </div>
        </div>
        <HomeThemeSwitch />
      </section>
      <HomeBackgroundSettings />
      {!isDemo && <Live2DSettings />}
    </>
  )
}
