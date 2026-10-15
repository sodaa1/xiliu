import { useEffect, useState } from 'react'
import {
  blankBackground,
  builtinBackground,
  readBackgrounds,
  watchBackground,
  type HomeBackground,
} from './background'
export function useHomeBackground() {
  const [library, setLibrary] = useState<{
    settings: HomeBackground
    images: { id: string; name: string; url: string }[]
  }>({ settings: blankBackground, images: [] })
  const [error, setError] = useState('')
  useEffect(() => {
    let stopped = false,
      generation = 0
    const refresh = async () => {
      const ticket = ++generation
      try {
        const value = await readBackgrounds()
        if (stopped || ticket !== generation) return
        setLibrary(value)
        setError('')
      } catch (failure) {
        if (!stopped) setError((failure as Error).message)
      }
    }
    void refresh()
    const stop = watchBackground(() => void refresh())
    return () => {
      stopped = true
      stop()
    }
  }, [])
  const { settings, images } = library
  const url =
    settings.mode === 'builtin'
      ? builtinBackground
      : settings.mode === 'custom'
        ? images.find((image) => image.id === settings.selected)?.url
        : undefined
  return { ...library, url, error }
}
