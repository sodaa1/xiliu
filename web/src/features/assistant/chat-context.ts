import { createContext, useContext } from 'react'
import type { ChatRun } from '../../lib/types'

export const ChatContext = createContext<{
  runs: Record<string, ChatRun>
  errors: Record<string, string>
  selected: string | null
  select: (id: string | null) => void
  dismiss: (id: string) => void
  stop: (id: string) => Promise<void>
  send: (
    id: string | undefined,
    text: string,
    onCreated: (id: string) => void,
    context?: string
  ) => Promise<void>
} | null>(null)

export function useChat() {
  const chat = useContext(ChatContext)
  if (!chat) throw new Error('ChatProvider is required')
  return chat
}
