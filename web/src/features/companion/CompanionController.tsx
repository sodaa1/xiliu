import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useChat } from '../assistant/chat-context'
import { api } from '../../lib/api'
import { isDesktop } from '../../desktop/bridge'
import {
  companionCall,
  companionListen,
  describeRuns,
  idleStatus,
  type QuickRequest,
} from '../../desktop/companion'

export function CompanionController() {
  const chat = useChat()
  const current = useRef(chat)
  const previous = useRef<string | null>(null)
  const revision = useRef(Date.now())
  const queue = useRef(Promise.resolve())
  const navigate = useNavigate()
  const navigation = useRef(navigate)
  const cache = useQueryClient()
  useEffect(() => {
    current.current = chat
  }, [chat])
  useEffect(() => {
    navigation.current = navigate
  }, [navigate])
  useEffect(() => {
    if (!isDesktop()) return
    let disposed = false
    const cleanup: (() => void)[] = []
    const seen = new Set<string>()
    const setup = async () => {
      const listen = async <T,>(name: string, handler: (payload: T) => void) => {
        const stop = await companionListen<T>(name, handler)
        if (disposed) stop()
        else cleanup.push(stop)
      }
      await listen<string>('navigate', (path) => navigation.current(path))
      await listen<string>('captured', () => {
        for (const key of ['content', 'content-tags', 'knowledge-folders', 'today'])
          void cache.invalidateQueries({ queryKey: [key] })
      })
      await listen<QuickRequest>('request', (request) => {
        if (disposed || seen.has(request.requestId)) return
        seen.add(request.requestId)
        void (async () => {
          try {
            const created = await api.create()
            cache.setQueryData(['conversation', created.id], created)
            void cache.invalidateQueries({ queryKey: ['conversations'] })
            void current.current.send(created.id, request.text, () => {})
            await companionCall('ack', {
              requestId: request.requestId,
              cid: created.id,
              error: null,
            })
          } catch (error) {
            await companionCall('ack', {
              requestId: request.requestId,
              cid: null,
              error: error instanceof Error ? error.message : '创建会话失败，请重试。',
            })
          }
        })().catch(() => {
          /* Retained native request can be checked after a lost acknowledgement. */
        })
      })
      if (!disposed) await companionCall('ready')
    }
    void setup().catch(() => {
      /* Native quick submit reports an unavailable main window. */
    })
    return () => {
      disposed = true
      cleanup.forEach((stop) => stop())
    }
  }, [cache])
  useEffect(() => {
    if (!isDesktop()) return
    const status = describeRuns(chat.runs, chat.errors, chat.selected)
    const completed = previous.current
    previous.current = status.phase === 'thinking' ? status.cid : null
    const next =
      status.phase === 'idle' && completed && chat.outcomes[completed] === 'success'
        ? {
            ...idleStatus,
            phase: 'success' as const,
            cid: completed,
            message: '已经完成，点击查看对话',
          }
        : status
    const publish = (value: typeof next) => {
      const snapshot = { ...value, revision: ++revision.current }
      queue.current = queue.current
        .catch(() => {})
        .then(() => companionCall<void>('publish', { snapshot }))
        .catch(() => {})
    }
    publish(next)
    if (next.phase !== 'success') return
    const timer = window.setTimeout(() => publish(idleStatus), 5000)
    return () => window.clearTimeout(timer)
  }, [chat.runs, chat.errors, chat.outcomes, chat.selected])
  return null
}
