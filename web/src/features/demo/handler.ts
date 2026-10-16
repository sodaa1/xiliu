import { DemoError, demoUnavailable } from './types'
import { mutateDemo, readDemoState } from './store'
import { handleWorkspaceRequest } from './workspace'
import { startDemoChat, stopDemoChat } from './chat'

export async function handleDemoRequest(input: string, init?: RequestInit): Promise<Response> {
  if (init?.signal?.aborted) throw new DOMException('请求已停止', 'AbortError')
  try {
    const url = new URL(input, 'https://demo.invalid'),
      method = init?.method?.toUpperCase() ?? 'GET',
      path = url.pathname
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) : {}
    if (!body || typeof body !== 'object' || Array.isArray(body))
      throw new DemoError('请求格式不正确。')
    if (path === '/api/health' && method === 'GET')
      return Response.json({ status: 'ok', demo: true })
    const workspace = await handleWorkspaceRequest(url, method, body)
    if (workspace) return workspace
    if (path === '/api/settings/preferences') {
      if (method === 'GET') return Response.json((await readDemoState()).preferences)
      if (method === 'PUT')
        return Response.json(
          await mutateDemo((state) => {
            if (body.expected_revision !== state.preferences.revision)
              throw new DemoError('偏好已在其他窗口更新，请检查后重试。', 'conflict', 409)
            const changes = body.changes
            if (!changes || typeof changes !== 'object') throw new DemoError('偏好格式不正确。')
            const prefs = state.preferences.preferences
            for (const key of ['displayName', 'email', 'bio', 'avatar'] as const)
              if (changes[key] !== undefined) {
                if (
                  typeof changes[key] !== 'string' ||
                  changes[key].length > (key === 'avatar' ? 220000 : key === 'bio' ? 300 : 100)
                )
                  throw new DemoError('个人资料格式不正确。')
                if (
                  key === 'avatar' &&
                  changes[key] &&
                  !/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(changes[key])
                )
                  throw new DemoError('头像格式不正确。')
                prefs[key] = changes[key]
              }
            const choices = {
              theme: ['light', 'dark', 'system'],
              fontSize: ['small', 'medium', 'large'],
              fontFamily: ['system', 'rounded', 'serif'],
              density: ['comfortable', 'compact'],
            }
            for (const key of Object.keys(choices) as (keyof typeof choices)[])
              if (changes[key] !== undefined) {
                if (!choices[key].includes(changes[key])) throw new DemoError('外观选项不正确。')
                Object.assign(prefs, { [key]: changes[key] })
              }
            if (changes.reducedMotion !== undefined) {
              if (typeof changes.reducedMotion !== 'boolean')
                throw new DemoError('动态选项不正确。')
              prefs.reducedMotion = changes.reducedMotion
            }
            state.preferences.revision++
            state.preferences.initialized = true
            return state.preferences
          })
        )
    }
    if (path === '/api/settings/model' && method === 'GET')
      return Response.json({
        provider: 'custom',
        model: '本地演示模板',
        base_url: '',
        api_key_set: true,
        connections: [],
      })
    if (path === '/api/models/catalog' && method === 'GET')
      return Response.json({ custom: { base_url: '', models: ['本地演示模板'] } })
    if (path === '/api/commands' && method === 'GET')
      return Response.json([{ name: 'clear', description: '清除当前演示会话' }])
    if ((path.startsWith('/api/capabilities/') || path === '/api/automations') && method === 'GET')
      return Response.json([])
    if (path === '/api/settings/data' && method === 'GET')
      return Response.json({
        data_dir: '当前浏览器 · 独立演示空间',
        database: 'IndexedDB（不可用时仅当前页面）',
        content_count: (await readDemoState()).content.length,
        scheduler_active: false,
      })
    if (path === '/api/appearance/backgrounds' && method === 'GET')
      return Response.json({ settings: (await readDemoState()).background, images: [] })
    if (path === '/api/appearance/backgrounds/selection' && method === 'PUT')
      return Response.json(
        await mutateDemo((state) => {
          if (!['blank', 'builtin'].includes(body.mode)) throw new DemoError(demoUnavailable)
          state.background = { mode: body.mode, selected: null }
          return state.background
        })
      )
    if (/^\/api\/appearance\/models\/(chibi|standing)$/.test(path) && method === 'GET')
      return Response.json(null)
    if (path === '/api/conversations') {
      if (method === 'GET') return Response.json((await readDemoState()).conversations)
      if (method === 'POST')
        return Response.json(
          await mutateDemo((state) => {
            const now = new Date().toISOString(),
              conversation = {
                id: crypto.randomUUID(),
                title: '新对话',
                model_override: null,
                context_cutoff_seq: 0,
                compressed_through_seq: 0,
                context_summary: '',
                created_at: now,
                updated_at: now,
              }
            state.conversations.unshift(conversation)
            return conversation
          }),
          { status: 201 }
        )
    }
    const chat = /^\/api\/conversations\/([^/]+)(?:\/(messages|chat|stop))?$/.exec(path)
    if (chat) {
      const cid = decodeURIComponent(chat[1]),
        action = chat[2]
      if (!(await readDemoState()).conversations.some((item) => item.id === cid))
        throw new DemoError('会话不存在。', 'not_found', 404)
      if (action === 'chat' && method === 'POST') {
        if (
          typeof body.text !== 'string' ||
          (body.context !== undefined && typeof body.context !== 'string')
        )
          throw new DemoError('消息格式不正确。')
        return await startDemoChat(cid, body, init?.signal ?? undefined)
      }
      if (action === 'stop' && method === 'POST')
        return Response.json({ stopping: stopDemoChat(cid) })
      if (method === 'GET' && action === 'messages')
        return Response.json(
          (await readDemoState()).messages.filter((item) => item.conversation_id === cid)
        )
      if (method === 'GET' && !action)
        return Response.json((await readDemoState()).conversations.find((item) => item.id === cid))
      if (!action && method === 'DELETE') {
        stopDemoChat(cid)
        await mutateDemo((state) => {
          state.conversations = state.conversations.filter((item) => item.id !== cid)
          state.messages = state.messages.filter((item) => item.conversation_id !== cid)
        })
        return new Response(null, { status: 204 })
      }
      if (!action && method === 'PATCH')
        return Response.json(
          await mutateDemo((state) => {
            const item = state.conversations.find((item) => item.id === cid)!
            if (body.title !== undefined) {
              if (typeof body.title !== 'string' || !body.title.trim() || body.title.length > 500)
                throw new DemoError('会话标题不正确。')
              item.title = body.title
            }
            if (body.model_override !== undefined) {
              if (body.model_override !== null && body.model_override !== '本地演示模板')
                throw new DemoError(demoUnavailable)
              item.model_override = body.model_override
            }
            return item
          })
        )
    }
    throw new DemoError(demoUnavailable)
  } catch (error) {
    const known = error instanceof DemoError
    return Response.json(
      {
        error: {
          code: known ? error.code : 'invalid_request',
          message: known ? error.message : '演示请求未能完成，请检查输入后重试。',
        },
      },
      { status: known ? error.status : 400 }
    )
  }
}
