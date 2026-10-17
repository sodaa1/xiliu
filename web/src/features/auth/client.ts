import { applySession, currentSession, type CloudSession } from './session'

async function authRequest(path: string, init?: RequestInit) {
  const response = await fetch(`/api${path}`, { credentials: 'same-origin', ...init })
  if (response.status === 401 && path === '/auth/session') return null
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.error?.message ?? '暂时无法连接服务器，请稍后重试。')
  }
  return response.status === 204 ? null : response.json()
}
export const loadSession = (): Promise<CloudSession | null> => authRequest('/auth/session')
export const loadBootstrap = (): Promise<{ signup_enabled: boolean }> =>
  authRequest('/cloud/bootstrap')
export function authenticate(mode: 'login' | 'register', username: string, password: string) {
  return authRequest(`/auth/${mode}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}
export async function logout() {
  const csrf = currentSession()?.csrf_token ?? ''
  await authRequest('/auth/logout', { method: 'POST', headers: { 'X-CSRF-Token': csrf } })
  applySession(null)
}
