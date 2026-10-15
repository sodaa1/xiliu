import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, X } from 'lucide-react'
import { CaptureForm } from '../content/CaptureDialog'
import { companionCall } from '../../desktop/companion'
import { isDesktop } from '../../desktop/bridge'
import type { ContentItem } from '../../lib/workspace-api'
import '../content/content-knowledge.css'
import './companion.css'

export function CapturePage() {
  const navigate = useNavigate()
  const [saved, setSaved] = useState<ContentItem | null>(null)
  const [error, setError] = useState('')
  const close = () => {
    if (isDesktop())
      void companionCall('close_capture').catch((error: Error) => setError(error.message))
    else navigate('/today')
  }
  return (
    <main className="capture-window">
      <header>
        <div>
          <span className="eyebrow">随手留住，每一个灵感</span>
          <h1>收进 Inbox</h1>
        </div>
        <button type="button" className="icon-button" aria-label="关闭收录窗口" onClick={close}>
          <X size={18} />
        </button>
      </header>
      {saved && (
        <div className="capture-saved" role="status">
          <Check size={18} />
          <span>已收进 Inbox，可以继续收录。</span>
          <button
            type="button"
            onClick={() => {
              if (isDesktop())
                void companionCall('open_main', {
                  path: `/inbox?item=${encodeURIComponent(saved.id)}`,
                }).catch((error: Error) => setError(error.message))
              else navigate(`/inbox?item=${encodeURIComponent(saved.id)}`)
            }}
          >
            查看内容
          </button>
        </div>
      )}
      <CaptureForm
        draftKey="xiliu-capture-draft"
        onClose={close}
        onSaved={(item) => {
          setSaved(item)
          if (isDesktop())
            void companionCall('captured', { id: item.id }).catch((error: Error) =>
              setError(error.message)
            )
        }}
      />
      {error && (
        <p role="alert" className="workspace-error">
          {error}
        </p>
      )}
      <p className="capture-footnote">关闭小窗会保留当前草稿，下次打开可继续。</p>
    </main>
  )
}
