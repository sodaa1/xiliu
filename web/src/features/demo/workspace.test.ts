import { beforeEach, expect, test } from 'vitest'
import { handleDemoRequest } from './handler'
import { mutateDemo, readDemoState, resetDemoState } from './store'

async function call(path: string, method = 'GET', body?: unknown) {
  const response = await handleDemoRequest(`/api${path}`, {
    method,
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  const value = response.status === 204 ? undefined : await response.json()
  if (!response.ok) throw new Error(value.error.message)
  return value
}
beforeEach(resetDemoState)
test.each([
  ['/content/note-method', '/content/note-method', 'title', 'summary'],
  ['/feed/manual/feed-manual', '/feed', 'title', 'summary'],
  ['/knowledge/folders/folder-learning', '/knowledge/folders', 'name', 'summary'],
  ['/tasks/task-week', '/tasks', 'title', 'title'],
])(
  'stale editing of %s cannot overwrite a newer record',
  async (path, readPath, field, secondField) => {
    const data = await call(readPath)
    const original = Array.isArray(data)
      ? data.find((item: { id: string }) => path.endsWith(item.id))
      : data.items
        ? data.items.find((item: { id: string }) => path.endsWith(item.id))
        : data
    await call(path, 'PATCH', { [field]: 'newer value', demo_revision: original.demo_revision })
    const stale = await handleDemoRequest(`/api${path}`, {
      method: 'PATCH',
      body: JSON.stringify({
        [field]: original[field],
        [secondField]: 'stale edit',
        demo_revision: original.demo_revision,
      }),
    })
    expect(stale.status).toBe(409)
    const latest = await call(readPath)
    const record = Array.isArray(latest)
      ? latest.find((item: { id: string }) => item.id === original.id)
      : latest.items
        ? latest.items.find((item: { id: string }) => item.id === original.id)
        : latest
    expect(record[field]).toBe('newer value')
  }
)
test('a manual link with an empty optional title uses the URL as its visible title', async () => {
  const saved = await call('/feed/manual', 'POST', {
    url: 'https://example.com/my-reading',
    title: '',
    summary: '',
  })
  expect(saved.title).toBe('https://example.com/my-reading')
  const edited = await call(`/feed/manual/${saved.id}`, 'PATCH', { title: '   ' })
  expect(edited.title).toBe('https://example.com/my-reading')
})
test('a request to fetch a real webpage title is not silently simulated', async () => {
  await expect(
    call('/feed/manual', 'POST', { url: 'https://example.com/my-reading', fetch_title: true })
  ).rejects.toThrow('演示')
  await expect(call('/feed/manual/feed-manual', 'PATCH', { fetch_title: true })).rejects.toThrow(
    '演示'
  )
})
test('new conversations have durable timestamps and can be renamed and deleted', async () => {
  const conversation = await call('/conversations', 'POST')
  expect(Number.isFinite(Date.parse(conversation.created_at))).toBe(true)
  await call(`/conversations/${conversation.id}`, 'PATCH', { title: '我的体验' })
  expect((await call(`/conversations/${conversation.id}`)).title).toBe('我的体验')
  await call(`/conversations/${conversation.id}`, 'DELETE')
  await expect(call(`/conversations/${conversation.id}`)).rejects.toThrow('不存在')
})
test('collect, tag, archive and search retain the actual saved document', async () => {
  const saved = await call('/feed/feed-reading/save', 'POST')
  expect(saved.status).toBe('inbox')
  expect((await call('/feed/feed-reading/save', 'POST')).id).toBe(saved.id)
  await call(`/content/${saved.id}`, 'PATCH', {
    tags: ['学习'],
    status: 'knowledge',
    folder_id: 'folder-learning',
  })
  const result = await call('/knowledge/search?q=知识库')
  expect(result.items.some((item: { document_id: string }) => item.document_id === saved.id)).toBe(
    true
  )
  expect((await call('/knowledge/folders'))[0].item_count).toBe(2)
})
test('deleting a folder keeps its documents and removes the stale reference', async () => {
  await call('/knowledge/folders/folder-learning', 'DELETE')
  expect((await call('/content/note-method')).folder_id).toBeNull()
  expect((await call('/content?status=knowledge')).length).toBe(1)
})
test('bulk classify, task hierarchy and restoration modify the demo snapshot', async () => {
  expect(
    (await call('/inbox/classify-batch', 'POST', { item_ids: ['note-inbox'] })).items[0].status
  ).toBe('knowledge')
  const task = await call('/tasks', 'POST', {
    title: '新计划',
    scope: 'day',
    parent_id: 'task-week',
  })
  expect(task.parent_id).toBe('task-week')
  await call(`/tasks/${task.id}`, 'PATCH', { completed: true })
  expect((await call('/tasks')).find((item: { id: string }) => item.id === task.id).completed).toBe(
    true
  )
  await call('/feed/manual/feed-manual', 'DELETE')
  expect(
    (await call('/feed')).items.some((item: { id: string }) => item.id === 'feed-manual')
  ).toBe(false)
  await call('/feed/manual/feed-manual/restore', 'POST')
  expect(
    (await call('/feed')).items.some((item: { id: string }) => item.id === 'feed-manual')
  ).toBe(true)
})
test('missing IDs and unsupported uploads fail instead of faking success', async () => {
  await expect(call('/content/not-found')).rejects.toThrow('不存在')
  await expect(
    call('/inbox/import', 'POST', { filename: 'private.pdf', data_base64: 'eA==' })
  ).rejects.toThrow('演示')
  await expect(call('/settings/model', 'PUT', { api_key: 'not-a-real-key' })).rejects.toThrow(
    '演示'
  )
})
test('preference revision conflicts do not overwrite the new settings', async () => {
  await call('/settings/preferences', 'PUT', {
    expected_revision: 0,
    changes: { displayName: '游客' },
  })
  const response = await handleDemoRequest('/api/settings/preferences', {
    method: 'PUT',
    body: JSON.stringify({ expected_revision: 0, changes: { displayName: '旧修改' } }),
  })
  expect(response.status).toBe(409)
  expect((await readDemoState()).preferences.preferences.displayName).toBe('游客')
})

test('old boolean-only demo tasks expose metadata defaults without inventing completion dates', async () => {
  await mutateDemo((state) => {
    state.tasks[0].completed = true
  })
  const tasks = await call('/tasks')
  expect(tasks[0]).toMatchObject({
    status: 'completed',
    completed: true,
    completed_at: null,
    starts_at: null,
    description: '',
    category: '',
    priority: 'normal',
    tags: [],
    reminder_minutes: null,
  })
  expect(tasks[1].status).toBe('not_started')
  expect((await call('/today')).tasks[0].completed_at).toBeNull()
  const edited = await call(`/tasks/${tasks[0].id}`, 'PATCH', { title: '历史完成任务' })
  expect(edited.completed_at).toBeNull()
  expect((await readDemoState()).tasks[0]).toMatchObject({
    status: 'completed',
    completed_at: null,
  })
})

test('demo task metadata is normalized and persisted alongside hierarchy', async () => {
  const task = await call('/tasks', 'POST', {
    title: '新计划',
    status: 'in_progress',
    starts_at: '2026-10-18T09:00:00+08:00',
    due_at: '2026-10-18T11:00:00+08:00',
    description: '说明',
    category: '学习',
    priority: 'important',
    tags: [' 阅读 ', '阅读', '', '笔记'],
    reminder_minutes: 15,
    parent_id: 'task-week',
  })
  expect(task).toMatchObject({
    status: 'in_progress',
    completed: false,
    completed_at: null,
    starts_at: '2026-10-18T09:00:00+08:00',
    due_at: '2026-10-18T11:00:00+08:00',
    description: '说明',
    category: '学习',
    priority: 'important',
    tags: ['阅读', '笔记'],
    reminder_minutes: 15,
    parent_id: 'task-week',
  })
  expect((await readDemoState()).tasks.find((item) => item.id === task.id)).toMatchObject(task)
  expect(
    (await call('/today')).tasks.find((item: { id: string }) => item.id === task.id)
  ).toMatchObject(task)
})

test('demo completion transitions synchronize status and preserve completion history', async () => {
  const task = await call('/tasks', 'POST', { title: '完成计划' })
  const completed = await call(`/tasks/${task.id}`, 'PATCH', { completed: true })
  expect(completed.status).toBe('completed')
  expect(Number.isFinite(Date.parse(completed.completed_at))).toBe(true)
  const edited = await call(`/tasks/${task.id}`, 'PATCH', {
    completed: true,
    description: '修改说明',
  })
  expect(edited.completed_at).toBe(completed.completed_at)
  const reopened = await call(`/tasks/${task.id}`, 'PATCH', { status: 'in_progress' })
  expect(reopened).toMatchObject({ completed: false, status: 'in_progress', completed_at: null })
  const timestamp = '2026-10-18T10:00:00Z'
  const explicit = await call(`/tasks/${task.id}`, 'PATCH', {
    status: 'completed',
    completed_at: timestamp,
  })
  expect(explicit).toMatchObject({ completed: true, status: 'completed', completed_at: timestamp })
  expect(await call(`/tasks/${task.id}`, 'PATCH', { completed: false })).toMatchObject({
    completed: false,
    status: 'not_started',
    completed_at: null,
  })
})

test.each(['2026-10-18', '2026-10-18T10:00:00', null])(
  'demo completion accepts ISO dates and generates a missing new completion time: %j',
  async (completed_at) => {
    const task = await call('/tasks', 'POST', {
      title: '已完成',
      status: 'completed',
      completed_at,
    })
    expect(task.completed).toBe(true)
    if (completed_at === null) expect(Number.isFinite(Date.parse(task.completed_at))).toBe(true)
    else expect(task.completed_at).toBe(completed_at)
  }
)

test.each([
  { status: 'paused' },
  { status: ['completed'] },
  { completed: 'yes' },
  { status: 'in_progress', completed: true },
  { status: 'completed', completed: false },
  { completed_at: 'not-a-date' },
  { completed_at: '2026-10-18T10:00:00Z' },
  { completed: true, completed_at: '10/18/2026' },
  { starts_at: 'not-a-date' },
  { starts_at: 10 },
  { due_at: 'not-a-date' },
  { starts_at: '2026-10-19T10:00:00Z', due_at: '2026-10-18T10:00:00Z' },
  { description: 'x'.repeat(501) },
  { category: 'x'.repeat(33) },
  { priority: 'high' },
  { priority: ['urgent'] },
  { tags: ['x'.repeat(33)] },
  { tags: [3] },
  { tags: Array.from({ length: 11 }, (_, i) => `tag${i}`) },
  { reminder_minutes: 10 },
  { reminder_minutes: '15' },
  { reminder_minutes: 0 },
])('invalid demo task metadata is rejected atomically: %j', async (body) => {
  const before = await readDemoState()
  await expect(call('/tasks/task-day', 'PATCH', { title: '不能保存', ...body })).rejects.toThrow()
  expect(await readDemoState()).toEqual(before)
})

test('demo task edits validate the merged date and reminder state', async () => {
  const task = await call('/tasks', 'POST', {
    title: '时间计划',
    starts_at: '2026-10-18T10:00:00Z',
    due_at: '2026-10-18T11:00:00Z',
    reminder_minutes: 0,
  })
  await expect(
    call(`/tasks/${task.id}`, 'PATCH', { due_at: '2026-10-18T09:00:00Z' })
  ).rejects.toThrow()
  expect(await call(`/tasks/${task.id}`, 'PATCH', { due_at: null })).toMatchObject({
    due_at: null,
    starts_at: '2026-10-18T10:00:00Z',
    reminder_minutes: 0,
  })
  await expect(call(`/tasks/${task.id}`, 'PATCH', { starts_at: null })).rejects.toThrow()
  const cleared = await call(`/tasks/${task.id}`, 'PATCH', { due_at: null, reminder_minutes: null })
  expect(cleared).toMatchObject({ due_at: null, reminder_minutes: null })
})
