import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'

export interface AssistantReference {
  title: string
  content: string
  truncated?: boolean
}
export function useAskAI() {
  const navigate = useNavigate(),
    cache = useQueryClient()
  return useMutation({
    mutationFn: async ({
      draft,
      reference,
    }: {
      draft: string
      reference?: AssistantReference
    }) => ({
      conversation: await api.create(),
      draft,
      reference: reference
        ? {
            ...reference,
            title: reference.title.slice(0, 300),
            content: reference.content.slice(0, 38000),
            ...(reference.content.length > 38000 || reference.title.length > 300
              ? { truncated: true }
              : {}),
          }
        : undefined,
    }),
    onSuccess: async ({ conversation, draft, reference }) => {
      await cache.invalidateQueries({ queryKey: ['conversations'] })
      navigate(`/assistant?c=${encodeURIComponent(conversation.id)}`, {
        state: { draft, reference },
      })
    },
  })
}
