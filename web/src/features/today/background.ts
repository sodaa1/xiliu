export const BACKGROUND_ACCEPT =
  '.png,.jpg,.jpeg,.webp,.gif,.avif,.bmp,image/png,image/jpeg,image/webp,image/gif,image/avif,image/bmp'
export type HomeBackground = { mode: 'blank' | 'builtin' | 'custom'; selected: string | null }
export type BackgroundAsset = { id: string; name: string; blob: Blob }
export const blankBackground: HomeBackground = { mode: 'blank', selected: null }
export const builtinBackground = '/companion/home-background.png'
const changed = 'xiliu-home-background'
export function backgroundMime(bytes: Uint8Array): string {
  const text = new TextDecoder('ascii').decode(bytes)
  if ([137, 80, 78, 71, 13, 10, 26, 10].every((n, i) => bytes[i] === n)) return 'image/png'
  if (bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255) return 'image/jpeg'
  if (text.startsWith('GIF87a') || text.startsWith('GIF89a')) return 'image/gif'
  if (text.startsWith('RIFF') && text.slice(8, 12) === 'WEBP') return 'image/webp'
  if (text.slice(4, 8) === 'ftyp' && /avif|avis/.test(text.slice(8))) return 'image/avif'
  if (text.startsWith('BM')) return 'image/bmp'
  throw new Error('图片格式不支持，请选择 PNG、JPEG、WebP、GIF、AVIF 或 BMP。')
}
export function validateBackgroundSize(size: number) {
  if (!size) throw new Error('图片文件为空。')
  if (size > 20 * 1024 * 1024) throw new Error('背景图片不能超过 20 MiB。')
}
export async function mediaRequest(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`/api/appearance/${path}`, init)
  if (!response.ok) {
    let message = '本机素材未能保存或读取，请重试。'
    try {
      message = (await response.json()).error?.message ?? message
    } catch {
      /* Keep fallback message. */
    }
    throw new Error(message)
  }
  return response
}
export async function readBackgrounds(): Promise<{
  settings: HomeBackground
  images: { id: string; name: string; url: string }[]
}> {
  const value = await (await mediaRequest('backgrounds')).json()
  if (
    !value ||
    !value.settings ||
    !['blank', 'builtin', 'custom'].includes(value.settings.mode) ||
    !Array.isArray(value.images) ||
    value.images.some(
      (image: { id?: string; name?: string; url?: string }) =>
        !image ||
        typeof image.id !== 'string' ||
        typeof image.name !== 'string' ||
        typeof image.url !== 'string' ||
        !image.url.startsWith('/api/appearance/backgrounds/')
    )
  )
    throw new Error('本机背景数据格式不正确，请重试。')
  return value
}
export async function saveBackground(
  settings: HomeBackground,
  asset?: BackgroundAsset,
  remove?: string
) {
  if (asset)
    await mediaRequest(`backgrounds?name=${encodeURIComponent(asset.name)}`, {
      method: 'POST',
      body: asset.blob,
    })
  else if (remove)
    await mediaRequest(`backgrounds/${encodeURIComponent(remove)}`, { method: 'DELETE' })
  else
    await mediaRequest('backgrounds/selection', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    })
  window.dispatchEvent(new Event(changed))
}
export function watchBackground(callback: () => void) {
  window.addEventListener(changed, callback)
  window.addEventListener('focus', callback)
  return () => {
    window.removeEventListener(changed, callback)
    window.removeEventListener('focus', callback)
  }
}
function readBytes(blob: Blob): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as ArrayBuffer)
    reader.onerror = () => reject(new Error('无法读取图片。'))
    reader.readAsArrayBuffer(blob)
  })
}
export async function importBackground(file: File) {
  validateBackgroundSize(file.size)
  const mime = backgroundMime(new Uint8Array(await readBytes(file.slice(0, 64))))
  const blob = new Blob([file], { type: mime })
  const url = URL.createObjectURL(blob)
  try {
    await new Promise<void>((resolve, reject) => {
      const image = new Image()
      image.onload = () =>
        image.naturalWidth * image.naturalHeight > 32_000_000
          ? reject(new Error('图片分辨率过大，请使用不超过 3200 万像素的图片。'))
          : resolve()
      image.onerror = () => reject(new Error('图片已损坏，或当前系统无法解码此格式。'))
      image.src = url
    })
  } finally {
    URL.revokeObjectURL(url)
  }
  const id = crypto.randomUUID()
  await saveBackground({ mode: 'custom', selected: id }, { id, name: file.name, blob })
}
