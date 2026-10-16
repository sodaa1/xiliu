import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { ChatRun, ChatOutcome, Conversation, Message } from '../../lib/types'
import { ChatContext } from './chat-context'

export function ChatProvider({ children }: { children: ReactNode }) {
  const cache = useQueryClient()
  const [runs, setRuns] = useState<Record<string, ChatRun>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [outcomes, setOutcomes] = useState<Record<string, ChatOutcome>>({})
  const [selected, select] = useState<string | null>(null)
  const active = useRef(new Map<string, AbortController>())
  useEffect(
    () => () => {
      for (const controller of active.current.values()) controller.abort()
    },
    []
  )

  function clearRun(id: string) {
    setRuns((items) => {
      const next = { ...items }
      delete next[id]
      return next
    })
  }

  async function stop(id: string) {
    const controller = active.current.get(id)
    if (!controller) return
    setRuns((items) => ({ ...items, [id]: { ...items[id], stopping: true, status: '正在停止…' } }))
    try {
      if (!id || !(await api.stop(id)).stopping) controller.abort()
    } catch (failure) {
      setErrors((items) => ({
        ...items,
        [id]: failure instanceof Error ? failure.message : '停止失败，请重试。',
      }))
      setRuns((items) =>
        items[id] ? { ...items, [id]: { ...items[id], stopping: false } } : items
      )
    }
  }

  function dismiss(id: string) {
    setErrors((items) => {
      const next = { ...items }
      delete next[id]
      return next
    })
  }
  async function send(
    id: string | undefined,
    text: string,
    onCreated: (id: string) => void,
    context?: string,
    onOutcome?: (outcome: ChatOutcome) => void
  ) {
    if (active.current.has(id ?? '') || !text.trim()) return
    const controller = new AbortController()
    active.current.set(id ?? '', controller)
    const startedAt = Date.now()
    let target = id
    let outcome: ChatOutcome = 'error'
    dismiss(id ?? '')
    setRuns((items) => ({
      ...items,
      [id ?? '']: { cid: id ?? '', status: '正在处理…', startedAt, steps: [], reasoning: '' },
    }))
    try {
      if (!target) {
        const created = await api.create()
        if (controller.signal.aborted) return
        target = created.id
        active.current.delete('')
        active.current.set(target, controller)
        clearRun('')
        cache.setQueryData(['conversation', target], created)
        cache.setQueryData<Conversation[]>(['conversations'], (items = []) => [created, ...items])
        select(target)
        onCreated(target)
      }
      const turnCid = target
      await cache.cancelQueries({ queryKey: ['messages', turnCid] })
      if (controller.signal.aborted) return
      setRuns((items) => ({
        ...items,
        [turnCid]: { cid: turnCid, status: '正在处理…', startedAt, steps: [], reasoning: '' },
      }))
      cache.setQueryData<Message[]>(['messages', turnCid], (items = []) => [
        ...items,
        {
          id: crypto.randomUUID(),
          conversation_id: turnCid,
          seq: items.length + 1,
          role: 'user',
          content: text,
          created_at: new Date().toISOString(),
          metadata_json: '{}',
        },
      ])
      await api.chat(
        turnCid,
        text,
        controller.signal,
        (event) => {
          if (controller.signal.aborted) return
          if (event.type === 'error') {
            setErrors((items) => ({
              ...items,
              [turnCid]: event.message ?? '本次对话失败，请重试。',
            }))
          } else if (event.type === 'final') {
            outcome = event.metadata?.cancelled ? 'stopped' : 'success'
            cache.setQueryData<Message[]>(['messages', turnCid], (items = []) => {
              const previous = event.reset_messages ? [] : items
              return [
                ...previous,
                {
                  id: event.message_id!,
                  conversation_id: turnCid,
                  seq: previous.length + 1,
                  role: event.role ?? 'assistant',
                  content: event.text ?? '',
                  created_at: new Date().toISOString(),
                  metadata_json: JSON.stringify(event.metadata ?? {}),
                },
              ]
            })
          } else {
            setRuns((items) => {
              const current = items[turnCid]
              if (!current) return items
              const status = event.message ?? current.status
              return {
                ...items,
                [turnCid]: {
                  ...current,
                  status: current.stopping ? '正在停止…' : status,
                  steps:
                    event.reasoning_delta || current.steps.at(-1) === status
                      ? current.steps
                      : [...current.steps, status],
                  reasoning: current.reasoning + (event.reasoning_delta ?? ''),
                },
              }
            })
          }
        },
        context
      )
    } catch (failure) {
      if (!controller.signal.aborted)
        setErrors((items) => ({
          ...items,
          [target ?? '']: failure instanceof Error ? failure.message : '连接失败，请重试。',
        }))
    } finally {
      if (!controller.signal.aborted) {
        if (target)
          await Promise.all([
            cache.invalidateQueries({ queryKey: ['messages', target] }),
            cache.invalidateQueries({ queryKey: ['conversation', target] }),
          ])
        await cache.invalidateQueries({ queryKey: ['conversations'] })
        await Promise.all(
          ['content', 'content-tags', 'knowledge-folders', 'today', 'data-settings'].map((key) =>
            cache.invalidateQueries({ queryKey: [key] })
          )
        )
      }
      const key = target ?? id ?? ''
      if (active.current.get(key) === controller) {
        setOutcomes((items) => {
          const next = { ...items }
          delete next[key]
          if (Object.keys(next).length >= 64) delete next[Object.keys(next)[0]]
          next[key] = controller.signal.aborted ? 'stopped' : outcome
          return next
        })
        active.current.delete(key)
        clearRun(key)
      }
      onOutcome?.(controller.signal.aborted ? 'stopped' : outcome)
    }
  }
  return (
    <ChatContext.Provider value={{ runs, errors, outcomes, selected, select, dismiss, send, stop }}>
      {children}
    </ChatContext.Provider>
  )
}
