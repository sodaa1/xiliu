import type { Preferences } from '../../lib/preferences'
import type { Conversation, Message } from '../../lib/types'
import type { ContentItem, FeedItem, KnowledgeFolder, Task } from '../../lib/workspace-api'

export interface DemoState {
  schemaVersion: 1
  revision: number
  generation: string
  feed: FeedItem[]
  content: ContentItem[]
  folders: KnowledgeFolder[]
  tasks: Task[]
  conversations: Conversation[]
  messages: Message[]
  preferences: { preferences: Preferences; revision: number; initialized: boolean }
  background: { mode: 'blank' | 'builtin'; selected: null }
}
export class DemoError extends Error {
  constructor(
    message: string,
    public code = 'demo_unavailable',
    public status = 400
  ) {
    super(message)
  }
}
export const demoUnavailable = '演示版暂不执行这项操作。可查看使用指南，了解正常应用的使用条件。'
