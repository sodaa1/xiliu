import { useEffect, useState } from 'react'
import { collectModelBundle, type PetForm } from './live2d-bundle'
import { readModelInfo, saveModel, watchModels } from './model-storage'
import { PetAvatar } from './PetAvatar'
export function Live2DSettings() {
  const [form, setForm] = useState<PetForm>('chibi'),
    [name, setName] = useState(''),
    [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [busy, setBusy] = useState(false)
  const [revision, setRevision] = useState(0)
  useEffect(() => watchModels(() => setRevision((value) => value + 1)), [])
  useEffect(() => {
    let alive = true
    void readModelInfo(form)
      .then((bundle) => {
        if (alive) setName(bundle?.name ?? '')
      })
      .catch((failure) => {
        if (alive) setError((failure as Error).message)
      })
    return () => {
      alive = false
    }
  }, [form, revision])
  return (
    <section className="settings-card live2d-settings" aria-label="Live2D 模型">
      <h2>Live2D 形象</h2>
      <p className="settings-hint">Q 版和常规比例可分别配置。未导入模型时显示原角色图片。</p>
      <div className="segmented">
        <button
          disabled={busy}
          aria-pressed={form === 'chibi'}
          onClick={() => {
            setForm('chibi')
            setError('')
            setNotice('')
          }}
        >
          Q 版
        </button>
        <button
          disabled={busy}
          aria-pressed={form === 'standing'}
          onClick={() => {
            setForm('standing')
            setError('')
            setNotice('')
          }}
        >
          常规比例
        </button>
      </div>
      <div className="live2d-preview">
        <PetAvatar key={`${form}:${revision}`} form={form} onError={setError} />
      </div>
      <p>{name ? `已导入：${name}` : '当前使用角色图片'}</p>
      <label>
        导入 Live2D 模型文件夹
        <input
          aria-label="导入 Live2D 模型文件夹"
          type="file"
          multiple
          disabled={busy}
          {...{ webkitdirectory: '', directory: '' }}
          onChange={async (event) => {
            const files = Array.from(event.target.files ?? [])
            event.target.value = ''
            if (!files.length) return
            setBusy(true)
            setError('')
            setNotice('')
            try {
              const bundle = await collectModelBundle(form, files)
              await saveModel(form, bundle)
              setNotice('模型已保存，桌宠将自动更新。')
            } catch (failure) {
              setError((failure as Error).message)
            } finally {
              setBusy(false)
            }
          }}
        />
      </label>
      <p className="settings-hint">选择包含 .model3.json、.moc3、贴图和动作的完整导出文件夹。</p>
      {name && (
        <button
          className="secondary-button"
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await saveModel(form)
              setNotice('已恢复角色图片。')
              setError('')
            } catch (failure) {
              setError((failure as Error).message)
            } finally {
              setBusy(false)
            }
          }}
        >
          恢复角色图片
        </button>
      )}
      {busy && <p role="status">正在校验并保存模型…</p>}
      {notice && <p role="status">{notice}</p>}
      {error && (
        <p role="alert" className="workspace-error">
          {error}
        </p>
      )}
    </section>
  )
}
