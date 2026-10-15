import { act, fireEvent, render, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { PetAvatar } from './PetAvatar'
const engine = vi.hoisted(() => ({
  destroy: vi.fn(),
  resize: vi.fn(),
  focus: vi.fn(),
  phase: vi.fn(),
  expression: vi.fn(),
}))
const mount = vi.hoisted(() => vi.fn())
const state = vi.hoisted(() => ({ reduced: false, model: true }))
vi.mock('../../lib/useReducedMotion', () => ({ useReducedMotion: () => state.reduced }))
vi.mock('./model-storage', () => ({
  readModel: async () =>
    state.model
      ? {
          form: 'chibi',
          name: 'Pet',
          manifestPath: 'Pet/model3.json',
          files: [],
        }
      : null,
  watchModels: () => () => {},
}))
vi.mock('./live2d-runtime', () => ({ mountLive2D: mount }))
beforeEach(() => {
  vi.clearAllMocks()
  state.reduced = false
  state.model = true
  mount.mockResolvedValue(engine)
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    }
  )
})
afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})
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

test('fallback expressions react to hover and drag while retaining the original body', () => {
  state.model = false
  const view = render(<PetAvatar dragging />)
  const base = view.container.querySelector('img')!
  const faces = view.container.querySelectorAll('.pet-face')
  faces.forEach((image) => fireEvent.load(image))
  expect(view.container.querySelector('.pet-face:not([hidden])')).toHaveAttribute(
    'src',
    '/companion/expressions/chibi-surprised.png'
  )
  expect(base).toHaveAttribute('src', '/companion/chibi.png')
  view.rerender(<PetAvatar />)
  fireEvent.pointerEnter(view.container.querySelector('.pet-avatar')!)
  expect(view.container.querySelector('.pet-face:not([hidden])')).toHaveAttribute(
    'src',
    '/companion/expressions/chibi-happy.png'
  )
  fireEvent.pointerLeave(view.container.querySelector('.pet-avatar')!)
  expect(view.container.querySelector('.pet-face:not([hidden])')).toBeNull()
  expect(base).toBeVisible()
})

test('idle fallback blinks briefly, pauses when hidden, and respects reduced motion', () => {
  vi.useFakeTimers()
  vi.spyOn(Math, 'random').mockReturnValue(0)
  let hidden = false
  vi.spyOn(document, 'hidden', 'get').mockImplementation(() => hidden)
  state.model = false
  const view = render(<PetAvatar />)
  view.container.querySelectorAll('.pet-face').forEach((image) => fireEvent.load(image))
  for (
    let elapsed = 0;
    elapsed < 10000 &&
    view.container.querySelector('.pet-avatar')?.getAttribute('data-expression') !== 'blink';
    elapsed += 100
  ) {
    act(() => vi.advanceTimersByTime(100))
  }
  expect(view.container.querySelector('.pet-face:not([hidden])')).toHaveAttribute(
    'src',
    '/companion/expressions/chibi-blink.png'
  )
  act(() => vi.advanceTimersByTime(500))
  expect(view.container.querySelector('.pet-face:not([hidden])')).toBeNull()
  hidden = true
  fireEvent(document, new Event('visibilitychange'))
  act(() => vi.advanceTimersByTime(20000))
  expect(view.container.querySelector('.pet-face:not([hidden])')).toBeNull()
  hidden = false
  fireEvent(document, new Event('visibilitychange'))
  state.reduced = true
  view.rerender(<PetAvatar />)
  act(() => vi.advanceTimersByTime(20000))
  expect(view.container.querySelector('.pet-face:not([hidden])')).toBeNull()
  view.unmount()
  expect(vi.getTimerCount()).toBe(0)
})

test('missing facial artwork leaves the visible original face intact', () => {
  state.model = false
  const view = render(<PetAvatar form="standing" dragging />)
  view.container.querySelectorAll('.pet-face').forEach((image) => fireEvent.error(image))
  expect(view.container.querySelector('.pet-face:not([hidden])')).toBeNull()
  expect(view.container.querySelector('img')).toHaveAttribute('src', '/companion/standing.png')
  expect(view.container.querySelector('img')).toBeVisible()
})

test('a loaded Live2D model receives the interaction expression instead of a raster overlay', async () => {
  const view = render(<PetAvatar dragging />)
  await waitFor(() =>
    expect(view.container.querySelector('.pet-avatar')).toHaveAttribute('data-renderer', 'live2d')
  )
  expect(engine.expression).toHaveBeenLastCalledWith('surprised')
  expect(view.container.querySelector('.pet-raster')).not.toBeVisible()
  view.rerender(<PetAvatar active />)
  await waitFor(() => expect(engine.expression).toHaveBeenLastCalledWith('happy'))
})

test('idle changes include a visible smile without requiring pointer interaction', () => {
  vi.useFakeTimers()
  vi.spyOn(Math, 'random').mockReturnValue(0)
  state.model = false
  const view = render(<PetAvatar />)
  view.container.querySelectorAll('.pet-face').forEach((image) => fireEvent.load(image))
  const expressions = new Set<string>()
  for (let elapsed = 0; elapsed < 20000; elapsed += 100) {
    act(() => vi.advanceTimersByTime(100))
    expressions.add(
      view.container.querySelector('.pet-face:not([hidden])')?.getAttribute('src') ?? 'neutral'
    )
  }
  expect(expressions).toContain('/companion/expressions/chibi-blink.png')
  expect(expressions).toContain('/companion/expressions/chibi-happy.png')
  expect(expressions).toContain('neutral')
})

test('a pointer resting on the character does not suppress idle blinking indefinitely', () => {
  vi.useFakeTimers()
  vi.spyOn(Math, 'random').mockReturnValue(0)
  state.model = false
  const view = render(<PetAvatar />)
  view.container.querySelectorAll('.pet-face').forEach((image) => fireEvent.load(image))
  fireEvent.pointerEnter(view.container.querySelector('.pet-avatar')!)
  expect(view.container.querySelector('.pet-face:not([hidden])')).toHaveAttribute(
    'src',
    '/companion/expressions/chibi-happy.png'
  )
  const expressions = new Set<string>()
  for (let elapsed = 0; elapsed < 20000; elapsed += 100) {
    act(() => vi.advanceTimersByTime(100))
    expressions.add(view.container.querySelector('.pet-avatar')!.getAttribute('data-expression')!)
  }
  expect(expressions).toContain('neutral')
  expect(expressions).toContain('blink')
})
