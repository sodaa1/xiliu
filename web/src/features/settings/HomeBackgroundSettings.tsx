import { useState } from 'react'
import { ImagePlus, Trash2 } from 'lucide-react'
import {
  BACKGROUND_ACCEPT,
  builtinBackground,
  importBackground,
  saveBackground,
  type HomeBackground,
} from '../today/background'
import { useHomeBackground } from '../today/useHomeBackground'
import { isDemo } from '../../lib/runtime-mode'
export function HomeBackgroundSettings() {
  const { settings, images, error: loadError } = useHomeBackground()
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [notice, setNotice] = useState('')
  async function perform(operation: () => Promise<void>) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await operation()
      setNotice('主页背景已保存')
    } catch (failure) {
      setError((failure as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const choose = (next: HomeBackground) => void perform(() => saveBackground(next))
  return (
    <section className="settings-card home-background-settings" aria-label="主页背景">
      <div className="card-title">
        <ImagePlus size={20} />
        <div>
          <h2>主页背景</h2>
          <p>只改变主页，角色与背景独立显示。</p>
        </div>
      </div>
      <div className="home-background-gallery">
        <button
          disabled={busy}
          aria-pressed={settings.mode === 'blank'}
          onClick={() => choose({ mode: 'blank', selected: null })}
        >
          <span className="home-background-blank" />
          纯色留白
        </button>
        <button
          disabled={busy}
          aria-pressed={settings.mode === 'builtin'}
          onClick={() => choose({ mode: 'builtin', selected: null })}
        >
          <img src={builtinBackground} alt="" />
          内置背景
        </button>
        {images.map((image) => (
          <div className="home-background-choice" key={image.id}>
            <button
              disabled={busy}
              aria-pressed={settings.mode === 'custom' && settings.selected === image.id}
              onClick={() => choose({ mode: 'custom', selected: image.id })}
            >
              <img src={image.url} alt="" />
              <span title={image.name}>{image.name}</span>
            </button>
            <button
              className="icon-button"
              disabled={busy}
              aria-label={`删除背景 ${image.name}`}
              onClick={() =>
                void perform(() =>
                  saveBackground(
                    settings.selected === image.id ? { mode: 'blank', selected: null } : settings,
                    undefined,
                    image.id
                  )
                )
              }
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>
      <label className="home-background-import">
        导入背景图片
        <input
          aria-label="导入主页背景"
          type="file"
          accept={BACKGROUND_ACCEPT}
          disabled={busy || isDemo}
          onChange={(event) => {
            const file = event.target.files?.[0]
            event.target.value = ''
            if (file) void perform(() => importBackground(file))
          }}
        />
      </label>
      <p className="settings-hint">
        {isDemo
          ? '演示提供内置与留白背景；自定义图片请在正常应用中导入。'
          : 'PNG、JPEG、WebP、GIF、AVIF、BMP · 最大 20 MiB · GIF 保留动画'}
      </p>
      {busy && <p role="status">正在读取并保存图片…</p>}
      {(error || loadError) && (
        <p role="alert" className="workspace-error">
          {error || loadError}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
    </section>
  )
}
