const clamp = (v: number, limit: number) => Math.max(-limit, Math.min(limit, v))
function smooth(a: number, b: number, v: number) {
  const t = Math.max(0, Math.min(1, (v - a) / (b - a)))
  return t * t * (3 - 2 * t)
}
function ellipse(x: number, y: number, cx: number, cy: number, rx: number, ry: number) {
  return smooth(1, 1.35, Math.hypot((x - cx) / rx, (y - cy) / ry))
}
function arm(x: number, y: number, ax: number, ay: number, bx: number, by: number) {
  y *= 1.5
  ay *= 1.5
  by *= 1.5
  const dx = bx - ax,
    dy = by - ay
  const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
  return smooth(0.062, 0.098, Math.hypot(x - ax - dx * t, y - ay - dy * t))
}
// Coordinates belong only to the bundled standing artwork, never imported models.
// The pinned corridors include a mesh-cell margin around skin and facial features.
export function clothWeight(x: number, y: number) {
  const pinned =
    Math.min(
      arm(x, y, 0.347, 0.439, 0.282, 0.548),
      arm(x, y, 0.575, 0.205, 0.631, 0.318),
      ellipse(x, y, 0.49, 0.126, 0.105, 0.076),
      ellipse(x, y, 0.5, 0.3, 0.11, 0.115)
    ) *
    (1 - smooth(0.505, 0.555, y))
  const side = smooth(0.07, 0.22, Math.abs(x - 0.5))
  const hair = Math.exp(-Math.pow((y - 0.18) / 0.052, 2)) * side
  const hem = smooth(0.34, 0.465, y) * (1 - smooth(0.5, 0.555, y)) * side
  return (hair * 0.65 + hem) * pinned
}
export const restingMotion = () => ({ lag: 0, lagVelocity: 0, lean: 0, leanVelocity: 0 })
export type StandingPose = ReturnType<typeof restingMotion>
export function motionStep(pose: StandingPose, dt: number, speed: number): StandingPose {
  dt = Math.max(0, Math.min(dt, 1 / 30))
  const lagVelocity =
    pose.lagVelocity + ((clamp(-speed * 0.1, 8) - pose.lag) * 110 - pose.lagVelocity * 15) * dt
  const leanVelocity =
    pose.leanVelocity +
    ((clamp(-speed * 0.0007, 0.025) - pose.lean) * 100 - pose.leanVelocity * 17) * dt
  return {
    lag: pose.lag + lagVelocity * dt,
    lagVelocity,
    lean: pose.lean + leanVelocity * dt,
    leanVelocity,
  }
}

