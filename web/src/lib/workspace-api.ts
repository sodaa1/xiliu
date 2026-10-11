import { ApiError } from './api'

export interface ContentItem {
  id: string
  type: 'note' | 'link' | 'file'
  status: 'inbox' | 'knowledge'
  title: string
  content: string
  summary: string
  source: string
  tags: string[]
  created_at: string
  updated_at: string
  filename: string | null
  folder_id?: string | null
  ai_processed?: boolean
  processing_status?: 'pending' | 'ready' | 'failed'
  processing_error?: string | null
}
export interface KnowledgeFolder {
  id: string
  name: string
  summary: string
  tags: string[]
  priority: number
  item_count: number
  created_at: string
  updated_at: string
}
export interface KnowledgeSearchResult {
  mode_used: string
  channels: string[]
  items: {
    document_id: string
    title: string
    summary: string
    matched_tags: string[]
    snippet: string
  }[]
}
export interface FeedItem {
  id: string
  source: 'aihot' | 'github' | 'manual'
  title: string
  summary: string
  url: string
  published_at: string
  tags: string[]
  metadata: Record<string, unknown>
  editable?: boolean
  hidden?: boolean
  deleted_at?: string | null
  created_at?: string
  updated_at?: string
}
export interface ManualFeedInput {
  url: string
  title?: string
  summary?: string
  tags?: string[]
  fetch_title?: boolean
}
export interface SourceStatus {
  source: string
  label: string
  status: string
  message: string
  updated_at: string | null
}
export interface FeedResult {
  items: FeedItem[]
  sources: SourceStatus[]
}
export interface Task {
  id: string
  title: string
  completed: boolean
  due_at: string | null
  created_at: string
  updated_at: string
}
export interface Automation {
  id: string
  name: string
  prompt: string
  trigger_type: 'cron' | 'interval' | 'date'
  schedule: Record<string, number | string>
  timezone: string
  enabled: boolean
}
export interface AutomationRun {
  run_id: string
  status: string
  started_at: string
  finished_at: string | null
  error?: string | null
  result_preview?: string | null
}
export interface DataSettings {
  data_dir: string
  database: string
  content_count: number
  scheduler_active: boolean
}
type ContentInput = Pick<ContentItem, 'type' | 'title' | 'content' | 'source' | 'tags'> &
  Partial<Pick<ContentItem, 'summary' | 'status'>> & { filename?: string; data_base64?: string }
