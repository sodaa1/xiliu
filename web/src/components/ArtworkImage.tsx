import type { ImgHTMLAttributes } from 'react'
import { publicAsset } from '../lib/deployment'
import { useThemedArtwork, type ArtworkTopic } from '../lib/artwork'

type Props = Omit<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'srcSet' | 'alt'> & {
  topic: ArtworkTopic
  slot: string
  remote?: string
}

/** Decorative photography only: article originals take priority over stock artwork. */
export function ArtworkImage({ topic, slot, remote, sizes = '320px', ...props }: Props) {
  const artwork = useThemedArtwork(topic, slot)
  const fallback = publicAsset(artwork.variants.find((variant) => variant.width === 960)!.path)
  const srcSet = artwork.variants
    .map((variant) => `${publicAsset(variant.path)} ${variant.width}w`)
    .join(', ')
  return (
    <img
      {...props}
      key={`${artwork.id}:${remote || ''}`}
      data-artwork={artwork.id}
      data-artwork-topic={topic}
      src={remote || fallback}
      srcSet={remote ? undefined : srcSet}
      sizes={remote ? undefined : sizes}
      alt=""
      decoding="async"
      onError={(event) => {
        const image = event.currentTarget
        if (remote && !image.dataset.localFallback) {
          image.dataset.localFallback = 'true'
          image.srcset = srcSet
          image.sizes = sizes
          image.src = fallback
        } else {
          image.hidden = true
        }
      }}
    />
  )
}
