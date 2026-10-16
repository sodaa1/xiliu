import { beforeEach, expect, test } from 'vitest'
import { handleDemoRequest } from './handler'
import { readDemoState, resetDemoState } from './store'

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
