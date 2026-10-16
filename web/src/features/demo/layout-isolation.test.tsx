import { act, renderHook } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { usePanelSize } from '../../lib/usePanelSize'

vi.mock('../../lib/runtime-mode', () => ({ isDemo: true }))

test('demo resizing neither reads nor changes normal workspace layout', () => {
  localStorage.clear()
  localStorage.setItem('xiliu-composer-height-v3', '95')
  const { result } = renderHook(() => usePanelSize('xiliu-composer-height-v3', 40, 98, 40))
  expect(result.current[0]).toBe(40)
  act(() => result.current[1](70))
  expect(localStorage.getItem('xiliu-composer-height-v3')).toBe('95')
  expect(localStorage.getItem('xiliu-demo-composer-height-v3')).toBe('70')
})

test('demo composer import preserves normal legacy layout keys', async () => {
  localStorage.setItem('xiliu-composer-height', '90')
  localStorage.setItem('xiliu-composer-height-v2', '91')
  await import('../assistant/Composer')
  expect(localStorage.getItem('xiliu-composer-height')).toBe('90')
  expect(localStorage.getItem('xiliu-composer-height-v2')).toBe('91')
})
