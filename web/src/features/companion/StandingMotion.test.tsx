import { fireEvent, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { StandingMotion } from './StandingMotion'

const mocks = vi.hoisted(() => ({
  native: false,
  mount: vi.fn(),
  listen: vi.fn(),
  engine: { resize: vi.fn(), dragging: vi.fn(), move: vi.fn(), destroy: vi.fn() },
}))
vi.mock('./standing-motion', () => ({ createStandingMotion: mocks.mount }))
vi.mock('../../desktop/bridge', () => ({ isDesktop: () => mocks.native }))
vi.mock('../../desktop/companion', () => ({ companionListen: mocks.listen }))
beforeEach(() => {
  vi.clearAllMocks()
  mocks.native = false
  mocks.mount.mockReturnValue(mocks.engine)
  vi.stubGlobal(
    'Image',
    class {
      onload: (() => void) | null = null
      set src(_value: string) {
        queueMicrotask(() => this.onload?.())
      }
    }
  )
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    }
  )
})
afterEach(() => {
  vi.unstubAllGlobals()
})

test('replaces the base only after renderer readiness and releases it on unmount', async () => {
  const view = render(<StandingMotion dragging={false} reduced={false} enabled />)
  expect(view.container.querySelector('img')).toBeVisible()
  await waitFor(() => expect(view.container.querySelector('canvas')).toBeVisible())
  expect(view.container.querySelector('img')).not.toBeVisible()
  view.rerender(<StandingMotion dragging reduced={false} enabled />)
  expect(mocks.engine.dragging).toHaveBeenLastCalledWith(true)
  fireEvent.pointerMove(window, { clientX: 50, clientY: 60 })
  expect(mocks.engine.move).toHaveBeenCalled()
  view.unmount()
  expect(mocks.engine.destroy).toHaveBeenCalledOnce()
})

test('graphics failure and reduced motion preserve the original body', async () => {
  mocks.mount.mockImplementation(() => {
    throw new Error('No WebGL')
  })
  const view = render(<StandingMotion dragging reduced={false} enabled />)
  await waitFor(() => expect(mocks.mount).toHaveBeenCalledOnce())
  expect(view.container.querySelector('img')).toBeVisible()
  expect(view.container.querySelector('canvas')).not.toBeVisible()
  view.rerender(<StandingMotion dragging reduced enabled />)
  expect(view.container.querySelector('img')).toBeVisible()
  expect(mocks.mount).toHaveBeenCalledOnce()
})

test('native movement uses actual window position events and removes the subscription', async () => {
  mocks.native = true
  vi.stubGlobal('devicePixelRatio', 2)
  const stop = vi.fn()
  let position!: (value: [number, number]) => void
  mocks.listen.mockImplementation(async (_name, handler) => {
    position = handler
    return stop
  })
  const view = render(<StandingMotion dragging reduced={false} enabled />)
  await waitFor(() => expect(view.container.querySelector('canvas')).toBeVisible())
  expect(mocks.listen).toHaveBeenCalledWith('position', expect.any(Function))
  position([400, 600])
  expect(mocks.engine.move).toHaveBeenLastCalledWith(200, 300)
  view.unmount()
  expect(stop).toHaveBeenCalledOnce()
})
