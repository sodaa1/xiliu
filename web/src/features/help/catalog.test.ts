import { expect, test } from 'vitest'
import { guideArticles, guideFeatures, searchGuide } from './catalog'

test('every documented feature has a brief introduction and a real article section', () => {
  expect(guideArticles).toHaveLength(12)
  expect(guideFeatures.length).toBeGreaterThan(65)
  expect(new Set(guideFeatures.map((feature) => feature.id)).size).toBe(guideFeatures.length)
  for (const feature of guideFeatures) {
    expect(feature.summary.length).toBeGreaterThan(20)
    expect(
      guideArticles.find((article) => article.slug === feature.articleSlug)?.markdown
    ).toContain(`## ${feature.title}`)
    expect(feature.route).toMatch(/^\/(today|feed|inbox|knowledge|assistant|plans|settings|guide)/)
  }
})

test.each([
  ['批量归类', 'inbox'],
  ['停止回复', 'assistant'],
  ['Live2D', 'appearance-companion'],
  ['/compress', 'assistant'],
  ['备份', 'data-backup'],
])('search %s finds its feature and excerpt', (query, slug) => {
  const result = searchGuide(query)
  expect(result.some(({ feature }) => feature.articleSlug === slug)).toBe(true)
  expect(result.every(({ snippet }) => snippet.length > 0)).toBe(true)
})

test('empty search lists features and unknown words return no matches', () => {
  expect(searchGuide('')).toHaveLength(guideFeatures.length)
  expect(searchGuide('xx-no-matching-feature-xx')).toEqual([])
})
