import { prepareModel, type ModelBundle } from './live2d-bundle'
import type { PetExpression } from './usePetExpression'
import type { CompanionStatus } from '../../desktop/companion'
let core: Promise<void> | undefined
function loadCore() {
  if ('Live2DCubismCore' in window) return Promise.resolve()
  if (!core)
    core = (async () => {
      const path = '/companion/live2d/live2dcubismcore.min.js'
      const response = await fetch(path, { method: 'HEAD' })
      if (!response.ok || response.headers.get('content-type')?.includes('text/html'))
        throw new Error('Live2D 运行库尚未安装，当前显示角色图片。')
      await new Promise<void>((resolve, reject) => {
        const script = document.createElement('script')
        const timeout = window.setTimeout(() => {
          script.remove()
          reject(new Error('Live2D 运行库加载超时。'))
        }, 15000)
        script.src = path
        script.onload = () => {
          clearTimeout(timeout)
          if ('Live2DCubismCore' in window) resolve()
          else reject(new Error('Live2D 运行库格式不正确。'))
        }
        script.onerror = () => {
          clearTimeout(timeout)
          script.remove()
          reject(new Error('无法加载 Live2D 运行库。'))
        }
        document.head.append(script)
      })
    })().catch((failure) => {
      core = undefined
      throw failure
    })
  return core
}
export async function mountLive2D(
  canvas: HTMLCanvasElement,
  bundle: ModelBundle,
  width: number,
  height: number,
  reduced: boolean
) {
  await loadCore()
  const [{ Application }, { Live2DModel }] = await Promise.all([
    import('pixi.js'),
    import('pixi-live2d-display/cubism4'),
  ])
  const prepared = await prepareModel(bundle)
  let app: InstanceType<typeof Application> | undefined
  let model: InstanceType<typeof Live2DModel> | undefined
  let released = false
  const dispose = () => {
    if (released) return
    released = true
    model?.destroy({ children: true, texture: true, baseTexture: true })
    app?.destroy(false)
    prepared.release()
  }
  try {
    app = new Application({
      view: canvas,
      width,
      height,
      resolution: Math.min(devicePixelRatio || 1, 2),
      autoDensity: true,
      backgroundAlpha: 0,
      antialias: true,
      autoStart: !reduced,
    })
    model = await Live2DModel.from(prepared.source, { autoInteract: false, autoUpdate: false })
    app.stage.addChild(model)
    const original = { width: model.width, height: model.height }
    model.anchor.set(0.5, 1)
    const resize = (w: number, h: number) => {
      if (released || !app || !model) return
      app.renderer.resize(w, h)
      model.scale.set(Math.min(w / original.width, h / original.height) * 0.98)
      model.position.set(w / 2, h)
      app.render()
    }
    resize(width, height)
    app.ticker.maxFPS = 30
    app.ticker.add(() => model?.update(app!.ticker.deltaMS))
    const groups = Object.keys(
      (prepared.source.FileReferences as { Motions?: Record<string, unknown> }).Motions ?? {}
    )
    const phase = (value: CompanionStatus['phase']) => {
      if (reduced || released || !model) return
      const names =
        value === 'thinking'
          ? ['thinking', 'idle']
          : value === 'success'
            ? ['success', 'tapbody', 'idle']
            : ['idle']
      const group = names
        .map((name) => groups.find((group) => group.toLowerCase().replaceAll('_', '') === name))
        .find(Boolean)
      if (group) void model.motion(group).catch(() => {})
    }
    const expressions =
      (
        prepared.source.FileReferences as {
          Expressions?: { Name: string }[]
        }
      ).Expressions ?? []
    const expression = (value: PetExpression) => {
      if (released || !model) return
      const manager = model.internalModel.motionManager.expressionManager
      if (value === 'neutral' || value === 'blink') {
        manager?.resetExpression()
        return
      }
      const names =
        value === 'happy'
          ? ['happy', 'smile', '笑顔', '微笑']
          : ['surprised', 'surprise', '驚き', '惊讶']
      const match = expressions.find((entry) => names.includes(entry.Name.toLowerCase()))
      if (match) void model.expression(match.Name).catch(() => {})
      else manager?.resetExpression()
    }
    const visibility = () => {
      if (!app || released) return
      if (document.hidden || reduced) app.stop()
      else app.start()
    }
    document.addEventListener('visibilitychange', visibility)
    visibility()
    return {
      resize,
      phase,
      expression,
      focus: (x: number, y: number) => {
        if (!reduced && !released) model?.focus(x, y)
      },
      destroy: () => {
        document.removeEventListener('visibilitychange', visibility)
        dispose()
      },
    }
  } catch (failure) {
    dispose()
    throw failure
  }
}
