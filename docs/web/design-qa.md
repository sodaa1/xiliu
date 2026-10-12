# 息流介绍长页 · Design QA

## Source truth

- 用户选定的 A 版：`docs/web/assets/xiliu-intro-concept-a.png`，1536×1024。
- 主参考：[Refero / Steep](https://styles.refero.design/style/75fdb89f-ca64-41b3-af36-7a78bd09448e)。
- 滚动参考：[Steep 实站](https://steep.app)，真实 Edge 1440×1000 首屏及两次滚动采集：`.preview/steep-hero.png`、`steep-scroll-1.png`、`steep-scroll-2.png`。确认首屏停留、产品卡片退场、完整工作台接管，以及后续分区排版。
- 实现入口：`http://127.0.0.1:5180/intro/`；构建产物 `web/dist/intro/index.html`。

## Comparison evidence

- 源图和 `.preview/intro-final-hero.png` 同为 1536×1024、deviceScaleFactor 1，在同一轮视觉输入中检查。
- 滚动后首屏：`.preview/intro-desktop-transition.png`，1536×1024。
- 分区：`.preview/intro-final-workflow.png`、`intro-final-feed.png`、`intro-final-ai.png`、`intro-final-local.png`、`intro-final-start.png`，1536×1024。
- 窄屏：`.preview/intro-final-mobile-hero.png`、`intro-final-mobile-ai.png`，390×844。
- 1440×900、1024×768 与 390×844 全页采集保留在 `.preview/intro-full-*.png`；sticky 区域不能用单张全页图表现多个滚动状态，以分区视口图为主。
- Reduced motion：`.preview/intro-reduced.png`，1440×900。

## Five fidelity surfaces

| Surface | Result |
| --- | --- |
| 字体与层级 | 保留中文衬线 display + sans 正文/UI；使用本机 SimSun regular 回退，符合 Steep regular-weight 方向；无远程字体依赖。标题独立断行，手机无单字孤行或截断。 |
| 间距与布局 | 1200px 内容区，白底和浅灰分区，24px 内容卡片，黑色胶囊主/次按钮。首屏围绕中央标题布置四张 UI 片段；长页增加停留与放大过渡、双栏功能区、滚动叙事。 |
| 颜色与 tokens | `#17191c` 墨黑、`#ffffff` 纸白、浅灰卡片；仅本地优先 editorial callout 使用 `#fbe1d1`，其棕字限制在蜜桃表面。无紫色扩散或额外渐变。 |
| 图像与资产 | A 版原图原样保存并用于 README。网页产品视觉是可选择的语义 UI 演示，不用整张截图替代网页；图标和单色 Sparkles 品牌复用项目 Lucide 资产。无图片占位、假用户头像、虚构增长数字。 |
| 产品文案 | 基于本项目 README 与验收文档；示意资料与示例对话有标识。说明模型联网、调度运行条件及桌面安装包状态；不承诺离线 AI 或云同步。 |

## Intentional adaptations

- A 版原稿是一屏概念；用户要求长页和原站滑动效果，因此第一屏扩展为滚动序列，蜜桃重点区移至后部作为完整的本地优先介绍。
- 原稿波形 logo 替换为本项目已有 Sparkles 品牌，保持产品识别；未建立另一套 logo 系统。
- Steep 的英文 serif 转译为中文 Songti/SimSun；正文仍采用系统 sans。首屏轻字重与更大留白符合其原站气质。
- 手机和平板使用正常文档流，减少动态模式禁用 scrub/reveal，全部内容可读；演示仍可用按钮/键盘切换。
- 为保证中文正文可读，灰色正文 token 调深为 `#686d77`，蜜桃表面的辅助棕字为 `#7d4b37`；保持原有色相、留白和标题层级。
- 工作台演示仅呈现产品功能，表单外观不连接模型或写入用户数据。真实功能入口跳到现有应用页面。

## Interaction and runtime checks

- `.preview/intro-browser-report.json`：13 项通过，浏览器运行错误 0；覆盖 sticky 过渡、反向恢复、4 步滚动切换、键盘 tabs、AI 示例、FAQ、安装反馈、四种视口无横向溢出、手机导航及 reduced motion。
- `intro-capture.cjs`：额外检查手机菜单 Escape 关闭与焦点返回；console error / pageerror 均为 0。
- 前端完整 29 项测试通过，包含新增 3 项：tab 键盘/焦点且不请求 API、安装复制成功、复制失败不误报。
- TypeScript / Vite 生产构建通过，原应用与介绍页分开入口，共享依赖。
- 后端目标检查：5 项通过，1 项因 Windows 无符号链接权限跳过；目录 index 的解析仍执行静态根目录边界检查。
- `.preview/intro-production-smoke.py`：实际构建产物的 `/intro`、`/intro/`、`/intro/index.html`、JS/CSS/favicon、原 SPA 和 health 均通过；HTML 禁缓存。
- `.preview/intro-contrast-report.json`：真实浏览器读取 30 处正文、说明、操作和页脚的前景及实际背景；全部达到 4.5:1，最低 4.64:1。FAQ 5.19:1，蜜桃区辅助正文 5.72:1。
- 最终复测：前端 29/29、生产构建、页面范围 ESLint（0 警告）及 Prettier 均通过；调色后的桌面和手机分区截图已重新检查。

## Findings

- 初次检查发现按 opacity+visibility 隐藏 offscreen reveal 会阻止键盘顺序访问。已将正文 reveal 改为 opacity，首屏退场元素仍以 visibility 防止不可见链接获焦。
- 安装说明中未实现的 `⌘ K` 装饰已移除，改为中文检索提示。
- 独立代码复核发现 FAQ 与部分说明灰字对比度不足（P2）；已统一修正正文/说明 token，并以浏览器实际背景测量确认解决。
- 未发现需要阻止交付的 P0/P1/P2 视觉问题。首屏 UI 片段的辅助文字和微标签延续参考中的小字号，仅作产品示意；主要内容不依赖这些微标签。

## 2026-10-08 导航细节预览

- 用户提供当前工作台滚动视图作为质感参考；以其中的 Lucide 细线图标、浅灰表面和柔和边界为约束，保留 A 版黑白与蜜桃重点区的角色。
- 顶部四个导航加入 16px / 1.7 stroke 的同套图标；浅灰胶囊底座，白色悬停表面、细边框与克制阴影，保留文字标签与键盘焦点。
- 手机使用同一语言的浮层菜单，48px 行高；导航折叠断点调整为 900px，保证加入图标后平板仍有足够空间。
- `.preview/intro-nav-report.json`：1536、1024、901、820、701、390 六种宽度无溢出；4 个装饰图标、键盘锚点和手机导航通过，浏览器异常 0。
- 前后对照和悬停截图为 `.preview/intro-nav-{before,after}-*.png`；生产构建、变更范围 ESLint 和 Prettier 通过。

final result: passed

## 2026-10-09：0.3.0 内容与目录迁移

- 当前项目入口和源码克隆地址统一为 `https://github.com/sodaa1/xiliu`；页脚 GitHub 标签使用 `xiliu`。
- 安装区补充 Python 3.12+、uv、Node.js / npm 和完整克隆步骤；Windows、WebView2、模型配置、公开 Release 状态依据当前仓库文档。
- 介绍网页的源码、图标、A 版原图、研究和 QA 脚本、独立构建入口集中在本目录。应用前端只保留 `/intro/` 的 Vite 集成配置。
- 独立 TypeScript / Vite 构建通过；应用构建通过；应用前端 34 项测试通过，其中介绍站 4 项交互检查，独立测试入口也通过。
- Edge 浏览器检查通过：首屏固定与反向滚动、四阶段切换、键盘操作、FAQ、复制反馈、1536 / 1440 / 1024 / 390 宽度、手机导航和减少动态。浏览器异常为 0。
- `scripts/qa/intro-content.cjs` 验证当前仓库、版本、安装要求及公开 / 本地链接；`intro-production-smoke.py` 验证生产 `/intro/` 路由及全部 JS、CSS、favicon 资源。
- 本次报告与截图位于 `.preview/`。线上同步尚未完成：Sites 连接返回 transport send error，未取得有效发布凭据或新部署结果。

## 2026-10-10：线上同步完成

- Sites 连接恢复。以线上最新源码为基础，仅更新 xiliu 子站及其项目链接维护说明，保留作品集首页和线上 xiliumini 子站。
- 个人网站生产构建和 17 项作品集、子站资源及 Worker 检查通过；官方流程完成源码推送和发布包生成。
- 已发布 Sites 版本 6，部署状态 `succeeded`。子站地址：`https://933693.xyz/projects/xiliu/`。
- 发布提交：`f9c3868190e6752b46653ff07ffb1b17f01b724a`；部署编号：`appgdep_6ac9fdbfcafc81919ccca58afed4950e`。
