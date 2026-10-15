import { describe, expect, test, vi } from 'vitest'
import { backgroundMime, validateBackgroundSize, readBackgrounds } from './background'

const bytes = (...values: number[]) => new Uint8Array(values)
describe('background image validation', () => {
  test.each([
    [bytes(137, 80, 78, 71, 13, 10, 26, 10), 'image/png'],
    [bytes(255, 216, 255, 224), 'image/jpeg'],
    [new TextEncoder().encode('RIFF0000WEBP'), 'image/webp'],
    [new TextEncoder().encode('GIF89a'), 'image/gif'],
    [bytes(0, 0, 0, 32, 102, 116, 121, 112, 97, 118, 105, 102, 0, 0, 0, 0), 'image/avif'],
    [bytes(66, 77, 0, 0), 'image/bmp'],
  ])('recognizes actual file headers independent of name or supplied MIME', (header, mime) => {
    expect(backgroundMime(header)).toBe(mime)
  })
  test('rejects an HTML file disguised as an image', () => {
    expect(() => backgroundMime(new TextEncoder().encode('<html>not an image'))).toThrow(/格式/)
  })
  test('rejects empty and oversized files before decoding', () => {
    expect(() => validateBackgroundSize(0)).toThrow()
    expect(() => validateBackgroundSize(20 * 1024 * 1024 + 1)).toThrow(/20/)
    expect(() => validateBackgroundSize(20 * 1024 * 1024)).not.toThrow()
  })
})

test('malformed media service response is rejected instead of crashing the home', async () => {
  vi.stubGlobal('fetch', async () => Response.json([]))
  try {
    await expect(readBackgrounds()).rejects.toThrow(/格式/)
  } finally {
    vi.unstubAllGlobals()
  }
})
