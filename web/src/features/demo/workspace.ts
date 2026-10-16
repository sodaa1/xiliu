import type { ContentItem, FeedItem, Task } from '../../lib/workspace-api'
import { mutateDemo, readDemoState } from './store'
import { DemoError, demoUnavailable, type DemoState } from './types'
type Body = Record<string, unknown>
const now = () => new Date().toISOString()
function row<T extends { id: string }>(rows: T[], id: string): T {
  const item = rows.find((entry) => entry.id === id)
  if (!item) throw new DemoError('内容不存在，请刷新或重新选择。', 'not_found', 404)
  return item
}
function text(body: Body, key: string, fallback = '', max = 40000): string {
  if (body[key] === undefined) return fallback
  if (typeof body[key] !== 'string' || body[key].length > max)
    throw new DemoError('内容格式或长度不正确。', 'invalid_request')
  return body[key] as string
}
function tags(body: Body, fallback: string[] = []): string[] {
  if (body.tags === undefined) return fallback
  if (
    !Array.isArray(body.tags) ||
    body.tags.length > 30 ||
    body.tags.some((tag) => typeof tag !== 'string' || tag.length > 100)
  )
    throw new DemoError('标签格式不正确。')
  return [...new Set(body.tags as string[])]
}
function classify(state: DemoState, item: ContentItem) {
  item.status = 'knowledge'
  item.folder_id =
    [...state.folders]
      .sort((a, b) => b.priority - a.priority)
      .find((folder) => folder.tags.some((tag) => item.tags.includes(tag)))?.id ?? null
  item.updated_at = now()
  return item
}
function makeContent(body: Body): ContentItem {
  const content = text(body, 'content', text(body, 'text')).trim()
  if (!content) throw new DemoError('请输入要保存的文字或链接。')
  const link = /^https?:\/\/\S+$/.test(content)
  return {
    id: crypto.randomUUID(),
    type: link ? 'link' : 'note',
    status: 'inbox',
    title: text(body, 'title', content.slice(0, 60), 500),
    content,
    summary: text(body, 'summary', content.slice(0, 180), 4000),
    source: text(body, 'source', link ? content : '演示收集'),
    tags: tags(body),
    filename: null,
    folder_id: null,
    processing_status: 'ready',
    created_at: now(),
    updated_at: now(),
  }
}
function listFeed(state: DemoState, url: URL) {
  const source = url.searchParams.get('source'),
    q = (url.searchParams.get('q') ?? '').toLowerCase()
  return {
    items: state.feed.filter(
      (item) =>
        (!source || item.source === source) &&
        (url.searchParams.get('include_hidden') === 'true' || (!item.hidden && !item.deleted_at)) &&
        `${item.title} ${item.summary} ${item.tags.join(' ')}`.toLowerCase().includes(q)
    ),
    sources: ['aihot', 'github', 'manual'].map((source) => ({
      source,
      label: source === 'github' ? 'GitHub Top 5' : source === 'aihot' ? 'AI Hot' : '我的资讯',
      status: 'ok',
      message: '预置示例 · 非实时资讯',
      updated_at: now(),
    })),
  }
}
export async function handleWorkspaceRequest(
  url: URL,
  method: string,
  body: Body
): Promise<Response | undefined> {
  const path = url.pathname.replace(/^\/api/, ''),
    get = method === 'GET',
    id = path.split('/').filter(Boolean).map(decodeURIComponent)
  if ((path === '/feed' && get) || (path === '/feed/refresh' && method === 'POST'))
    return Response.json(listFeed(await readDemoState(), url))
  if (path === '/today' && get) {
    const state = await readDemoState()
    return Response.json({
      feed: listFeed(state, url).items,
      tasks: state.tasks,
      inbox_count: state.content.filter((item) => item.status === 'inbox').length,
    })
  }
  if (path === '/feed/manual' && method === 'POST')
    return Response.json(
      await mutateDemo((state) => {
        const address = text(body, 'url')
        if (!/^https?:\/\//.test(address)) throw new DemoError('请输入 http 或 https 链接。')
        const item: FeedItem = {
          id: crypto.randomUUID(),
          source: 'manual',
          editable: true,
          url: address,
          title: text(body, 'title', address, 500),
          summary: text(body, 'summary', '', 4000),
          tags: tags(body),
          metadata: { demo: true, fetch_status: 'not_requested' },
          published_at: now(),
          created_at: now(),
          updated_at: now(),
        }
        state.feed.unshift(item)
        return item
      }),
      { status: 201 }
    )
  if (id[0] === 'feed' && id.length >= 2 && !get)
    return Response.json(
      await mutateDemo((state) => {
        const manual = id[1] === 'manual',
          item = row(state.feed, manual ? id[2] : id[1]),
          action = manual ? id[3] : id[2]
        if (manual && item.source !== 'manual') throw new DemoError('只能编辑手动资讯。')
        if (!manual && action === 'save' && method === 'POST') {
          const existing = state.content.find((entry) => entry.source === item.url)
          if (existing) return existing
          const content = makeContent({
            title: item.title,
            content: item.summary || item.title,
            source: item.url,
            tags: item.tags,
          })
          content.type = 'link'
          state.content.unshift(content)
          return content
        }
        if (!manual && action === 'summarize' && method === 'POST')
          return {
            summary: `演示摘要：${item.summary || item.title}（仅整理卡片内容，未抓取原网页。）`,
          }
        if (!manual && ['hide', 'unhide'].includes(action) && method === 'POST')
          item.hidden = action === 'hide'
        else if (manual && action === 'restore' && method === 'POST') item.deleted_at = null
        else if (manual && !action && method === 'DELETE') item.deleted_at = now()
        else if (manual && !action && method === 'PATCH') {
          if (body.url !== undefined && !/^https?:\/\//.test(text(body, 'url')))
            throw new DemoError('链接格式不正确。')
          for (const key of ['title', 'summary', 'url'] as const)
            if (body[key] !== undefined) item[key] = text(body, key)
          item.tags = tags(body, item.tags)
          item.updated_at = now()
        } else throw new DemoError(demoUnavailable)
        return item
      })
    )
  if ((path === '/inbox' || path === '/content') && get) {
    const state = await readDemoState(),
      status = path === '/inbox' ? 'inbox' : url.searchParams.get('status'),
      q = (url.searchParams.get('q') ?? '').toLowerCase(),
      tag = url.searchParams.get('tag')
    return Response.json(
      state.content.filter(
        (item) =>
          (!status || item.status === status) &&
          (!tag || item.tags.includes(tag)) &&
          `${item.title} ${item.content} ${item.tags.join(' ')}`.toLowerCase().includes(q)
      )
    )
  }
  if ((path === '/inbox/import' || path === '/content') && method === 'POST') {
    if (body.filename || body.data_base64 || body.type === 'file' || body.use_ai === true)
      throw new DemoError(demoUnavailable)
    return Response.json(
      await mutateDemo((state) => {
        const item = makeContent(body)
        state.content.unshift(item)
        return item
      }),
      { status: 201 }
    )
  }
  if (path === '/inbox/classify-batch' && method === 'POST')
    return Response.json(
      await mutateDemo((state) => {
        if (
          !Array.isArray(body.item_ids) ||
          body.item_ids.some((value) => typeof value !== 'string')
        )
          throw new DemoError('请选择资料。')
        const items = body.item_ids.length
          ? body.item_ids.map((value) => row(state.content, value as string))
          : state.content.filter((item) => item.status === 'inbox')
        return { items: items.map((item) => classify(state, item)) }
      })
    )
  if (id[0] === 'inbox' && id[2] === 'retry' && method === 'POST')
    return Response.json(row((await readDemoState()).content, id[1]))
  if (id[0] === 'content' && id.length === 2) {
    if (get) return Response.json(row((await readDemoState()).content, id[1]))
    if (method === 'DELETE') {
      await mutateDemo((state) => {
        row(state.content, id[1])
        state.content = state.content.filter((item) => item.id !== id[1])
      })
      return new Response(null, { status: 204 })
    }
    if (method === 'PATCH')
      return Response.json(
        await mutateDemo((state) => {
          const item = row(state.content, id[1])
          for (const key of ['title', 'content', 'summary'] as const)
            if (body[key] !== undefined) item[key] = text(body, key)
          item.tags = tags(body, item.tags)
          if (body.status !== undefined) {
            if (!['inbox', 'knowledge'].includes(String(body.status)))
              throw new DemoError('资料状态不正确。')
            item.status = body.status as ContentItem['status']
            if (item.status === 'knowledge' && body.folder_id === undefined) classify(state, item)
          }
          if (body.folder_id !== undefined)
            item.folder_id =
              body.folder_id === null ? null : row(state.folders, String(body.folder_id)).id
          if (item.status === 'inbox') item.folder_id = null
          item.updated_at = now()
          return item
        })
      )
  }
  if (path === '/knowledge/search' && get) {
    const q = (url.searchParams.get('q') ?? '').toLowerCase(),
      state = await readDemoState()
    return Response.json({
      mode_used: 'local',
      channels: ['正文', '标签'],
      items: state.content
        .filter(
          (item) =>
            item.status === 'knowledge' &&
            `${item.title} ${item.content} ${item.tags.join(' ')}`.toLowerCase().includes(q)
        )
        .slice(0, 20)
        .map((item) => ({
          document_id: item.id,
          title: item.title,
          summary: item.summary,
          matched_tags: item.tags,
          snippet: item.content.slice(0, 280),
        })),
    })
  }
  if (path === '/knowledge/folders' && get) {
    const state = await readDemoState()
    return Response.json(
      state.folders.map((folder) => ({
        ...folder,
        item_count: state.content.filter(
          (item) => item.status === 'knowledge' && item.folder_id === folder.id
        ).length,
      }))
    )
  }
  if (id[0] === 'knowledge' && id[1] === 'folders') {
    if (id.length === 4 && id[3] === 'items' && get) {
      const state = await readDemoState()
      if (id[2] !== 'unfiled') row(state.folders, id[2])
      return Response.json(
        state.content.filter(
          (item) =>
            item.status === 'knowledge' &&
            (id[2] === 'unfiled' ? !item.folder_id : item.folder_id === id[2])
        )
      )
    }
    if ((id.length === 2 && method === 'POST') || (id.length === 3 && method === 'PATCH'))
      return Response.json(
        await mutateDemo((state) => {
          const folder =
            method === 'POST'
              ? {
                  id: crypto.randomUUID(),
                  name: '',
                  summary: '',
                  tags: [] as string[],
                  priority: 0,
                  item_count: 0,
                  created_at: now(),
                  updated_at: now(),
                }
              : row(state.folders, id[2])
          folder.name = text(body, 'name', folder.name, 200).trim()
          if (!folder.name) throw new DemoError('请输入文件夹名称。')
          folder.summary = text(body, 'summary', folder.summary, 4000)
          folder.tags = tags(body, folder.tags)
          if (body.priority !== undefined) {
            if (!Number.isInteger(body.priority)) throw new DemoError('优先级需要整数。')
            folder.priority = Number(body.priority)
          }
          folder.updated_at = now()
          if (method === 'POST') state.folders.push(folder)
          return folder
        })
      )
    if (id.length === 3 && method === 'DELETE') {
      await mutateDemo((state) => {
        row(state.folders, id[2])
        state.folders = state.folders.filter((folder) => folder.id !== id[2])
        state.content.forEach((item) => {
          if (item.folder_id === id[2]) item.folder_id = null
        })
      })
      return new Response(null, { status: 204 })
    }
  }
  if (path === '/tasks' && get) return Response.json((await readDemoState()).tasks)
  if (
    (path === '/tasks' && method === 'POST') ||
    (id[0] === 'tasks' && id.length === 2 && method === 'PATCH')
  )
    return Response.json(
      await mutateDemo((state) => {
        const task: Task =
          method === 'POST'
            ? {
                id: crypto.randomUUID(),
                title: '',
                completed: false,
                due_at: null,
                scope: 'day',
                parent_id: null,
                created_at: now(),
                updated_at: now(),
              }
            : row(state.tasks, id[1])
        task.title = text(body, 'title', task.title, 500).trim()
        if (!task.title) throw new DemoError('请输入计划名称。')
        if (body.completed !== undefined) {
          if (typeof body.completed !== 'boolean') throw new DemoError('完成状态不正确。')
          task.completed = body.completed
        }
        if (body.scope !== undefined) {
          if (!['day', 'week', 'goal'].includes(String(body.scope)))
            throw new DemoError('计划范围不正确。')
          task.scope = body.scope as Task['scope']
        }
        if (body.due_at !== undefined) {
          if (
            body.due_at !== null &&
            (typeof body.due_at !== 'string' || !Number.isFinite(Date.parse(body.due_at)))
          )
            throw new DemoError('日期不正确。')
          task.due_at = body.due_at as string | null
        }
        if (body.parent_id !== undefined) {
          let parent = body.parent_id === null ? null : row(state.tasks, String(body.parent_id))
          const seen = new Set([task.id])
          while (parent) {
            if (seen.has(parent.id)) throw new DemoError('计划不能形成循环关联。')
            seen.add(parent.id)
            parent = parent.parent_id ? row(state.tasks, parent.parent_id) : null
          }
          task.parent_id = body.parent_id as string | null
        }
        task.updated_at = now()
        if (method === 'POST') state.tasks.push(task)
        return task
      })
    )
  if (id[0] === 'tasks' && id.length === 2 && method === 'DELETE') {
    await mutateDemo((state) => {
      row(state.tasks, id[1])
      state.tasks = state.tasks.filter((task) => task.id !== id[1])
      state.tasks.forEach((task) => {
        if (task.parent_id === id[1]) task.parent_id = null
      })
    })
    return new Response(null, { status: 204 })
  }
  return undefined
}
