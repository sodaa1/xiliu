import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RotateCcw } from 'lucide-react'
import { Modal } from '../../components/Modal'
import { getDemoNotice, getDemoStorageStatus, subscribeDemo } from './store'
import './demo.css'

export function DemoBar({ onReset }: { onReset: () => Promise<void> }) {
  const [confirm, setConfirm] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('')
  const [, update] = useState(0)
  useEffect(() => subscribeDemo(() => update((value) => value + 1)), [])
  async function reset() {
    setBusy(true)
    setError('')
    try {
      await onReset()
      setConfirm(false)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : '未能重置，请重试。')
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <div className="demo-bar" aria-label="游客演示状态">
        <strong>游客演示</strong>
        <span>
          示例资讯 · 本地模板回复 ·{' '}
          {getDemoStorageStatus() === 'memory' ? '仅在当前页面保留' : '修改保存在此浏览器'}
        </span>
        <Link to="/guide/getting-started">了解功能</Link>
        <button onClick={() => setConfirm(true)}>
          <RotateCcw size={13} />
          重置体验
        </button>
      </div>
      {getDemoNotice() && (
        <p className="demo-storage-note" role="status">
          {getDemoNotice()}
        </p>
      )}
      {confirm && (
        <Modal
          title="重置演示体验"
          onClose={() => {
            if (!busy) setConfirm(false)
          }}
        >
          <p>
            将清除本浏览器中的演示资料、聊天、计划、偏好与引导进度，恢复预置示例。正常 Web
            和桌面资料不受影响。
          </p>
          {error && <p role="alert">{error}</p>}
          <div className="editor-actions">
            <button className="secondary-button" disabled={busy} onClick={() => setConfirm(false)}>
              继续体验
            </button>
            <button className="primary-button" disabled={busy} onClick={() => void reset()}>
              {busy ? '重置中…' : '确认重置'}
            </button>
          </div>
        </Modal>
      )}
    </>
  )
}
