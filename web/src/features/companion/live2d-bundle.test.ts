import { expect, test } from 'vitest'
import { validateModelBundle } from './live2d-bundle'
const model = {
  Version: 3,
  FileReferences: {
    Moc: 'Pet.moc3',
    Textures: ['textures/texture_00.png'],
    Motions: { Idle: [{ File: 'motions/idle.motion3.json' }] },
  },
}
const paths = [
  'Pet/Pet.model3.json',
  'Pet/Pet.moc3',
  'Pet/textures/texture_00.png',
  'Pet/motions/idle.motion3.json',
]
test('resolves local model, texture and motion references in the selected folder', () => {
  expect(validateModelBundle(model, paths, paths[0])).toEqual([
    'Pet/Pet.moc3',
    'Pet/textures/texture_00.png',
    'Pet/motions/idle.motion3.json',
  ])
})
test('rejects incomplete texture imports before loading the renderer', () => {
  expect(() =>
    validateModelBundle(
      model,
      paths.filter((path) => !path.includes('texture_00')),
      paths[0]
    )
  ).toThrow(/texture_00/)
})
test.each([
  'https://example.org/texture.png',
  '/private/texture.png',
  '../../secret.png',
  '%2e%2e/%2e%2e/secret.png',
  'C:\\private.png',
])('rejects external or escaping model references: %s', (texture) => {
  expect(() =>
    validateModelBundle(
      { ...model, FileReferences: { ...model.FileReferences, Textures: [texture] } },
      paths,
      paths[0]
    )
  ).toThrow()
})
test('rejects unsupported and malformed model manifests', () => {
  for (const manifest of [
    null,
    { Version: 2 },
    { Version: 3, FileReferences: { Moc: 'Pet.moc3', Textures: [] } },
  ])
    expect(() => validateModelBundle(manifest, paths, paths[0])).toThrow(/模型/)
})
