import { useEffect, useState } from 'react'
import {
  companionCall,
  companionListen,
  PET_SCALES,
  petScale,
  previewSettings,
  savePreviewSettings,
  type CompanionSettings as Settings,
} from '../../desktop/companion'
import { isDesktop } from '../../desktop/bridge'
import './companion.css'

export function CompanionSettings() {
  const [settings, setSettings] = useState<Settings | null>(() =>
    isDesktop() ? null : previewSettings()
  )
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    let disposed = false
    let stop: (() => void) | undefined
    if (isDesktop()) {
      void companionCall<Settings>('settings')
        .then((value) => {
          if (!disposed) setSettings(value)
        })
        .catch((failure) => {
          if (!disposed) setError(String(failure))
        })
      if (window.__TAURI__?.event)
        void companionListen<Settings>('settings', (value) => {
          if (!disposed) setSettings(value)
        })
          .then((unlisten) => {
            if (disposed) unlisten()
            else stop = unlisten
          })
          .catch((failure) => {
            if (!disposed) setError(String(failure))
          })
    } else {
      const refresh = () => setSettings(previewSettings())
      window.addEventListener('storage', refresh)
      window.addEventListener('companion-preview-settings', refresh)
      stop = () => {
        window.removeEventListener('storage', refresh)
        window.removeEventListener('companion-preview-settings', refresh)
      }
    }
    return () => {
      disposed = true
      stop?.()
    }
  }, [])
  const save = async (patch: Partial<Settings>) => {
    if (!settings || saving) return
    setSaving(true)
    try {
      const current = isDesktop() ? await companionCall<Settings>('settings') : previewSettings()
      setSettings(
        isDesktop()
          ? await companionCall<Settings>('configure', { settings: { ...current, ...patch } })
          : savePreviewSettings({ ...current, ...patch })
      )
      setError('')
    } catch (error) {
      setError(String(error))
    } finally {
      setSaving(false)
    }
  }
  return (
    <section className="settings-card companion-controls" aria-label="桌宠设置">
      <div>
        <h2>桌面伴侣</h2>
        <p className="settings-hint">小小一只，随时开始对话或收进 Inbox。</p>
      </div>
      {settings && (
        <fieldset className="companion-settings-fields" disabled={saving}>
          {isDesktop() && (
            <label>
              启用常驻桌宠
              <input
                type="checkbox"
                checked={settings.enabled}
                onChange={(event) =>
                  void save({ enabled: event.target.checked, visible: event.target.checked })
                }
              />
            </label>
          )}
          <label>
            桌宠形态
            <select
              aria-label="桌宠形态"
              value={settings.form ?? 'chibi'}
              onChange={(event) => void save({ form: event.target.value as 'chibi' | 'standing' })}
            >
              <option value="chibi">Q 版</option>
              <option value="standing">常规比例</option>
            </select>
          </label>
          {isDesktop() && (
            <label>
              保持置顶
              <input
                type="checkbox"
                checked={settings.alwaysOnTop}
                onChange={(event) => void save({ alwaysOnTop: event.target.checked })}
              />
            </label>
          )}
          {(['chibi', 'standing'] as const).map((form) => {
            const label = form === 'chibi' ? 'Q 版' : '常规比例'
            const scale = petScale(settings, form)
            return (
              <div className="companion-scale" key={form}>
                <div>
                  <strong>{label}</strong>
                  <small>100% · {form === 'chibi' ? 96 : 168} px</small>
                </div>
                <div
                  className="companion-scale-options"
                  role="group"
                  aria-label={`${label}缩放比例`}
                >
                  {PET_SCALES.map((value) => (
                    <button
                      type="button"
                      key={value}
                      aria-label={`${label} ${value}%`}
                      aria-pressed={scale === value}
                      onClick={() =>
                        void save(
                          form === 'chibi' ? { chibiScale: value } : { standingScale: value }
                        )
                      }
                    >
                      {value}%
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
          <div>
            <button
              className="secondary-button"
              onClick={() =>
                void save({ chibiScale: 100, standingScale: 100, enabled: true, visible: true })
              }
            >
              恢复默认并显示
            </button>
          </div>
        </fieldset>
      )}
      {error && (
        <p role="alert" className="workspace-error">
          {error}
        </p>
      )}
    </section>
  )
}
