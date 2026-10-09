import { useEffect, useRef } from 'react'
import { usePreferences } from '../../lib/preferences'

const TAU = Math.PI * 2
const INTRO_SECONDS = 2.6

// A fixed seed keeps the composition stable across resize and motion preferences.
function randomSequence() {
  let seed = 41927
  return () => {
    seed = (seed * 16807) % 2147483647
    return (seed - 1) / 2147483646
  }
}

export function GalaxyCanvas({ introComplete }: { introComplete: boolean }) {
  const { reducedMotion } = usePreferences()
  const canvas = useRef<HTMLCanvasElement>(null)
  const complete = useRef(introComplete)
  useEffect(() => {
    complete.current = introComplete
  }, [introComplete])

  useEffect(() => {
    const surface = canvas.current
    const context = surface?.getContext('2d', { alpha: true })
    if (!surface || !context) return
    const random = randomSequence()
    const stars = Array.from({ length: 180 }, () => ({
      x: random(),
      y: random(),
      size: 0.35 + random() * 1.1,
      phase: random() * TAU,
      brightness: 0.12 + random() * 0.4,
    }))
    // Inspired by Crystalized Ball's depth, dust and braided light; keep our
    // existing spiral composition and palette rather than introducing a new orb.
    const particles = Array.from({ length: 3400 }, (_, index) => ({
      arm: index % 4,
      position: random(),
      scatter: (random() - 0.5) * 0.5,
      speed: 0.018 + random() * 0.012,
      size: 0.55 + random() * 1.35,
      brightness: 0.28 + random() * 0.68,
      depth: random() * 2 - 1,
      phase: random() * TAU,
      tint: index % 3,
      startX: random() * 2 - 1,
      startY: random() * 2 - 1,
    }))
    const colors = ['160, 199, 255', '184, 155, 255', '225, 232, 255']
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let width = 1,
      height = 1,
      frame = 0,
      lastTime = 0
    let started = 0,
      hiddenAt = 0,
      pausedTime = 0

    function draw(timestamp: number) {
      if (!context) return
      if (!started) started = timestamp
      const elapsed =
        motion.matches || reducedMotion ? 8 : Math.max(0, (timestamp - started - pausedTime) / 1000)
      const raw =
        complete.current || motion.matches || reducedMotion
          ? 1
          : Math.min(1, elapsed / INTRO_SECONDS)
      const arrival = 1 - Math.pow(1 - raw, 3)
      const time = motion.matches || reducedMotion ? 8 : elapsed
      const cx = width * 0.5,
        cy = height * 0.46
      const radius = Math.max(width * 0.48, height * 0.57)
      const tilt = -0.24,
        spin = time * 0.13
      const cosine = Math.cos(tilt),
        sine = Math.sin(tilt)
      context.clearRect(0, 0, width, height)

      for (const star of stars) {
        const angle = time * 0.006
        const dx = (star.x - 0.5) * width * 1.15,
          dy = (star.y - 0.5) * height * 1.15
        const x = cx + dx * Math.cos(angle) - dy * Math.sin(angle)
        const y = cy + dx * Math.sin(angle) + dy * Math.cos(angle)
        const alpha = star.brightness * (0.75 + 0.25 * Math.sin(time * 0.7 + star.phase))
        context.fillStyle = `rgba(198, 212, 255, ${alpha})`
        context.beginPath()
        context.arc(x, y, star.size, 0, TAU)
        context.fill()
      }

      function point(position: number, arm: number, scatter = 0, depth = 0) {
        const distance = 18 + Math.pow(1 - position, 1.18) * radius
        const angle = (arm * TAU) / 4 + position * 7.4 + spin + scatter
        const perspective = 1 + depth * 0.085
        const x = Math.cos(angle) * distance * perspective,
          y =
            Math.sin(angle) * distance * 0.7 * perspective +
            Math.sin(time * 0.22 + angle) * depth * radius * 0.025
        return { x: cx + x * cosine - y * sine, y: cy + x * sine + y * cosine }
      }

      // Quiet haze sits beneath the crystalline strands, preserving readable type.
      context.globalCompositeOperation = 'lighter'
      for (let arm = 0; arm < 4; arm++) {
        context.beginPath()
        for (let step = 0; step <= 95; step++) {
          const p = point(step / 100, arm)
          if (!step) context.moveTo(p.x, p.y)
          else context.lineTo(p.x, p.y)
        }
        context.strokeStyle = `rgba(${colors[arm % 3]}, ${arrival * 0.018})`
        context.lineWidth = width < 600 ? 12 : 20
        context.stroke()
        for (let strand = 0; strand < 3; strand++) {
          context.beginPath()
          for (let step = 0; step <= 140; step++) {
            const position = step / 145
            const ripple =
              Math.sin(position * 38 + time * 0.48 + strand * 2.1) * 0.009 +
              Math.sin(position * 79 - time * 0.3 + arm) * 0.003
            const p = point(position, arm, ripple + (strand - 1) * 0.012)
            if (!step) context.moveTo(p.x, p.y)
            else context.lineTo(p.x, p.y)
          }
          context.strokeStyle = `rgba(${colors[(arm + strand) % 3]}, ${arrival * (strand === 1 ? 0.23 : 0.08)})`
          context.lineWidth = strand === 1 ? 0.8 : 0.4
          context.stroke()
        }
        // A small travelling flare brings the rim to life without a bright,
        // permanent circle competing with the wordmark.
        const lead = 0.1 + ((time * 0.035 + arm * 0.21) % 0.7)
        const start = point(lead - 0.06, arm)
        const end = point(lead + 0.06, arm)
        const flare = context.createLinearGradient(start.x, start.y, end.x, end.y)
        flare.addColorStop(0, `rgba(${colors[arm % 3]}, 0)`)
        flare.addColorStop(0.5, `rgba(${colors[arm % 3]}, ${arrival * 0.65})`)
        flare.addColorStop(1, `rgba(${colors[arm % 3]}, 0)`)
        context.beginPath()
        for (let step = 0; step <= 24; step++) {
          const position = lead - 0.06 + step * 0.005
          const p = point(position, arm, Math.sin(position * 38 + time * 0.48 + 2.1) * 0.009)
          if (!step) context.moveTo(p.x, p.y)
          else context.lineTo(p.x, p.y)
        }
        context.strokeStyle = flare
        context.shadowColor = `rgb(${colors[arm % 3]})`
        context.shadowBlur = 8
        context.lineWidth = 1.3
        context.stroke()
        context.shadowBlur = 0
      }

      const count = width < 600 ? 1400 : particles.length
      for (let index = 0; index < count; index++) {
        const particle = particles[index]
        const position = (particle.position + time * particle.speed) % 1
        const target = point(position, particle.arm, particle.scatter, particle.depth)
        const x = cx + particle.startX * radius * (1 - arrival) + (target.x - cx) * arrival
        const y = cy + particle.startY * radius * (1 - arrival) + (target.y - cy) * arrival
        const twinkle = 0.6 + 0.4 * Math.pow((1 + Math.sin(time * 0.8 + particle.phase)) / 2, 3)
        const depthLight = 0.58 + (particle.depth + 1) * 0.21
        const alpha =
          particle.brightness *
          twinkle *
          depthLight *
          Math.min(1, position * 8) *
          Math.min(1, (1 - position) * 12)
        const size = particle.size * (0.7 + (particle.depth + 1) * 0.25) * (0.65 + arrival * 0.35)
        context.fillStyle = `rgba(${colors[particle.tint]}, ${alpha})`
        // Tiny square facets are cheaper than blurred circles and keep dust crisp.
        context.fillRect(x - size / 2, y - size / 2, size, size)
        if (index % 89 === 0 && twinkle > 0.9 && arrival > 0.6) {
          context.strokeStyle = `rgba(225, 232, 255, ${alpha * 0.7})`
          context.lineWidth = 0.5
          context.beginPath()
          context.moveTo(x - size * 2.5, y)
          context.lineTo(x + size * 2.5, y)
          context.moveTo(x, y - size * 2.5)
          context.lineTo(x, y + size * 2.5)
          context.stroke()
        }
        if (index % 11 === 0 && arrival > 0.2) {
          const tail = point(
            Math.max(0, position - 0.009),
            particle.arm,
            particle.scatter,
            particle.depth
          )
          context.beginPath()
          context.moveTo(x, y)
          context.lineTo(x + (tail.x - target.x) * arrival, y + (tail.y - target.y) * arrival)
          context.strokeStyle = `rgba(${colors[particle.tint]}, ${alpha * 0.4})`
          context.lineWidth = particle.size * 0.7
          context.stroke()
        }
      }

      const glow = context.createRadialGradient(cx, cy, 0, cx, cy, radius * 0.32)
      glow.addColorStop(0, `rgba(200, 207, 255, ${arrival * 0.24})`)
      glow.addColorStop(0.16, `rgba(147, 116, 255, ${arrival * 0.15})`)
      glow.addColorStop(1, 'rgba(80, 88, 205, 0)')
      context.fillStyle = glow
      context.fillRect(0, 0, width, height)
      context.globalCompositeOperation = 'source-over'
    }

    function tick(timestamp: number) {
      // Cap at 30fps: enough for slow orbital motion without heating idle laptops.
      if (timestamp - lastTime >= 1000 / 30) {
        draw(timestamp)
        lastTime = timestamp
      }
      frame = requestAnimationFrame(tick)
    }
    function resize() {
      if (!surface || !context) return
      const bounds = surface.getBoundingClientRect()
      width = bounds.width
      height = bounds.height
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5)
      surface.width = Math.round(width * ratio)
      surface.height = Math.round(height * ratio)
      context.setTransform(ratio, 0, 0, ratio, 0, 0)
      draw(performance.now())
    }
    function updateMotion() {
      cancelAnimationFrame(frame)
      draw(performance.now())
      if (!(motion.matches || reducedMotion) && !document.hidden)
        frame = requestAnimationFrame(tick)
    }
    function visibility() {
      if (document.hidden) {
        hiddenAt = performance.now()
        cancelAnimationFrame(frame)
      } else {
        if (hiddenAt) pausedTime += performance.now() - hiddenAt
        hiddenAt = 0
        updateMotion()
      }
    }
    const observer = new ResizeObserver(resize)
    observer.observe(surface)
    motion.addEventListener('change', updateMotion)
    document.addEventListener('visibilitychange', visibility)
    resize()
    updateMotion()
    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      motion.removeEventListener('change', updateMotion)
      document.removeEventListener('visibilitychange', visibility)
    }
  }, [reducedMotion])

  return <canvas ref={canvas} className="launch-galaxy" aria-hidden="true" />
}
