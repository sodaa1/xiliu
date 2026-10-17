import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { useReducedMotion } from '../../lib/useReducedMotion'
import type { CompanionStatus } from '../../desktop/companion'
import type { PetForm } from './live2d-bundle'
import { readModel, watchModels } from './model-storage'
import type { mountLive2D } from './live2d-runtime'
import { usePetExpression } from './usePetExpression'
import { StandingMotion } from './StandingMotion'
const faces = ['blink', 'happy', 'surprised'] as const
export function PetAvatar({
  form = 'chibi',
  phase = 'idle',
  onError,
  dragging = false,
  active = false,
}: {
  form?: PetForm
  phase?: CompanionStatus['phase']
  onError?: (message: string) => void
  dragging?: boolean
  active?: boolean
}) {
  const root = useRef<HTMLSpanElement>(null),
    canvas = useRef<HTMLCanvasElement>(null)
  const controller = useRef<Awaited<ReturnType<typeof mountLive2D>> | null>(null)
  const [loaded, setLoaded] = useState('')
  const [revision, setRevision] = useState(0)
  const reduced = useReducedMotion()
  const renderKey = `${form}:${revision}:${reduced}`
  const ready = loaded === renderKey
  const [hover, setHover] = useState(false)
  const [available, setAvailable] = useState<Record<string, boolean>>({})
  const expression = usePetExpression({
    dragging,
    active,
    hover,
    phase,
    reduced,
    raster: !ready,
  })
  useEffect(() => watchModels(() => setRevision((value) => value + 1)), [])
  useEffect(() => {
    let disposed = false
    let local: Awaited<ReturnType<typeof mountLive2D>> | undefined
    let observer: ResizeObserver | undefined
    const start = async () => {
      const bundle = await readModel(form)
      if (!bundle || disposed || !canvas.current || !root.current) return
      const { mountLive2D } = await import('./live2d-runtime')
      if (disposed) return
      const rect = root.current!.getBoundingClientRect()
      const engine = await mountLive2D(
        canvas.current!,
        bundle,
        Math.max(1, rect.width),
        Math.max(1, rect.height),
        reduced
      )
      if (disposed) {
        engine.destroy()
        return
      }
      local = engine
      controller.current = engine
      setLoaded(renderKey)
      observer = new ResizeObserver((entries) => {
        const rect = entries[0]?.contentRect
        if (rect) engine.resize(Math.max(1, rect.width), Math.max(1, rect.height))
      })
      observer.observe(root.current!)
    }
    void start().catch((failure) => {
      if (!disposed) onError?.((failure as Error).message)
    })
    return () => {
      disposed = true
      observer?.disconnect()
      local?.destroy()
      if (controller.current === local) controller.current = null
    }
  }, [form, revision, reduced, renderKey, onError])
  useEffect(() => {
    if (ready) controller.current?.phase(phase)
  }, [phase, ready])
  useEffect(() => {
    if (ready) controller.current?.dragging(dragging)
  }, [dragging, ready])
  useEffect(() => {
    if (ready) controller.current?.expression(expression)
  }, [expression, ready])
  return (
    <span
      ref={root}
      className="pet-avatar"
      data-renderer={ready ? 'live2d' : 'image'}
      data-expression={expression}
      data-form={form}
      style={
        {
          '--pet-aspect': form === 'standing' ? 2 / 3 : 1,
          '--pet-inverse-aspect': form === 'standing' ? 1.5 : 1,
        } as CSSProperties
      }
      onPointerEnter={() => setHover(true)}
      onPointerLeave={() => setHover(false)}
      onPointerMove={(event) => {
        const rect = event.currentTarget.getBoundingClientRect()
        controller.current?.focus(event.clientX - rect.left, event.clientY - rect.top)
      }}
    >
      <span className="pet-raster" hidden={ready}>
        {form === 'standing' ? (
          <StandingMotion dragging={dragging} reduced={reduced} enabled={!ready} />
        ) : (
          <img src={`/companion/${form}.png`} alt="" draggable={false} />
        )}
        {faces.map((face) => {
          const key = `${form}-${face}`
          return (
            <img
              key={key}
              className="pet-face"
              src={`/companion/expressions/${key}.png`}
              alt=""
              draggable={false}
              hidden={expression !== face || !available[key]}
              onLoad={() => setAvailable((old) => ({ ...old, [key]: true }))}
              onError={() => setAvailable((old) => ({ ...old, [key]: false }))}
            />
          )
        })}
      </span>
      <canvas
        ref={canvas}
        aria-hidden="true"
        style={{ visibility: ready ? 'visible' : 'hidden' }}
      />
    </span>
  )
}
