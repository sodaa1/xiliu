import { expect, test } from 'vitest'
import { clothWeight, motionStep, restingMotion } from './standing-motion'

test('pins hands, forearms, face and legs while keeping the garment and hair tips movable', () => {
  for (const [x1, y1, x2, y2] of [
    [0.265, 0.485, 0.325, 0.56],
    [0.315, 0.435, 0.35, 0.485],
    [0.55, 0.19, 0.61, 0.235],
    [0.44, 0.09, 0.54, 0.155],
    [0.4, 0.6, 0.6, 0.9],
  ]) {
    for (let x = x1; x <= x2; x += 0.005)
      for (let y = y1; y <= y2; y += 0.005) expect(clothWeight(x, y)).toBe(0)
  }
  expect(clothWeight(0.73, 0.47)).toBeGreaterThan(0.2)
  expect(clothWeight(0.74, 0.18)).toBeGreaterThan(0.1)
})

test('fast movement has bounded lean and cloth displacement and settles after release', () => {
  let state = restingMotion()
  for (let i = 0; i < 90; i++) {
    state = motionStep(state, 1 / 30, 6000)
    expect(Math.abs(state.lean)).toBeLessThanOrEqual(0.027)
    expect(Math.abs(state.lag)).toBeLessThanOrEqual(8.5)
  }
  expect(state.lean).toBeLessThan(0)
  expect(state.lag).toBeLessThan(0)
  for (let i = 0; i < 180; i++) state = motionStep(state, 1 / 30, 0)
  expect(Math.abs(state.lean)).toBeLessThan(0.0001)
  expect(Math.abs(state.lag)).toBeLessThan(0.01)
})

test('inertia reverses with the direction of movement without enlarging the character', () => {
  const left = motionStep(restingMotion(), 1 / 30, -300)
  const right = motionStep(restingMotion(), 1 / 30, 300)
  expect(left.lean).toBe(-right.lean)
  expect(left.lag).toBe(-right.lag)
})
