const sources = import.meta.glob('../../../../docs/wiki/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

const chapters = [
  ['getting-started', '快速开始', '/today'],
  ['feature-map', '功能地图', '/guide'],
  ['feed', 'Feed 资讯', '/feed'],
  ['inbox', 'Inbox 收件箱', '/inbox'],
  ['knowledge', 'Knowledge 知识库', '/knowledge'],
  ['assistant', 'Assistant', '/assistant'],
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
  const markdown = Object.entries(sources).find(([path]) => path.endsWith(`/${slug}.md`))?.[1] ?? ''
  const features = [...markdown.matchAll(/^## (.+)\n+([\s\S]*?)(?=\n## |$)/gm)].map((match) => {
    const name = cleanHeading(match[1]),
      anchor = headingAnchor(name)
    return {
      id: `${slug}/${anchor}`,
      title: name,
      summary: match[2].trim().split('\n\n')[0],
      articleSlug: slug,
      anchor,
      route,
      platform: match[1].includes('desktop') ? ('desktop' as const) : ('all' as const),
      demo: match[1].includes('unavailable') ? ('unavailable' as const) : ('interactive' as const),
    }
  })
  return { slug, title, route, markdown, summary: markdown.split('\n\n')[1] ?? '', features }
})
export const guideFeatures = guideArticles.flatMap((article) => article.features)
export function searchGuide(query: string): { feature: GuideFeature; snippet: string }[] {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return guideFeatures
    .filter((feature) =>
      words.every((word) => `${feature.title} ${feature.summary}`.toLowerCase().includes(word))
    )
    .map((feature) => ({ feature, snippet: feature.summary }))
}
