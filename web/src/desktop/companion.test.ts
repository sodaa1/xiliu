import { expect, test } from 'vitest'
import { describeRuns, acceptSnapshot, DEFAULT_PET_HEIGHT } from './companion'

test('selected run wins and raw reasoning never crosses the desktop bridge', () => {
  const run = (cid: string, startedAt: number) => ({
    cid,
    startedAt,
    status: '正在检索\n知识库',
    steps: [],
    reasoning: 'private reasoning',
  })
  const summary = describeRuns({ a: run('a', 1), b: run('b', 2) }, {}, 'a')
  expect(summary).toEqual({ phase: 'thinking', cid: 'a', message: '正在检索 知识库', count: 2 })
  expect(JSON.stringify(summary)).not.toContain('private')
  expect(DEFAULT_PET_HEIGHT).toBe(96)
})

test('late status cannot replace a more recent snapshot and empty errors are not manufactured', () => {
  const latest = { revision: 9, phase: 'idle' as const, cid: null, message: '', count: 0 }
  expect(acceptSnapshot(latest, { ...latest, revision: 8, phase: 'thinking' })).toBe(latest)
  expect(describeRuns({}, {}, null)).toEqual({ phase: 'idle', cid: null, message: '', count: 0 })
})
