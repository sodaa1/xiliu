import { publicAsset } from '../../lib/deployment'
export type PetForm = 'chibi' | 'standing'
export type ModelBundle = {
  form: PetForm
  name: string
  manifestPath: string
  files: { path: string; blob: Blob }[]
}
type Manifest = { Version?: number; FileReferences?: Record<string, unknown> }
export function modelAssetPath(manifestPath: string, reference: string) {
  let decoded: string
  try {
    decoded = decodeURIComponent(reference).replaceAll('\\', '/')
  } catch {
    throw new Error('模型文件路径无效。')
  }
  if (
    /^[a-z][a-z0-9+.-]*:|^\//i.test(decoded) ||
    /[?#]/.test(decoded) ||
    decoded.includes(String.fromCharCode(0))
  )
    throw new Error('模型只能引用所选文件夹内的文件。')
  const root = manifestPath.split('/')[0]
  const parts = manifestPath.split('/').slice(0, -1)
  for (const part of decoded.split('/')) {
    if (part === '..') {
      if (parts.length <= 1) throw new Error('模型文件不能超出所选文件夹。')
      parts.pop()
    } else if (part && part !== '.') parts.push(part)
  }
  if (parts[0] !== root) throw new Error('模型路径无效。')
  return parts.join('/')
}
const fileKeys = new Set(['Moc', 'Physics', 'Pose', 'UserData', 'DisplayInfo', 'File', 'Sound'])
export function mapModelReferences(
  value: unknown,
  map: (path: string) => string,
  key = ''
): unknown {
  if (typeof value === 'string' && fileKeys.has(key)) return map(value)
  if (key === 'Textures' && Array.isArray(value))
    return value.map((path) => {
      if (typeof path !== 'string') throw new Error('模型贴图路径无效。')
      return map(path)
    })
  if (Array.isArray(value)) return value.map((item) => mapModelReferences(item, map))
  if (value && typeof value === 'object')
    return Object.fromEntries(
      Object.entries(value).map(([name, item]) => [name, mapModelReferences(item, map, name)])
    )
  return value
}
export function validateModelBundle(
  manifest: unknown,
  paths: string[],
  manifestPath: string
): string[] {
  const model = manifest as Manifest | null
  const refs = model?.FileReferences
  if (
    model?.Version !== 3 ||
    !refs ||
    typeof refs.Moc !== 'string' ||
    !Array.isArray(refs.Textures) ||
    !refs.Textures.length
  )
    throw new Error('请选择有效的 Cubism 3/4 模型导出文件夹。')
  const required: string[] = []
  mapModelReferences(refs, (reference) => {
    const path = modelAssetPath(manifestPath, reference)
    if (!paths.includes(path)) throw new Error(`模型缺少文件：${reference}`)
    required.push(path)
    return reference
  })
  return [...new Set(required)]
}
export function readModelText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('无法读取模型文件。'))
    reader.readAsText(blob)
  })
}
export async function collectModelBundle(form: PetForm, files: File[]): Promise<ModelBundle> {
  if (files.length > 1000 || files.reduce((sum, file) => sum + file.size, 0) > 200 * 1024 * 1024)
    throw new Error('模型文件夹最多 1000 个文件、200 MiB。')
  const manifests = files.filter((file) => file.name.endsWith('.model3.json'))
  if (manifests.length !== 1) throw new Error('请选择只包含一个 .model3.json 的模型文件夹。')
  const pathOf = (file: File) => file.webkitRelativePath || `model/${file.name}`
  const paths = files.map(pathOf)
  if (new Set(paths).size !== paths.length) throw new Error('模型中存在重复文件路径。')
  const manifestPath = pathOf(manifests[0])
  const manifest: unknown = JSON.parse(await readModelText(manifests[0]))
  const required = validateModelBundle(manifest, paths, manifestPath)
  return {
    form,
    name: manifests[0].name.replace('.model3.json', ''),
    manifestPath,
    files: files
      .filter((file) => required.includes(pathOf(file)) || file === manifests[0])
      .map((file) => ({ path: pathOf(file), blob: file })),
  }
}
export async function prepareModel(bundle: ModelBundle) {
  const entry = bundle.files.find((file) => file.path === bundle.manifestPath)
  if (!entry) throw new Error('模型配置缺失，请重新导入。')
  const manifest: unknown = JSON.parse(await readModelText(entry.blob))
  validateModelBundle(
    manifest,
    bundle.files.map((file) => file.path),
    bundle.manifestPath
  )
  const urls = new Map<string, string>()
  try {
    const source = mapModelReferences(manifest, (reference) => {
      const path = modelAssetPath(bundle.manifestPath, reference)
      if (!urls.has(path))
        urls.set(path, URL.createObjectURL(bundle.files.find((file) => file.path === path)!.blob))
      return urls.get(path)!
    }) as Record<string, unknown>
    source.url = `${location.origin}${publicAsset('companion/live2d/local.model3.json')}`
    return { source, release: () => urls.forEach(URL.revokeObjectURL) }
  } catch (failure) {
    urls.forEach(URL.revokeObjectURL)
    throw failure
  }
}
