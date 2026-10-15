import { useEffect, useState } from 'react'
import {
  companionCall,
  DEFAULT_PET_HEIGHT,
  type CompanionSettings as Settings,
} from '../../desktop/companion'
import { isDesktop } from '../../desktop/bridge'
import './companion.css'

export function CompanionSettings() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (isDesktop())
      void companionCall<Settings>('settings')
        .then(setSettings)
        .catch((error) => setError(String(error)))
  }, [])
  if (!isDesktop()) return null
  const save = async (patch: Partial<Settings>) => {
    try {
      setSettings(
        await companionCall<Settings>('configure', { settings: { ...settings, ...patch } })
      )
      setError('')
    } catch (error) {
      setError(String(error))
    }
  }
  return (
    <section className="settings-card companion-controls" aria-label="桌宠设置">
      <div>
        <h2>桌面伴侣</h2>
        <p className="settings-hint">小小一只，随时开始对话或收进 Inbox。</p>
      </div>
      {settings && (
        <>
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
          <label>
            保持置顶
            <input
              type="checkbox"
              checked={settings.alwaysOnTop}
              onChange={(event) => void save({ alwaysOnTop: event.target.checked })}
            />
          </label>
          <label>
            形象大小 · {settings.height} px
            <input
              aria-label="桌宠大小"
              type="range"
              min="72"
              max="128"
              step="8"
              value={settings.height}
              onChange={(event) => setSettings({ ...settings, height: Number(event.target.value) })}
              onPointerUp={() => void save({})}
              onKeyUp={() => void save({})}
            />
          </label>
          <div>
            <button
              className="secondary-button"
              onClick={() =>
                void save({ height: DEFAULT_PET_HEIGHT, enabled: true, visible: true })
              }
            >
              恢复默认并显示
            </button>
          </div>
        </>
      )}
      {error && (
        <p role="alert" className="workspace-error">
          {error}
        </p>
      )}
    </section>
  )
}
