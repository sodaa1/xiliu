export async function readAvatar(file: File): Promise<string> {
  if (!/^image\/(png|jpeg|webp|gif|avif)$/.test(file.type))
    throw new Error('请选择 PNG、JPG、WebP、GIF 或 AVIF 图片。')
  if (file.size > 5 * 1024 * 1024) throw new Error('头像图片不能超过 5 MB。')
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = url
    await image.decode()
    if (!image.width || !image.height) throw new Error('无法读取图片。')
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 160
    const context = canvas.getContext('2d')
    if (!context) throw new Error('浏览器暂时无法处理图片。')
    const edge = Math.min(image.width, image.height)
    context.drawImage(
      image,
      (image.width - edge) / 2,
      (image.height - edge) / 2,
      edge,
      edge,
      0,
      0,
      160,
      160
    )
    return canvas.toDataURL('image/webp', 0.82)
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : '图片无法读取，请换一张图片。')
  } finally {
    URL.revokeObjectURL(url)
  }
}
