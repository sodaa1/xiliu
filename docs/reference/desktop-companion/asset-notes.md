# 息流角色源素材

日期：2026-10-15。

本目录保留用户已认可的角色设定，以及从该设定分别整理的正常比例与 Q 版透明源素材。角色分工：正常比例融入 Today 首页欢迎区域，Q 版用于 Windows 常驻桌宠。

## 文件与状态

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| `character-board.png` | 已认可的双比例角色设定及待机、思考、完成状态参考 | 设计参考图，非运行资源 |
| `standing-source.png` | 正常比例全身立绘，1024×1536 | 带透明通道的扁平源素材 |
| `chibi-source.png` | Q 版全身角色，1254×1254 | 带透明通道的扁平源素材 |

生成方式：内置 `image_gen` 工具。两份独立素材均以 `character-board.png` 对应的原始图为编辑参考，`transparent_background` 为 `true`。保留原生成文件，本目录另存项目副本。没有调用 API/CLI 回退。

透明通道检查：两份 PNG 均为带 alpha 的 32 位图，角点 alpha 为 0，主体采样存在接近不透明的像素。仍需在实际界面的深浅背景和缩放尺寸中进行视觉验收。

这些文件没有独立的眼睛、嘴、头发和躯干图层，不是 PSD，也不是 `.moc3` 模型。进入 Live2D 制作时需要补全遮挡区域并拆层、建模，不能将此目录视为已交付动画模型。

## 正常比例素材最终提示词

```text
Use case: background-extraction. Asset type: transparent PNG full-body anime standing portrait for xiliu's Today welcome section.
Edit target: the supplied approved character design board. Extract and faithfully recreate ONLY the full-proportion adult anime character standing on the LEFT of that board, on a genuinely transparent alpha background.
Preserve the existing exact identity, face, silver-lavender short bob hair, curved forelock, violet star hair clip, purple eyes, gentle expression, ivory cape jacket with violet lining and star decorations, dark navy dress, belt, opaque charcoal tights and dark ankle boots. Preserve her existing natural standing pose, hands, front three-quarter angle and full adult body proportions. This is the same approved character, not a redesign. Keep the delicate dark contour and controlled original 2D anime cel shading.
Composition: ONE complete full-body character centered in a portrait canvas, largest possible size with a small even safety margin, all hair, cape, fingers and boots fully inside the canvas. No other figures, no chibi figure, no board.
Remove all original presentation background, stars outside her body, star trails, orbit lines, text, header, captions, borders, ground, contact shadow and all other board content. Keep decorative stars that are printed on her clothing or attached to her hair. Edges must be clean, without pale fringe, matte halo, sticker border, gray rectangle or checkerboard baked into pixels. Preserve true alpha around the figure and between separated body/clothing parts.
No new props, no text, no watermark. This is a clean reusable standing portrait source asset, not a layered Live2D model.
```

## Q 版素材最终提示词

```text
Use case: background-extraction. Asset type: transparent PNG full-body chibi character source for xiliu's Windows desktop companion.
Edit target: the approved supplied character design board. Extract and faithfully recreate ONLY the LARGE CHIBI CHARACTER in the UPPER RIGHT area of that board, on a genuinely transparent alpha background. One single chibi character, no other figures.
Identity lock: exactly the approved silver-lavender short bob hair, curved forelock, violet four-ray star hair clip, muted purple anime eyes, small gentle smile, ivory short cape jacket with violet lining, dark navy short tunic dress, opaque dark charcoal leggings and tiny dark ankle boots. The character is the same young-adult anime star-spirit character stylized to about 2.5 heads tall. Preserve the same big-eyed face and the reference's open, friendly pose, with tiny hands visible at the sides and relaxed feet. The clothing and hair silhouette must match the reference character precisely.
Style: original clean 2D anime line art and refined controlled cel shading matching the supplied board, crisp modest contour suitable for a 100–180px desktop companion, no pixel art, no 3D, no sticker outline.
Composition: ONE full-body complete character centered in an approximately square canvas, occupying about 85 percent of the canvas height, with a small transparent safety margin around the entire figure; both hands, curved forelock, cape tips and boots fully visible, no cropped parts.
REMOVE all board content: white/gray background, stars floating outside the body, orbit lines, labels, all text, ground ellipse, cast shadow, all other characters and presentation swatches. Keep the star clip and stars printed on the clothing. No glow, halo or diffuse haze surrounding the figure. Do not add a platform, backdrop, gradients, checkerboard pixels or drop shadow. True alpha transparency outside the character, clean cutout edges with no fringe. No text, no props, no watermark. This is a clean reusable source image for later layer preparation, not a completed Live2D model.
```
