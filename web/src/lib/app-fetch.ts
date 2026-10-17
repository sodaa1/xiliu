import { isCloud, isDemo } from './runtime-mode'
import { applySession, currentSession, sessionSignal } from '../features/auth/session'

export async function appFetch(input: string, init?: RequestInit): Promise<Response> {
  if (isDemo) {
    const { handleDemoRequest } = await import('../features/demo/handler')
    return handleDemoRequest(input, init)
  }
  if (!isCloud || !input.startsWith('/api/')) return fetch(input, init)
  const session = currentSession()
  if (!session) throw new Error('请先登录工作区。')
  const headers = new Headers(init?.headers)
  headers.set('X-Workspace-ID', session.workspace.id)
  if (!['GET', 'HEAD'].includes(init?.method?.toUpperCase() ?? 'GET'))
    headers.set('X-CSRF-Token', session.csrf_token)
  const signal = init?.signal ? AbortSignal.any([init.signal, sessionSignal()]) : sessionSignal()
  const response = await fetch(input, { ...init, headers, signal, credentials: 'same-origin' })
  const csrfExpired =
    response.status === 403 &&
    (
      await response
        .clone()
        .json()
        .catch(() => ({}))
    ).error?.code === 'invalid_csrf'
  if (response.status === 401 || csrfExpired || response.headers.get('X-Session-Changed') === '1') {
    applySession(null)
    throw new Error('会话已失效或已切换，请重新登录。')
  }
  return response
}
