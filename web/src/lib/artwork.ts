import { useEffect, useMemo, useState } from 'react'
import catalog from './artwork-catalog.json'

export type ArtworkTopic = 'nature' | 'reading' | 'technology' | 'design' | 'urban'
export type Artwork = (typeof catalog)[number]
const storageKey = 'xiliu-artwork-rotation-v1'
const remembered = new Map<string, string>()

export function topicForContent(
  title: string,
  tags: string[] = [],
  fallback: ArtworkTopic = 'reading'
): ArtworkTopic {
  const text = `${tags.join(' ')} ${title}`
  if (/设计|创意|产品|界面|\b(design|creative|ux|ui|figma)\b/i.test(text)) return 'design'
  if (
    /科技|技术|编程|开发|模型|人工智能|\b(ai|rag|mcp|llm|github|react|typescript|python|code|tech)\b/i.test(
      text
    )
  )
    return 'technology'
  if (/城市|建筑|旅行|都市|\b(city|urban|architecture)\b/i.test(text)) return 'urban'
  if (/自然|山|湖|海|徒步|风景|生活|\b(nature|landscape|outdoor|travel)\b/i.test(text))
    return 'nature'
  return fallback
}

export function selectArtwork(
  topic: ArtworkTopic,
  previous?: string,
  random = Math.random()
): Artwork {
  const pool = catalog.filter((asset) => asset.topic === topic && asset.id !== previous)
  return pool[Math.floor(Math.min(0.999999, Math.max(0, random)) * pool.length)]
}

function previousArtwork(key: string): string | undefined {
  try {
    const stored: unknown = JSON.parse(sessionStorage.getItem(storageKey) || '{}')
    if (stored && typeof stored === 'object' && key in stored) {
      const value = (stored as Record<string, unknown>)[key]
      if (typeof value === 'string') return value
    }
  } catch {
    // The in-memory history also supports storage-restricted webviews.
  }
  return remembered.get(key)
}

export function useThemedArtwork(topic: ArtworkTopic, slot: string): Artwork {
  const [seed] = useState(() => Math.random())
  const key = `${topic}:${slot}`
  const image = useMemo(() => selectArtwork(topic, previousArtwork(key), seed), [topic, key, seed])
  useEffect(() => {
    remembered.delete(key)
    remembered.set(key, image.id)
    if (remembered.size > 256) remembered.delete(remembered.keys().next().value!)
    try {
      const stored: unknown = JSON.parse(sessionStorage.getItem(storageKey) || '{}')
      const history = new Map<string, string>(
        stored && typeof stored === 'object' && !Array.isArray(stored)
          ? Object.entries(stored).filter(
              (entry): entry is [string, string] => typeof entry[1] === 'string'
            )
          : []
      )
      for (const entry of remembered) {
        history.delete(entry[0])
        history.set(...entry)
      }
      while (history.size > 256) history.delete(history.keys().next().value!)
      sessionStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(history)))
    } catch {
      // Selection remains available without browser storage or network requests.
    }
  }, [key, image.id])
  return image
}
