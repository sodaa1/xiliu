import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { ArrowUpRight, BookOpen, Search } from 'lucide-react'
import { cleanHeading, guideArticles, guideFeatures, headingAnchor, searchGuide } from './catalog'
import './guide.css'

export function GuidePage() {
  const { slug } = useParams(),
    location = useLocation()
  const [query, setQuery] = useState('')
  const article = guideArticles.find((entry) => entry.slug === slug)
  useEffect(() => {
    setQuery('')
  }, [slug])
  useEffect(() => {
    if (location.hash) {
      const id = decodeURIComponent(location.hash.slice(1))
      document.getElementById(id)?.scrollIntoView?.({ block: 'start' })
    }
  }, [location.hash, slug])
  const results = query.trim() ? searchGuide(query) : null
  return (
    <section className="guide-page" aria-label="使用指南">
      <header className="guide-heading">
        <div>
          <span className="guide-eyebrow">息流 · 使用指南</span>
          <h1>知道能做什么，也知道怎么开始。</h1>
          <p>
            {guideFeatures.length} 项功能简介，Web 与桌面共用。按任务找入口，按步骤完成第一件事。
          </p>
        </div>
        <label className="guide-search">
          <Search size={18} />
          <input
            type="search"
            aria-label="搜索功能与指南"
            placeholder="搜索功能，例如：批量归类"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </header>
      <div className="guide-layout">
        <nav className="guide-nav" aria-label="指南目录">
          <Link to="/guide" aria-current={!slug ? 'page' : undefined}>
            <BookOpen size={16} /> 指南首页
          </Link>
          {guideArticles.map((entry) => (
            <Link
              key={entry.slug}
              to={`/guide/${entry.slug}`}
              aria-current={slug === entry.slug ? 'page' : undefined}
            >
              {entry.title}
            </Link>
          ))}
        </nav>
        <div className="guide-body">
          {results ? (
            <>
              <p role="status">找到 {results.length} 项功能</p>
              {!results.length && (
                <div className="guide-empty">
                  <h2>没有找到对应功能</h2>
                  <p>换个词试试，或返回完整功能目录。</p>
                  <button onClick={() => setQuery('')}>清空搜索</button>
                </div>
              )}
              {results.map(({ feature, snippet }) => (
                <article className="guide-result" key={feature.id}>
                  <Link
                    to={`/guide/${feature.articleSlug}#${feature.anchor}`}
                    onClick={() => setQuery('')}
                  >
                    {feature.title} <ArrowUpRight size={14} />
                  </Link>
                  <p>{snippet}</p>
                </article>
              ))}
            </>
          ) : article ? (
            <article className="guide-article">
              <Link className="guide-open" to={article.route}>
                前往 {article.title} <ArrowUpRight size={15} />
              </Link>
              <ReactMarkdown
                skipHtml
                components={{
                  h2: ({ children }) => {
                    const title = cleanHeading(String(children)),
                      feature = article.features.find((item) => item.title === title)
                    return (
                      <h2 id={headingAnchor(title)}>
                        {title}
                        {feature?.platform === 'desktop' && <small>桌面专属</small>}
                        {feature?.demo === 'unavailable' && <small>演示仅介绍</small>}
                      </h2>
                    )
                  },
                  a: ({ href, children }) =>
                    href?.startsWith('/') ? (
                      <Link to={href}>{children}</Link>
                    ) : (
                      <a
                        href={href && /^https?:\/\//.test(href) ? href : undefined}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {children}
                      </a>
                    ),
                }}
              >
                {article.markdown.replace(/<!--.*?-->/g, '')}
              </ReactMarkdown>
            </article>
          ) : (
            <>
              {slug && <p role="status">未找到这篇指南，请从目录重新选择。</p>}
              <section className="guide-start">
                <span className="guide-eyebrow">01 / 开始体验</span>
                <h2>从一条资讯，开始使用息流</h2>
                <p>
                  收藏到 Inbox，整理进 Knowledge，再带着资料向 Assistant 提问。每一步都能回到原文。
                </p>
                <Link className="guide-primary" to="/guide/getting-started">
                  阅读快速开始 <ArrowUpRight size={16} />
                </Link>
              </section>
              <div className="guide-chapters">
                {guideArticles.slice(1).map((entry) => (
                  <Link className="guide-chapter" key={entry.slug} to={`/guide/${entry.slug}`}>
                    <h3>
                      {entry.title}
                      <ArrowUpRight size={16} />
                    </h3>
                    <p>{entry.summary}</p>
                    <small>{entry.features.length} 项功能</small>
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
