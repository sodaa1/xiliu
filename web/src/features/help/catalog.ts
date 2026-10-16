const sources = import.meta.glob('../../../../docs/wiki/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

const chapters = [
  ['getting-started', '快速开始', '/today'],
  ['feature-map', '功能地图', '/guide'],
  ['feed', '资讯', '/feed'],
  ['inbox', '收件箱', '/inbox'],
  ['knowledge', '知识库', '/knowledge'],
  ['assistant', '助手', '/assistant'],
  ['plans', '个人计划', '/plans'],
  ['models', '模型连接', '/settings?section=model'],
  ['automations-extensions', '自动任务与扩展', '/settings?section=automations'],
  ['appearance-companion', '外观与桌宠', '/settings?section=appearance'],
  ['data-backup', '数据与备份', '/settings?section=data'],
  ['faq', '常见问题', '/guide/faq'],
] as const

export interface GuideFeature {
  id: string
  title: string
  summary: string
  body: string
  articleSlug: string
  anchor: string
  route: string
  platform: 'all' | 'desktop'
  demo: 'interactive' | 'simulated' | 'unavailable'
}
export interface GuideArticle {
  slug: string
  title: string
  summary: string
  markdown: string
  route: string
  features: GuideFeature[]
}
export const headingAnchor = (title: string) =>
  title
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^\p{L}\p{N}\u4e00-\u9fff/-]/gu, '')
    .toLowerCase()
export const cleanHeading = (title: string) => title.replace(/<!--.*?-->/g, '').trim()
export const guideArticles: GuideArticle[] = chapters.map(([slug, title, route]) => {
  const markdown = (
    Object.entries(sources).find(([path]) => path.endsWith(`/${slug}.md`))?.[1] ?? ''
  ).replace(/\r\n/g, '\n')
  const features = markdown
    .split(/^## /m)
    .slice(1)
    .map((section) => {
      const [heading, ...lines] = section.split('\n')
      const body = lines.join('\n').trim()
      const name = cleanHeading(heading),
        anchor = headingAnchor(name)
      return {
        id: `${slug}/${anchor}`,
        title: name,
        summary: body.split('\n\n')[0],
        body,
        articleSlug: slug,
        anchor,
        route,
        platform: heading.includes('desktop') ? ('desktop' as const) : ('all' as const),
        demo: heading.includes('unavailable') ? ('unavailable' as const) : ('interactive' as const),
      }
    })
  return { slug, title, route, markdown, summary: markdown.split('\n\n')[1] ?? '', features }
})
export const guideFeatures = guideArticles.flatMap((article) => article.features)
export function searchGuide(query: string): { feature: GuideFeature; snippet: string }[] {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return guideFeatures
    .filter((feature) =>
      words.every((word) => `${feature.title} ${feature.body}`.toLowerCase().includes(word))
    )
    .map((feature) => {
      const index = words.length ? feature.body.toLowerCase().indexOf(words[0]) : 0
      return {
        feature,
        snippet:
          index > 100
            ? `…${feature.body.slice(Math.max(0, index - 35), index + 160)}`
            : feature.body.slice(0, 220),
      }
    })
}
