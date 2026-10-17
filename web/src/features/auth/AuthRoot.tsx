import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Brand } from '../../components/Brand'
import { authenticate, loadBootstrap, loadSession } from './client'
import { applySession, currentSession, useCloudSession } from './session'
import './auth.css'

export function AuthForm({
  signupEnabled,
  onSuccess = () => window.location.replace('/today'),
}: {
  signupEnabled: boolean
  onSuccess?: () => void
}) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await authenticate(mode, username, password)
      setPassword('')
      onSuccess()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : '请求失败，请重试。')
    } finally {
      setBusy(false)
    }
  }
  return (
    <main className="cloud-auth">
      <section className="cloud-auth-panel" aria-labelledby="auth-title">
        <div className="cloud-auth-brand">
          <Brand large />
          <span>息流</span>
        </div>
        <h1 id="auth-title">{mode === 'login' ? '回到你的工作区' : '创建你的工作区'}</h1>
        <p>把灵感、资料与计划，放在同一个地方。</p>
        <form onSubmit={submit} aria-busy={busy}>
          <label htmlFor="cloud-username">账号</label>
          <input
            id="cloud-username"
            autoComplete="username"
            required
            minLength={3}
            maxLength={32}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={busy}
          />
          <label htmlFor="cloud-password">密码</label>
          <input
            id="cloud-password"
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
            minLength={12}
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={busy}
          />
          {mode === 'register' && (
            <p className="cloud-auth-hint">
              账号使用 3–32 位英文字母、数字或下划线；密码至少 12 位。
            </p>
          )}
          {error && (
            <p role="alert" className="cloud-auth-error">
              {error}
            </p>
          )}
          <button className="cloud-auth-submit" disabled={busy}>
            {busy ? '正在处理…' : mode === 'login' ? '登录' : '注册并开始使用'}
          </button>
        </form>
        {signupEnabled && (
          <button
            type="button"
            className="cloud-auth-switch"
            disabled={busy}
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError('')
              setPassword('')
            }}
          >
            {mode === 'login' ? '还没有账号？创建一个' : '已有账号？返回登录'}
          </button>
        )}
        <a className="cloud-auth-guest" href="/demo/#/today">
          先体验一下 <span aria-hidden="true">↗</span>
        </a>
        <p className="cloud-auth-hint">
          游客可免登录体验示例资料与模拟回复。登录后拥有独立资料空间，可配置自己的模型
          API；公共试用开放时，每个账号累计可用 5 次。
        </p>
      </section>
    </main>
  )
}

export function AuthRoot({ children }: { children: ReactNode }) {
  const session = useCloudSession()
  const [signup, setSignup] = useState(false)
  const [failure, setFailure] = useState('')
  useEffect(() => {
    let active = true
    Promise.all([loadBootstrap(), loadSession()])
      .then(([bootstrap, value]) => {
        if (active) {
          setSignup(bootstrap.signup_enabled)
          applySession(value)
        }
      })
      .catch(() => {
        if (active) setFailure('无法连接服务器，请检查网络后重新加载。')
      })
    return () => {
      active = false
    }
  }, [])
  useEffect(() => {
    const verify = () => {
      const expected = currentSession()?.workspace.id
      if (!expected) return
      void loadSession()
        .then((value) => {
          if (currentSession()?.workspace.id === expected) {
            if (value?.workspace.id !== expected) applySession(null)
            else if (value.csrf_token !== currentSession()?.csrf_token) applySession(value)
          }
        })
        .catch(() => {})
    }
    window.addEventListener('focus', verify)
    return () => window.removeEventListener('focus', verify)
  }, [])
  if (failure)
    return (
      <main className="cloud-auth">
        <p role="alert">
          {failure} <button onClick={() => window.location.reload()}>重新加载</button>
        </p>
      </main>
    )
  if (session === undefined)
    return (
      <main className="cloud-auth" role="status">
        正在打开工作区…
      </main>
    )
  return session ? (
    <div key={session.workspace.id} className="cloud-workspace">
      {children}
    </div>
  ) : (
    <AuthForm signupEnabled={signup} />
  )
}
