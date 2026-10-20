# 高清主题素材与随机轮换 · 2026-10-20

已将首页山水主题、首页资讯配图、Feed 装饰封面、知识库最近内容配图和 Launch 背景改为本地高清素材池。布局、业务接口、路由、个人计划和用户上传背景保持现状。

[查看素材和实际截图](index.html) · [实际应用](http://127.0.0.1:5200/feed)

## 模糊与重复的原因

原 Feed 卡片照片约 239–243×174–175，首页小卡约 289–290×133，焦点图 863×262；来自参考图裁剪，代码按固定索引/ID 取图。在较大的图片框和高 DPI 屏幕上会放大。原始测量：[old-image-dimensions.json](old-image-dimensions.json)。

此次从 [Pexels](https://www.pexels.com/) 筛选 16 张真实摄影作品，分为山水 4 张、阅读 3 张、科技 3 张、设计 3 张、城市 3 张。官方 [Pexels License](https://www.pexels.com/license/) 允许在应用内使用；逐张记录摄影师、来源页和下载地址，未使用在线随机图片端点。图库不是对外售卖或分发的独立图片服务。

卡片母版宽 1920px，山水母版宽 3840px；均由大尺寸摄影素材缩小得到，没有将旧截图放大冒充高清。提供 480/960/1920px WebP，山水另外提供 3840px，共 52 个文件，合计约 15.3MiB（整个离线素材池，不是单页下载量）。`srcset/sizes`、缓存与懒加载让浏览器按显示尺寸选图；不下载整个池到当前页。

## 轮换规则

- 进入有配图的板块时随机选图；再次离开再返回，避开同一位置上一次的图片。刷新后同一会话内保留最近记录，最多 256 个位置。
- 同一页面输入、打开弹窗、查询更新或切换列表布局不会重新抽图。不设置自动轮播定时器，不增加持续动画。
- 根据真实标题/标签分配科技、设计、自然、城市等主题；知识库无匹配时使用阅读池，资讯无匹配时使用科技池。
- 文章自带原图优先；加载失败才使用本地主题配图。不同展示位置独立记录，避免焦点与列表相互覆盖轮换历史。图库图片为空 alt 装饰图，不冒充文章原始摄影。
- 原版首页的纯色/内置角色背景和自定义上传设置保留；随机山水背景应用于山水首页与启动页。桌宠人物、个人头像、计划表单插画属于已确定形象，保留固定身份。没有给纯表单或纯文本页面额外堆放照片。
- 没有新增依赖、API、密钥或后端逻辑；素材使用项目部署基础路径。外网不可用时，本机应用服务器仍能提供素材；不声称网页在本机服务器也关闭后仍能使用。

## 实际验证

| 检查 | 结果 | 证据 |
|---|---|---|
| 全量前端测试 | 57 文件、248 项通过 | [日志](frontend-tests.txt) |
| 随机、稳定性、原图回退与重复位置回归 | 5 项通过 | [日志](rotation-green.txt) |
| ESLint / TypeScript | 通过 | [Lint](lint.txt) / [TypeScript](typescript.txt) |
| 生产构建 | 主应用与 intro 通过 | [日志](build.txt) |
| UI surface guard | 1073 个 surface，0 错误 | [摘要](surface-verification.txt) |
| 真实 Edge | 8 组检查，0 页面脚本错误 | [报告](browser-results.json) |

浏览器使用 1440×900 CSS px / DPR 2，以及 390px 手机、768px 平板。逐页记录第一次/第二次访问的具体素材 ID；实际操作输入、布局按钮与弹窗验证图片稳定。另检查深色大字号和拦截外网 HTTPS 请求后的本地图片加载。DPR 2 实测选中 3840px 山水文件，真实像素尺寸来自素材清单，浏览器 `naturalWidth` 在 srcset 下可能是密度校正后的 CSS 宽度。

首次浏览器复核发现焦点与列表共用同一个换图记录，导致偶尔重复；先补测试重现失败，再分开展示位置并重新跑完整验证。[修复前失败](duplicate-slot-red.txt)、[修复后通过](rotation-green.txt)。

截图使用 `5200` 独立临时验收实例的实际 API，写入前核验数据目录；新增的示例资讯和知识笔记仅用于该实例，不触碰用户数据或触发抓取/模型调用。未重新运行 Python 全量测试，因为本轮只修改前端图片和对应 surface 映射；guard 引用前轮真实业务执行报告，未冒充本轮后端执行。构建仍有此前超过 500KB 的 chunk 提示。

再次打开用户 Feed 参考图检查原有主图/缩略图角色，检查 16 张素材总览和实际首页、Feed、知识库、启动页/移动/深色截图。保留白灰与淡紫框架和原图布局，只更换素材与取图行为。摄影主体和数据内容与参考不同，不声称逐像素复刻。

## 修改文件

- `docs/audit/coverage-manifest.json`
- `web/src/features/feed/FeedDiscovery.tsx`
- `web/src/features/feed/FeedPage.tsx`
- `web/src/features/knowledge/KnowledgePage.tsx`
- `web/src/features/launch/LaunchPage.tsx`
- `web/src/features/today/WorkbenchHome.tsx`
- `web/src/lib/artwork.ts`
- `web/src/lib/artwork.test.tsx`
- `web/src/lib/artwork-catalog.json`
- `web/src/components/ArtworkImage.tsx`
- `web/public/artwork/`

新增本目录验证材料；素材署名另见 `web/public/artwork/CREDITS.md`。旧裁图未删除，避免误删前轮未提交资产，但上述新界面已不再引用旧 Feed / 首页小卡裁图。无提交或部署。

## 素材来源

| 主题 | 文件标识 | 摄影师 | 来源 | 最大本地尺寸 |
|---|---|---|---|---|
| nature | alpine-huts | Dominik Perau | [原始页面](https://www.pexels.com/photo/beautiful-landscape-of-a-mountain-lake-12699620/) | 3840×2560 |
| nature | turquoise-peaks | Luke Miller | [原始页面](https://www.pexels.com/photo/serene-mountain-landscape-with-turquoise-lake-28811891/) | 3840×2560 |
| nature | winter-lake | Boris Ulzibat | [原始页面](https://www.pexels.com/photo/landscape-photography-of-mountain-lake-3055497/) | 3840×2560 |
| nature | quiet-water | Jordi Costa Tomé | [原始页面](https://www.pexels.com/photo/serene-mountain-lake-landscape-in-overcast-weather-31469974/) | 3840×2560 |
| reading | white-library | Polona Mitar Osolnik | [原始页面](https://www.pexels.com/photo/interior-view-of-library-1837726/) | 1920×1272 |
| reading | reading-room | Element5 Digital | [原始页面](https://www.pexels.com/photo/selective-focus-photography-of-bookshelf-with-books-1370296/) | 1920×1282 |
| reading | library-shelves | Zetong Li | [原始页面](https://www.pexels.com/photo/rows-of-bookshelves-in-a-college-library-16689053/) | 1920×1277 |
| technology | laptop-mouse | Markus Spiske | [原始页面](https://www.pexels.com/photo/apple-desk-laptop-technology-96858/) | 1920×1280 |
| technology | digital-workspace | Mateusz Dach | [原始页面](https://www.pexels.com/photo/computer-set-up-on-a-workspace-450035/) | 1920×1280 |
| technology | desktop-display | Skylar Kang | [原始页面](https://www.pexels.com/photo/laptop-and-monitor-on-desk-6045231/) | 1920×1272 |
| design | open-notebook | Kaboompics | [原始页面](https://www.pexels.com/photo/a-notebook-and-pen-on-the-table-8092410/) | 1920×1280 |
| design | minimal-tools | Tima Miroshnichenko | [原始页面](https://www.pexels.com/photo/grayscale-photo-of-a-notebook-5717300/) | 1920×1280 |
| design | creative-notes | cottonbro studio | [原始页面](https://www.pexels.com/photo/notebook-on-a-table-7441089/) | 1920×2880 |
| urban | city-skyline | AG ZN | [原始页面](https://www.pexels.com/photo/skyline-photography-of-a-modern-city-5698184/) | 1920×1080 |
| urban | london-skyline | Pablo | [原始页面](https://www.pexels.com/photo/modern-city-skyline-with-skyscrapers-36552948/) | 1920×1446 |
| urban | baku-architecture | Tahir Xəlfəquliyev | [原始页面](https://www.pexels.com/photo/urban-skyline-view-with-modern-architecture-33686105/) | 1920×1280 |