async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    ...(body !== undefined
      ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      : {}),
  })
  if (!response.ok) {
    let payload: { error?: { code?: string; message?: string } } = {}
    try {
      payload = await response.json()
    } catch {
      /* Non-JSON error response. */
    }
    throw new ApiError(
      payload.error?.code ?? 'request_failed',
      payload.error?.message ?? '暂时无法完成操作，请重试。'
    )
  }
  return response.status === 204 ? (undefined as T) : response.json()
}
const itemPath = (id: string) => `/content/${encodeURIComponent(id)}`
function query(values: Record<string, string>) {
  return new URLSearchParams(Object.entries(values).filter(([, value]) => value)).toString()
}
export const workspaceApi = {
  inbox: () => request<ContentItem[]>('/inbox'),
  importContent: (body: {
    text?: string
    filename?: string
    data_base64?: string
    use_ai?: boolean
  }) => request<ContentItem>('/inbox/import', 'POST', body),
  contentItem: (id: string) => request<ContentItem>(itemPath(id)),
  classifyBatch: (item_ids: string[]) =>
    request<{ items: ContentItem[] }>('/inbox/classify-batch', 'POST', { item_ids, save_to_knowledge: true, use_ai: false }),
  retryContent: (id: string) =>
    request<ContentItem>(`/inbox/${encodeURIComponent(id)}/retry`, 'POST'),
  folders: () => request<KnowledgeFolder[]>('/knowledge/folders'),
  createFolder: (body: Pick<KnowledgeFolder, 'name' | 'summary' | 'tags' | 'priority'>) =>
    request<KnowledgeFolder>('/knowledge/folders', 'POST', body),
  updateFolder: (
    id: string,
    body: Partial<Pick<KnowledgeFolder, 'name' | 'summary' | 'tags' | 'priority'>>
  ) => request<KnowledgeFolder>(`/knowledge/folders/${encodeURIComponent(id)}`, 'PATCH', body),
  deleteFolder: (id: string) =>
    request<void>(`/knowledge/folders/${encodeURIComponent(id)}`, 'DELETE'),
  folderItems: (id: string) =>
    request<ContentItem[]>(`/knowledge/folders/${encodeURIComponent(id)}/items`),
  searchKnowledge: (q: string) =>
    request<KnowledgeSearchResult>(`/knowledge/search?${query({ q, mode: 'auto', limit: '6' })}`),
  content: (status: ContentItem['status'], q = '', tag = '') =>
    request<ContentItem[]>(`/content?${query({ status, q, tag })}`),
  createContent: (body: ContentInput) => request<ContentItem>('/content', 'POST', body),
  updateContent: (
    id: string,
    body: Partial<
      Pick<ContentItem, 'title' | 'content' | 'summary' | 'tags' | 'status' | 'folder_id'>
    >
  ) => request<ContentItem>(itemPath(id), 'PATCH', body),
  deleteContent: (id: string) => request<void>(itemPath(id), 'DELETE'),
  originalUrl: (id: string) => `/api${itemPath(id)}/original`,
  feed: (source = '', q = '', includeHidden = false) =>
    request<FeedResult>(
      `/feed?${query({ source, q, include_hidden: includeHidden ? 'true' : '' })}`
    ),
  refreshFeed: () => request<FeedResult>('/feed/refresh', 'POST'),
  addManualFeed: (body: ManualFeedInput) => request<FeedItem>('/feed/manual', 'POST', body),
  updateManualFeed: (id: string, body: Partial<ManualFeedInput>) =>
    request<FeedItem>(`/feed/manual/${encodeURIComponent(id)}`, 'PATCH', body),
  removeManualFeed: (id: string) =>
    request<FeedItem>(`/feed/manual/${encodeURIComponent(id)}`, 'DELETE'),
  restoreManualFeed: (id: string) =>
    request<FeedItem>(`/feed/manual/${encodeURIComponent(id)}/restore`, 'POST'),
  hideExternalFeed: (id: string) =>
    request<FeedItem>(`/feed/${encodeURIComponent(id)}/hide`, 'POST'),
  unhideExternalFeed: (id: string) =>
    request<FeedItem>(`/feed/${encodeURIComponent(id)}/unhide`, 'POST'),
  saveFeed: (id: string) => request<ContentItem>(`/feed/${encodeURIComponent(id)}/save`, 'POST'),
  today: () => request<{ feed: FeedItem[]; tasks: Task[]; inbox_count: number }>('/today'),
  createTask: (title: string, due_at: string | null) =>
    request<Task>('/tasks', 'POST', { title, due_at }),
  updateTask: (id: string, body: Partial<Pick<Task, 'title' | 'completed' | 'due_at'>>) =>
    request<Task>(`/tasks/${encodeURIComponent(id)}`, 'PATCH', body),
  deleteTask: (id: string) => request<void>(`/tasks/${encodeURIComponent(id)}`, 'DELETE'),
  automations: () => request<Automation[]>('/automations'),
  createAutomation: (body: {
    name: string
    prompt: string
    hour: number
    minute: number
    timezone: string
  }) => request<Automation>('/automations', 'POST', body),
  toggleAutomation: (id: string, enabled: boolean) =>
    request<Automation>(`/automations/${encodeURIComponent(id)}`, 'PATCH', { enabled }),
  deleteAutomation: (id: string) =>
    request<void>(`/automations/${encodeURIComponent(id)}`, 'DELETE'),
  runs: (id: string) => request<AutomationRun[]>(`/automations/${encodeURIComponent(id)}/runs`),
  dataSettings: () => request<DataSettings>('/settings/data'),
}
export function safeHttpUrl(value: string): string | undefined {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined
  } catch {
    return undefined
  }
}
export function fileBase64(file: File): Promise<string> {
  if (file.size > 20 * 1024 * 1024) return Promise.reject(new Error('文件不能超过 20 MB。'))
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('无法读取这个文件，请重新选择。'))
    reader.onload = () => resolve(String(reader.result).split(',')[1])
    reader.readAsDataURL(file)
  })
}
