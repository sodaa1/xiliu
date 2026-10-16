import { expect, test, vi } from 'vitest'
import { DemoStore, type DemoPersistence } from './store'
import { createSeed } from './seed'

test('independent demo state preserves relationships and returns snapshots', async () => {
  const store = new DemoStore(null)
  const first = await store.read()
  first.content[0].title = 'outside mutation'
  expect((await store.read()).content[0].title).not.toBe('outside mutation')
  expect(first.content.some((item) => item.folder_id === first.folders[0].id)).toBe(true)
  await store.mutate((draft) => {
    draft.tasks[0].completed = true
  })
  expect((await store.read()).tasks[0].completed).toBe(true)
  await store.reset()
  expect((await store.read()).tasks[0].completed).toBe(false)
  expect((await store.read()).generation).not.toBe(first.generation)
})
test('an oversized change is rejected without losing prior state', async () => {
  const store = new DemoStore(null)
  await expect(
    store.mutate((draft) => {
      draft.content[0].content = '大'.repeat(800000)
    })
  ).rejects.toThrow('空间')
  expect((await store.read()).content[0].content.length).toBeLessThan(800000)
})
test('storage unavailable on first access uses memory and never touches normal storage', async () => {
  const get = vi.spyOn(Storage.prototype, 'getItem')
  const remove = vi.spyOn(Storage.prototype, 'removeItem')
  const backend: DemoPersistence = {
    transact: async () => {
      throw new Error('denied')
    },
  }
  const store = new DemoStore(backend)
  await store.mutate((draft) => {
    draft.tasks[0].completed = true
  })
  expect(store.status).toBe('memory')
  expect((await store.read()).tasks[0].completed).toBe(true)
  expect(get).not.toHaveBeenCalled()
  expect(remove).not.toHaveBeenCalled()
  get.mockRestore()
  remove.mockRestore()
})
test('corrupt schemas restore usable seed data and announce recovery', async () => {
  let raw: unknown = { ...createSeed(), schemaVersion: 7 }
  const backend: DemoPersistence = {
    transact: async (change) => {
      const next = change(raw)
      raw = next.state
      return next.result
    },
  }
  const store = new DemoStore(backend)
  expect((await store.read()).schemaVersion).toBe(1)
  expect(store.notice).toContain('恢复')
})
test('a later persistence failure leaves the last committed state intact', async () => {
  let raw: unknown
  let fail = false
  const backend: DemoPersistence = {
    transact: async (change) => {
      if (fail) throw new Error('disk full')
      const next = change(raw)
      raw = next.state
      return next.result
    },
  }
  const store = new DemoStore(backend)
  const before = await store.read()
  fail = true
  await expect(
    store.mutate((draft) => {
      draft.tasks = []
    })
  ).rejects.toThrow('保存')
  fail = false
  expect((await store.read()).tasks).toEqual(before.tasks)
})