export function createStandingMotion(
  canvas: HTMLCanvasElement,
  image: HTMLImageElement,
  lean: (radians: number) => void,
  unavailable: () => void
) {
  const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false, antialias: true })
  if (!gl) throw new Error('WebGL unavailable')
  const shaders: WebGLShader[] = []
  let program: WebGLProgram | null = null,
    buffer: WebGLBuffer | null = null,
    texture: WebGLTexture | null = null
  let disposed = false,
    frame = 0,
    dragging = false,
    last = 0,
    pending = 0
  let previous: readonly [number, number] | undefined
  let pose = restingMotion()
  const shader = (type: number, source: string) => {
    const value = gl.createShader(type)!
    shaders.push(value)
    gl.shaderSource(value, source)
    gl.compileShader(value)
    if (!gl.getShaderParameter(value, gl.COMPILE_STATUS)) throw new Error('Standing shader failed')
    return value
  }
  const destroy = () => {
    disposed = true
    cancelAnimationFrame(frame)
    document.removeEventListener('visibilitychange', visibility)
    canvas.removeEventListener('webglcontextlost', lost)
    gl.deleteTexture(texture)
    gl.deleteBuffer(buffer)
    gl.deleteProgram(program)
    shaders.forEach((s) => gl.deleteShader(s))
    lean(0)
  }
  let draw: () => void = () => {}
  const tick = (now: number) => {
    frame = 0
    if (disposed || document.hidden) return
    const elapsed = (now - last) / 1000
    if (elapsed < 1 / 30) {
      frame = requestAnimationFrame(tick)
      return
    }
    last = now
    pose = motionStep(pose, elapsed, dragging ? pending / Math.max(elapsed, 1 / 30) : 0)
    pending = 0
    lean(pose.lean)
    draw()
    if (
      dragging ||
      Math.abs(pose.lag) > 0.01 ||
      Math.abs(pose.lagVelocity) > 0.01 ||
      Math.abs(pose.lean) > 0.0001 ||
      Math.abs(pose.leanVelocity) > 0.0001
    )
      frame = requestAnimationFrame(tick)
    else {
      pose = restingMotion()
      lean(0)
      draw()
    }
  }
  const start = () => {
    if (!disposed && !frame && !document.hidden) {
      last = performance.now()
      frame = requestAnimationFrame(tick)
    }
  }
  function visibility() {
    cancelAnimationFrame(frame)
    frame = 0
    pending = 0
    previous = undefined
    pose = restingMotion()
    lean(0)
    if (!document.hidden) {
      draw()
      if (dragging) start()
    }
  }
  function lost(event: Event) {
    event.preventDefault()
    destroy()
    unavailable()
  }
  try {
    const vs = shader(
      gl.VERTEX_SHADER,
      `attribute vec2 uv;attribute float weight;varying vec2 tex;uniform float inertia;
      void main(){tex=uv;vec2 p=uv+vec2(inertia*weight,0.);gl_Position=vec4(p.x*2.-1.,1.-p.y*2.,0.,1.);}`
    )
    const fs = shader(
      gl.FRAGMENT_SHADER,
      'precision mediump float;varying vec2 tex;uniform sampler2D picture;void main(){gl_FragColor=texture2D(picture,tex);}'
    )
    program = gl.createProgram()!
    gl.attachShader(program, vs)
    gl.attachShader(program, fs)
    gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error('Standing program failed')
    gl.useProgram(program)
    const vertices: number[] = [],
      nx = 60,
      ny = 100
    const vertex = (x: number, y: number) => vertices.push(x, y, clothWeight(x, y))
    for (let j = 0; j < ny; j++)
      for (let i = 0; i < nx; i++) {
        const u = i / nx,
          v = j / ny,
          U = (i + 1) / nx,
          V = (j + 1) / ny
        vertex(u, v)
        vertex(U, v)
        vertex(u, V)
        vertex(U, v)
        vertex(U, V)
        vertex(u, V)
      }
    buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW)
    const uv = gl.getAttribLocation(program, 'uv'),
      weight = gl.getAttribLocation(program, 'weight')
    gl.enableVertexAttribArray(uv)
    gl.vertexAttribPointer(uv, 2, gl.FLOAT, false, 12, 0)
    gl.enableVertexAttribArray(weight)
    gl.vertexAttribPointer(weight, 1, gl.FLOAT, false, 12, 8)
    texture = gl.createTexture()
    gl.bindTexture(gl.TEXTURE_2D, texture)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image)
    const inertia = gl.getUniformLocation(program, 'inertia')
    draw = () => {
      if (disposed) return
      gl.viewport(0, 0, canvas.width, canvas.height)
      gl.clearColor(0, 0, 0, 0)
      gl.clear(gl.COLOR_BUFFER_BIT)
      gl.uniform1f(inertia, pose.lag / 208)
      gl.drawArrays(gl.TRIANGLES, 0, vertices.length / 3)
    }
    canvas.addEventListener('webglcontextlost', lost)
    document.addEventListener('visibilitychange', visibility)
    return {
      resize(width: number, height: number) {
        const dpr = Math.min(window.devicePixelRatio || 1, 3)
        canvas.width = Math.max(1, Math.round(width * dpr))
        canvas.height = Math.max(1, Math.round(height * dpr))
        draw()
      },
      dragging(value: boolean) {
        dragging = value
        previous = undefined
        pending = 0
        start()
      },
      move(x: number, y: number) {
        if (dragging && previous) pending += x - previous[0] + (y - previous[1]) * 0.2
        previous = [x, y]
      },
      destroy,
    }
  } catch (error) {
    destroy()
    throw error
  }
}
