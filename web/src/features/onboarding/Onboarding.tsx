import { useSyncExternalStore } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Check, X } from 'lucide-react'
import { workspaceApi } from '../../lib/workspace-api'
import { isDemo } from '../../lib/runtime-mode'
import { guideArticles } from '../help/catalog'
import { dismissGuide, getGuideProgress, resetGuide, startGuide, subscribeGuide } from './progress'
import './onboarding.css'

export function Onboarding() {
  const progress = useSyncExternalStore(subscribeGuide, getGuideProgress),
    navigate = useNavigate()
  const item = useQuery({
    queryKey: ['guide-content', progress.itemId],
    queryFn: () => workspaceApi.contentItem(progress.itemId!),
    enabled: progress.status === 'active' && !!progress.itemId,
    retry: false,
  })
  if (progress.status === 'dismissed') return null
  const steps = [
    ['收藏一条资讯', '在资讯选择感兴趣的资讯，点击收藏，把它收进收件箱。'],
    ['添加标签，再归档', '打开刚收藏的资料，添加标签并保存到知识库。已有标签也可以保留。'],
    [
      '带着资料提问',
      isDemo
        ? '在这份资料上点击引用提问，发送一个问题，体验带引用的演示回复。'
        : '在这份资料上点击引用提问。发送前请先配置模型，回复成功后完成上手。',
    ],
  ]
  const target =
    progress.step === 0
      ? '/feed'
      : progress.step === 1
        ? `/inbox?item=${encodeURIComponent(progress.itemId ?? '')}`
        : `/knowledge?folder=all&document=${encodeURIComponent(progress.itemId ?? '')}`
  return (
    <section className="onboarding" aria-label="快速上手">
      <button className="onboarding-close" aria-label="关闭引导" onClick={dismissGuide}>
        <X size={16} />
      </button>
      {progress.status === 'new' ? (
        <>
          <small>第一次使用息流</small>
          <h2>用一条资讯，走通你的信息流。</h2>
          <p>收藏 → 整理 → 引用提问。三步了解主要流程，也可以先看看所有功能。</p>
          <div className="onboarding-actions">
            <button
              onClick={() => {
                startGuide()
                navigate('/feed')
              }}
            >
              开始快速上手 <ArrowRight size={14} />
            </button>
            <Link to="/guide" onClick={dismissGuide}>
              浏览所有功能
            </Link>
            <button className="onboarding-quiet" onClick={dismissGuide}>
              稍后再看
            </button>
          </div>
        </>
      ) : progress.status === 'completed' ? (
        <>
          <small>
            <Check size={13} /> 已完成三步上手
          </small>
          <h2>发现、整理、提问，已经连起来了。</h2>
          <p>接下来可以创建个人计划，或打开指南了解自动任务、模型与桌宠。</p>
          <div className="onboarding-actions">
            <Link to="/guide">继续探索全部功能 →</Link>
            <button className="onboarding-quiet" onClick={dismissGuide}>
              完成并收起
            </button>
          </div>
        </>
      ) : (
        <>
          <small>快速上手 · 第 {progress.step + 1} / 3 步</small>
          <h2>{steps[progress.step][0]}</h2>
          <p>{steps[progress.step][1]}</p>
          <div className="onboarding-actions">
            <Link to={target}>
              前往当前步骤 <ArrowRight size={14} />
            </Link>
            {!isDemo && progress.step === 2 && <Link to="/settings?section=model">配置模型</Link>}
            <Link to="/guide/getting-started">查看步骤说明</Link>
            <button className="onboarding-quiet" onClick={dismissGuide}>
              稍后继续
            </button>
          </div>
          {item.error && (
            <p role="status">
              这份资料暂不可用。可以刷新重试，或
              <button
                className="onboarding-quiet"
                onClick={() => {
                  resetGuide()
                  startGuide()
                  navigate('/feed')
                }}
              >
                重新选择资讯
              </button>
              。
            </p>
          )}
        </>
      )}
    </section>
  )
}

export function PageHelp() {
  const { pathname } = useLocation()
  const slug = (
    {
      '/today': 'getting-started',
      '/feed': 'feed',
      '/inbox': 'inbox',
      '/knowledge': 'knowledge',
      '/assistant': 'assistant',
      '/plans': 'plans',
    } as Record<string, string>
  )[pathname]
  const article = guideArticles.find((article) => article.slug === slug)
  if (!article) return null
  return (
    <div className="page-guide-hint">
      <span>{article.summary}</span>
      <Link to={`/guide/${article.slug}`}>
        了解这里的功能 <ArrowRight size={12} />
      </Link>
    </div>
  )
}
