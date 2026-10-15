import { act, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { PetAvatar } from './PetAvatar'
const engine = vi.hoisted(() => ({
  destroy: vi.fn(),
  resize: vi.fn(),
  focus: vi.fn(),
  phase: vi.fn(),
}))
const mount = vi.hoisted(() => vi.fn())
vi.mock('../../lib/useReducedMotion', () => ({ useReducedMotion: () => false }))
vi.mock('./model-storage', () => ({
  readModel: async () => ({
    form: 'chibi',
    name: 'Pet',
    manifestPath: 'Pet/model3.json',
    files: [],
  }),
  watchModels: () => () => {},
}))
vi.mock('./live2d-runtime', () => ({ mountLive2D: mount }))
beforeEach(() => {
  vi.clearAllMocks()
  mount.mockResolvedValue(engine)
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    }
  )
})
afterEach(() => vi.unstubAllGlobals())
test('shows the live canvas after mounting and releases the renderer on unmount', async () => {
  const view = render(<PetAvatar />)
  await waitFor(() =>
    expect(view.container.querySelector('.pet-avatar')).toHaveAttribute('data-renderer', 'live2d')
  )
  expect(view.container.querySelector('img')).not.toBeVisible()
  expect(view.container.querySelector('canvas')).toBeVisible()
  view.unmount()
  expect(engine.destroy).toHaveBeenCalledTimes(1)
})
test('an asynchronous renderer that completes after unmount is immediately released', async () => {
  let finish!: (value: typeof engine) => void
  mount.mockReturnValue(
    new Promise((resolve) => {
      finish = resolve
    })
  )
  const view = render(<PetAvatar />)
  await waitFor(() => expect(mount).toHaveBeenCalledTimes(1))
  view.unmount()
  await act(async () => finish(engine))
  expect(engine.destroy).toHaveBeenCalledTimes(1)
})
test('WebGL failure preserves the original visible character', async () => {
  mount.mockRejectedValue(new Error('WebGL unavailable'))
  const error = vi.fn()
  const view = render(<PetAvatar onError={error} />)
  await waitFor(() => expect(error).toHaveBeenCalledWith('WebGL unavailable'))
  expect(view.container.querySelector('.pet-avatar')).toHaveAttribute('data-renderer', 'image')
  expect(view.container.querySelector('img')).toBeVisible()
})
