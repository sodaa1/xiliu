export interface Conversation {
  id: string
  title: string
  model_override: string | null
  context_cutoff_seq: number
  compressed_through_seq: number
  context_summary: string
  created_at: string
  updated_at: string
}
export interface Message {
  id: string
  conversation_id: string
  seq: number
  role: 'user' | 'assistant' | 'event'
  content: string
  created_at: string
  metadata_json: string
}
export interface ModelSettings {
  provider: 'openai' | 'deepseek' | 'mimo' | 'custom'
  model: string
  base_url: string
  api_key_set: boolean
  profiles?: Record<string, { model: string; base_url: string; api_key_set: boolean }>
  connections?: ModelConnection[]
}
export interface ModelConnection {
  enabled?: boolean
  id: string
  label: string
  provider: ModelSettings['provider']
  model: string
  base_url: string
  api_key_set: boolean
}
export type ModelCatalog = Record<string, { base_url: string; models: string[] }>
export interface Command {
  name: string
  description: string
}
export interface Capability {
  name: string
  description: string
}
export interface WebEvent {
  type: 'status' | 'progress' | 'final' | 'error'
  stage?: string
  message?: string
  text?: string
  message_id?: string
  code?: string
  role?: Message['role']
  reasoning_delta?: string
  metadata?: { thinking?: Thinking; model?: string; cancelled?: boolean }
  reset_messages?: boolean
}
export interface Thinking {
  elapsed_ms: number
  steps: string[]
  reasoning: string
}
export interface ChatRun {
  stopping?: boolean
  cid: string
  status: string
  startedAt: number
  steps: string[]
  reasoning: string
}
export type ChatOutcome = 'success' | 'stopped' | 'error'
