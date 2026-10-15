import type { ModelBundle, PetForm } from './live2d-bundle'
import { mediaRequest } from '../today/background'
const eventName = 'xiliu-pet-models'
const channel =
  typeof window.BroadcastChannel === 'function' ? new window.BroadcastChannel(eventName) : null
type ModelInfo = {
  form: PetForm
  name: string
  manifestPath: string
  files: { path: string; url: string }[]
}
export async function readModelInfo(form: PetForm): Promise<ModelInfo | null> {
  const value = (await (await mediaRequest(`models/${form}`)).json()) as ModelInfo | null
  if (
    value !== null &&
    (!value ||
      typeof value.name !== 'string' ||
      typeof value.manifestPath !== 'string' ||
      !Array.isArray(value.files) ||
      value.files.some(
        (file) =>
          !file ||
          typeof file.path !== 'string' ||
          typeof file.url !== 'string' ||
          !file.url.startsWith('/api/appearance/model-assets/')
      ))
  )
    throw new Error('本机模型数据格式不正确，请重新导入。')
  return value
}
export async function readModel(form: PetForm): Promise<ModelBundle | undefined> {
  const value = await readModelInfo(form)
  if (!value) return undefined
  const files = []
  for (const file of value.files) {
    const response = await fetch(file.url)
    if (!response.ok) throw new Error('模型文件不完整，请重新导入。')
    files.push({ path: file.path, blob: await response.blob() })
  }
  return { ...value, files }
}
function base64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(',')[1])
    reader.onerror = () => reject(new Error('模型文件无法读取。'))
    reader.readAsDataURL(blob)
  })
}
export async function saveModel(form: PetForm, bundle?: ModelBundle) {
  if (bundle) {
    const files = []
    for (const file of bundle.files)
      files.push({ path: file.path, data_base64: await base64(file.blob) })
    await mediaRequest(`models/${form}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: bundle.name, manifestPath: bundle.manifestPath, files }),
    })
  } else await mediaRequest(`models/${form}`, { method: 'DELETE' })
  window.dispatchEvent(new Event(eventName))
  channel?.postMessage(form)
}
export function watchModels(callback: () => void) {
  window.addEventListener(eventName, callback)
  window.addEventListener('focus', callback)
  channel?.addEventListener('message', callback)
  return () => {
    window.removeEventListener(eventName, callback)
    window.removeEventListener('focus', callback)
    channel?.removeEventListener('message', callback)
  }
}
