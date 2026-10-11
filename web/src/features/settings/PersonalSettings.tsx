import { useEffect, useState } from 'react'
import { Check, UserRound } from 'lucide-react'
import { savePreferences, usePreferenceRevision, usePreferences } from '../../lib/preferences'
import { readAvatar } from '../../lib/avatar'

export function PersonalSettings() {
  const preferences = usePreferences()
  const revision = usePreferenceRevision()
  const [baselineRevision, setBaselineRevision] = useState(revision)
  const [dirty, setDirty] = useState(false)
  const [displayName, setDisplayName] = useState(preferences.displayName)
  const [avatar, setAvatar] = useState(preferences.avatar)
  const [reading, setReading] = useState(false)
  const [email, setEmail] = useState(preferences.email),
    [bio, setBio] = useState(preferences.bio)
  const [saved, setSaved] = useState(false),
    [error, setError] = useState(''),
    [saving, setSaving] = useState(false)
  useEffect(() => {
    if (dirty) return
    setDisplayName(preferences.displayName)
    setAvatar(preferences.avatar)
    setEmail(preferences.email)
    setBio(preferences.bio)
    setBaselineRevision(revision)
  }, [preferences, revision, dirty])
  return (
    <form
      className="settings-card"
      onSubmit={async (event) => {
        event.preventDefault()
        setSaving(true)
        setSaved(false)
        setError('')
        try {
          await savePreferences(
            {
              displayName: displayName.trim(),
              email: email.trim(),
              bio: bio.trim(),
              avatar,
            },
            baselineRevision
          )
          setDirty(false)
          setSaved(true)
          setError('')
        } catch (failure) {
          setError((failure as Error).message)
          setSaved(false)
        } finally {
          setSaving(false)
        }
      }}
      onChange={() => {
        setSaved(false)
        setDirty(true)
      }}
    >
      <div className="card-title">
        <UserRound size={20} />
        <div>
          <h2>个人信息</h2>
          <p>用你喜欢的名字，开启每一天。</p>
        </div>
      </div>
      <div className="profile-preview">
        <span className="profile-avatar large">
          {avatar ? <img src={avatar} alt="头像预览" /> : Array.from(displayName.trim() || '溪')[0]}
        </span>
        <div>
          <strong>{displayName.trim() || '你的息流空间'}</strong>
          <p>{bio.trim() || '给灵感留一个位置。'}</p>
        </div>
      </div>
      <div className="avatar-controls">
        <label className="secondary-button avatar-upload">
          {reading ? '正在处理…' : '更换头像'}
          <input
            type="file"
            aria-label="上传头像"
            accept="image/png,image/jpeg,image/webp,image/gif,image/avif"
            disabled={saving || reading}
            onChange={async (event) => {
              const file = event.target.files?.[0]
              event.target.value = ''
              if (!file) return
              setReading(true)
              setError('')
              setSaved(false)
              try {
                setAvatar(await readAvatar(file))
              } catch (failure) {
                setError((failure as Error).message)
              } finally {
                setReading(false)
              }
            }}
          />
        </label>
        <button
          type="button"
          className="secondary-button"
          disabled={!avatar || saving || reading}
          onClick={() => {
            setAvatar('')
            setSaved(false)
            setDirty(true)
          }}
        >
          恢复默认头像
        </button>
        <small>最大 5 MB · 自动居中裁剪 · 保存后生效</small>
      </div>
      <div className="settings-grid">
        <label>
          昵称
          <input
            disabled={saving}
            maxLength={40}
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="希望息流如何称呼你"
            autoComplete="nickname"
          />
        </label>
        <label>
          邮箱（可选）
          <input
            disabled={saving}
            type="email"
            maxLength={100}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="用于你的个人资料"
            autoComplete="email"
          />
        </label>
        <label className="full-width">
          个人简介
          <textarea
            disabled={saving}
            maxLength={300}
            rows={3}
            value={bio}
            onChange={(event) => setBio(event.target.value)}
            placeholder="最近在关注什么，或一句喜欢的话…"
          />
          <small>{bio.length} / 300</small>
        </label>
      </div>
      <p className="settings-hint">资料保存在本机；桌面版会备份偏好以供下次启动使用。</p>
      <div className="settings-save">
        {error && <span role="alert">{error}</span>}
        {saved && (
          <span className="saved" role="status">
            <Check size={15} />
            个人信息已保存
          </span>
        )}
        <button className="primary-button" disabled={saving || reading}>
          {saving ? '保存中…' : '保存个人信息'}
        </button>
      </div>
    </form>
  )
}
