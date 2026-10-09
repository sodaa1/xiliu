import { useLayoutEffect } from 'react'
import type { RefObject } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function useLandingMotion(
  root: RefObject<HTMLDivElement | null>,
  setStage: (stage: number) => void
) {
  useLayoutEffect(() => {
    if (!root.current) return
    const media = gsap.matchMedia()
    const context = gsap.context(() => {
      media.add('(min-width: 1101px) and (prefers-reduced-motion: no-preference)', () => {
        const timeline = gsap.timeline({
          scrollTrigger: {
            trigger: '.hero-scroll',
            start: 'top 80px',
            end: 'bottom bottom',
            scrub: 0.7,
          },
        })
        timeline.to('.hero-copy', { y: -95, autoAlpha: 0, duration: 0.35 }, 0)
        timeline.to(
          '.float-inbox, .float-today',
          { x: 105, y: -35, opacity: 0, scale: 0.94, duration: 0.35 },
          0
        )
        timeline.to(
          '.float-knowledge, .float-assistant',
          { x: -105, y: -35, opacity: 0, scale: 0.94, duration: 0.35 },
          0
        )
        timeline.fromTo(
          '.hero-overview',
          { y: 300, scale: 0.88, autoAlpha: 0 },
          { y: 0, scale: 1, autoAlpha: 1, duration: 0.65, ease: 'power2.out' },
          0.15
        )
        timeline.to('.hero-scroll-cue', { autoAlpha: 0, duration: 0.2 }, 0)
        gsap.utils.toArray<HTMLElement>('.workflow-step').forEach((step, i) => {
          ScrollTrigger.create({
            trigger: step,
            start: 'top 55%',
            end: 'bottom 55%',
            onEnter: () => setStage(i),
            onEnterBack: () => setStage(i),
          })
        })
      })
      media.add('(prefers-reduced-motion: no-preference)', () => {
        gsap.utils.toArray<HTMLElement>('[data-reveal]').forEach((element) => {
          gsap.from(element, {
            y: 28,
            opacity: 0,
            duration: 0.7,
            ease: 'power2.out',
            scrollTrigger: { trigger: element, start: 'top 92%', once: true },
          })
        })
      })
    }, root)
    return () => {
      media.revert()
      context.revert()
    }
  }, [root, setStage])
}
