import { createSeed } from './seed'
import { DemoError, type DemoState } from './types'

type Change<T> = (raw: unknown) => { state: DemoState; result: T }
export interface DemoPersistence {
  transact<T>(change: Change<T>): Promise<T>
}
const MAX_BYTES = 2 * 1024 * 1024
const copy = <T>(value: T): T => structuredClone(value)

function valid(raw: unknown): raw is DemoState {
  if (!raw || typeof raw !== 'object') return false
  const value = raw as DemoState
  return (
    value.schemaVersion === 1 &&
    Number.isInteger(value.revision) &&
    value.revision >= 0 &&
    typeof value.generation === 'string' &&
    typeof value.preferences?.preferences?.theme === 'string' &&
    Number.isInteger(value.preferences.revision) &&
    ['blank', 'builtin'].includes(value.background?.mode) &&
    ['feed', 'content', 'folders', 'tasks', 'conversations', 'messages'].every((key) => {
      const rows = value[key as 'content']
      return Array.isArray(rows) && rows.every((row) => row && typeof row.id === 'string')
    }) &&
    value.content.every(
      (item) =>
        typeof item.title === 'string' &&
        typeof item.content === 'string' &&
        Array.isArray(item.tags) &&
        ['inbox', 'knowledge'].includes(item.status)
    ) &&
    value.folders.every(
      (folder) => Array.isArray(folder.tags) && typeof folder.name === 'string'
    ) &&
    value.messages.every(
      (message) =>
        typeof message.content === 'string' && typeof message.conversation_id === 'string'
    )
  )
}

function indexedPersistence(): DemoPersistence | null {
  if (typeof indexedDB === 'undefined') return null
  let opening: Promise<IDBDatabase> | undefined
  function open() {
    return (opening ??= new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open('xiliu-demo-v1', 1)
      request.onupgradeneeded = () => request.result.createObjectStore('snapshots')
      request.onsuccess = () => {
        request.result.onversionchange = () => request.result.close()
        resolve(request.result)
      }
      request.onerror = () => reject(request.error)
      request.onblocked = () => reject(new Error('演示存储暂时被其他窗口占用。'))
    }))
  }
  return {
    async transact<T>(change: Change<T>) {
      const db = await open()
      return new Promise<T>((resolve, reject) => {
        const transaction = db.transaction('snapshots', 'readwrite')
        const table = transaction.objectStore('snapshots'),
          request = table.get('state')
        let result: T, failure: unknown
        request.onsuccess = () => {
          try {
            const next = change(request.result)
            result = next.result
            table.put(next.state, 'state')
          } catch (error) {
            failure = error
            transaction.abort()
          }
        }
        transaction.oncomplete = () => resolve(result)
        transaction.onabort = transaction.onerror = () =>
          reject(failure ?? transaction.error ?? new Error('演示存储不可用。'))
      })
    },
  }
}

export class DemoStore {
  private memory = createSeed()
  private accessed = false
  private listeners = new Set<() => void>()
  private channel: BroadcastChannel | undefined
  private queue: Promise<unknown> = Promise.resolve()
  notice = ''
  constructor(private backend: DemoPersistence | null = indexedPersistence()) {
    if (typeof window !== 'undefined' && typeof window.BroadcastChannel === 'function') {
      this.channel = new window.BroadcastChannel('xiliu-demo-updated')
      this.channel.onmessage = () => this.listeners.forEach((listener) => listener())
    }
  }
  get status(): 'persistent' | 'memory' {
    return this.backend ? 'persistent' : 'memory'
  }
  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }
  private run<T>(change: (draft: DemoState) => T, mutate: boolean): Promise<T> {
    const operation = async () => {
      const apply: Change<T> = (raw) => {
        if (raw !== undefined && !valid(raw)) this.notice = '演示存档无法读取，已恢复预置示例。'
        const state = valid(raw) ? copy(raw) : createSeed()
        const result = change(state)
        if (mutate) state.revision++
        if (new TextEncoder().encode(JSON.stringify(state)).byteLength > MAX_BYTES)
          throw new DemoError('演示空间已满，请删除部分资料或重置体验。', 'demo_storage_full')
        return { state, result: copy(result) }
      }
      let result: T
      if (this.backend) {
        try {
          result = await this.backend.transact(apply)
          this.accessed = true
        } catch (error) {
          if (error instanceof DemoError) throw error
          if (this.accessed)
            throw new DemoError(
              '演示修改未能保存，原内容已保留。请重试或重置体验。',
              'demo_storage_failed'
            )
          this.backend = null
          this.notice = '本次体验仅在当前页面保留，刷新后将恢复示例。'
          const next = apply(this.memory)
          this.memory = next.state
          result = next.result
        }
      } else {
        const next = apply(this.memory)
        this.memory = next.state
        result = next.result
      }
      if (mutate) {
        this.channel?.postMessage('changed')
        this.listeners.forEach((listener) => listener())
      }
      return result
    }
    const pending = this.queue.then(operation, operation)
    this.queue = pending.catch(() => {})
    return pending
  }
  read() {
    return this.run((state) => state, false)
  }
  mutate<T>(change: (draft: DemoState) => T) {
    return this.run(change, true)
  }
  reset() {
    return this.mutate((state) => {
      Object.assign(state, createSeed())
    })
  }
}
const store = new DemoStore()
export const readDemoState = () => store.read()
export const mutateDemo = <T>(change: (draft: DemoState) => T) => store.mutate(change)
export const resetDemoState = () => store.reset()
export const subscribeDemo = store.subscribe
export const getDemoStorageStatus = () => store.status
export const getDemoNotice = () => store.notice
