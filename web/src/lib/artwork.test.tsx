import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { selectArtwork, topicForContent, useThemedArtwork } from './artwork'
import { ArtworkImage } from '../components/ArtworkImage'
import { FeedCover } from '../features/feed/FeedDiscovery'

beforeEach(() => sessionStorage.clear())
afterEach(() => vi.restoreAllMocks())

test('artwork topics follow content themes and never repeat the previous image', () => {
  expect(topicForContent('RAG 和 TypeScript 开发', ['AI'], 'reading')).toBe('technology')
  expect(topicForContent('产品界面设计', [], 'reading')).toBe('design')
  expect(topicForContent('城市建筑摄影', [], 'reading')).toBe('urban')
  expect(topicForContent('山间徒步', [], 'reading')).toBe('nature')
  expect(topicForContent('一本书的读书笔记', [], 'reading')).toBe('reading')
  for (const topic of ['nature', 'reading', 'technology', 'design', 'urban'] as const) {
    const first = selectArtwork(topic, undefined, 0)
    const next = selectArtwork(topic, first.id, 0)
    expect(next.id).not.toBe(first.id)
    expect(next.topic).toBe(topic)
    expect(next.variants.at(-1)!.width).toBeGreaterThanOrEqual(1920)
  }
})

test('a visit stays visually stable while a later visit rotates even with identical random input', () => {
  vi.spyOn(Math, 'random').mockReturnValue(0)
  function Probe({ tick }: { tick: number }) {
    const image = useThemedArtwork('reading', 'test-stable-visit')
    return (
      <output data-testid="picked" data-image={image.id}>
        {tick}
      </output>
    )
  }
  const first = render(<Probe tick={0} />)
  const id = screen.getByTestId('picked').dataset.image
  first.rerender(<Probe tick={1} />)
  expect(screen.getByTestId('picked').dataset.image).toBe(id)
  first.unmount()
  render(<Probe tick={2} />)
  expect(screen.getByTestId('picked').dataset.image).not.toBe(id)
})

test('original article images stay first and fail over to local responsive photography', () => {
  const view = render(
    <ArtworkImage
      topic="technology"
      slot="test-source"
      remote="https://example.org/source.jpg"
      data-testid="cover"
    />
  )
  const image = screen.getByTestId('cover') as HTMLImageElement
  expect(image.src).toBe('https://example.org/source.jpg')
  fireEvent.error(image)
  expect(image.getAttribute('src')).toMatch(/^\/artwork\//)
  expect(image.getAttribute('srcset')).toContain('1920w')
  view.rerender(
    <ArtworkImage
      topic="technology"
      slot="test-source"
      remote="https://example.org/next.jpg"
      data-testid="cover"
    />
  )
  expect(screen.getByTestId('cover')).toHaveAttribute('src', 'https://example.org/next.jpg')
})

test('rotation remains usable when browser storage is unavailable', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('Storage blocked')
  })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Storage blocked')
  })
  expect(() =>
    render(<ArtworkImage topic="nature" slot="test-blocked-storage" data-testid="offline" />)
  ).not.toThrow()
  expect(screen.getByTestId('offline')).toHaveAttribute('srcset', expect.stringContaining('3840w'))
})

test('featured and list covers do not overwrite each other’s rotation history', () => {
  vi.spyOn(Math, 'random').mockReturnValueOnce(0).mockReturnValueOnce(0.99).mockReturnValue(0)
  const item = {
    id: 'test-duplicate-slots',
    title: 'AI research',
    tags: ['AI'],
    metadata: {},
  } as Parameters<typeof FeedCover>[0]['item']
  const view = render(
    <>
      <FeedCover item={item} featured />
      <FeedCover item={item} />
    </>
  )
  const first = view.container.querySelector('img')!.dataset.artwork
  view.unmount()
  const second = render(<FeedCover item={item} featured />)
  expect(second.container.querySelector('img')!.dataset.artwork).not.toBe(first)
})
