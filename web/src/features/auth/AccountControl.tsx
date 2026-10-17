import { useState } from 'react'
import { logout } from './client'
import { useCloudSession } from './session'

export function AccountControl() {
  const session = useCloudSession()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (!session) return null
  return (
    <div className="cloud-account">
      <span>{session.user.username}</span>
      <button
        type="button"
        disabled={busy}
        onClick={async () => {
          setBusy(true)
          setError('')
          try {
            await logout()
          } catch {
            setError('退出失败，请重试。')
            setBusy(false)
          }
        }}
      >
        {busy ? '正在退出…' : '退出'}
      </button>
      {error && <span role="alert">{error}</span>}
    </div>
  )
}
