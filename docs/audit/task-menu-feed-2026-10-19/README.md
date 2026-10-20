# 任务菜单、资讯页与字体调整 · 2026-10-19

本轮已完成个人任务菜单、Feed 资讯主页面/阅读弹窗/编辑弹窗/来源状态面板，以及共享字号与默认字体调整。首页仍可切换原版和山水工作台，左侧保持原有图标顺序。其余模块没有在本轮宣称完成重设计。

## 实际效果

- [截图画廊](index.html)：逐页前后对比、参考图对照、任务菜单、手机/平板、深色大字号、阅读与编辑弹窗。
- [资讯参考对照](feed-reference-comparison.png)、[资讯前后对比](compare-feed.png)、[任务菜单前后对比](task-menu-comparison.png)。
- [真实浏览器验收记录](browser-checks.json)：Windows Edge / Playwright，1440×900、390×844、768×1024。
- [触屏与实际字体检查](touch-font-checks.json)：触屏菜单默认可见，浮层保持在 390px 视口内；浏览器实际使用 Microsoft YaHei UI 字体绘制资讯标题。

## 参考与实施锁定

每组改造先阅读用户参考，再查看实际浏览器截图。资讯采用 ZIP 内 `feed/01-feed-main.jpg` 的焦点大图、精选侧栏、下方缩略图阅读列表与淡紫色筛选；同时阅读 `02-article-detail.jpg`、`03-source-management.jpg`、`04-saved-later.jpg`。任务操作依据用户第二张截图的三点浮层和顶部颜色选择，保留本产品浅色主题。

保留原版侧栏和业务能力，因此没有复制参考中的文字导航、虚构订阅源数量或新增后台订阅管理。顶部导航仍置于右上方现有背景。手机端来源筛选可横向滚动，精选栏隐藏，完整资讯列表仍可操作。

字体参考：

- [Atlassian Applying typography](https://atlassian.design/foundations/typography/applying-typography)：按标题、正文、辅助文字建立角色，并使用相对字号。
- [Material typography](https://m3.material.io/styles/typography/applying-type)：参考类型层级；其页面依赖脚本，本轮没有直接移植字体或组件。
- [W3C 中文排版需求](https://www.w3.org/International/clreq/)：参考中文排版可读性和行距。
- [React Bits](https://www.reactbits.dev/) 与 [Uiverse](https://uiverse.io/)：筛选后采用轻量悬停、选中反馈和切换思路，以现有 React/CSS 实现，没有复制整套效果或新增依赖。

默认字体优先 PingFang / Microsoft YaHei UI / Microsoft YaHei；保留系统、圆润、衬线选项及 14/16/18px 偏好。共享字号角色以 rem 表示：辅助 12、标签 13、正文 14、阅读 15、卡片标题 18、页面标题 26px（默认小字号下），长段行高约 1.8–1.9。页面标题不再混用手写字；品牌字体保留。

## 交互与功能

- 任务行仅显示状态色点，移除行内状态下拉及常驻编辑/删除按钮。悬停、键盘聚焦或触屏时显示三点按钮；顶部灰/橙/绿对应未开始、进行中、已完成，下方编辑/删除。
- 菜单支持方向键、Home/End、Escape、Tab；状态有文本辅助名称，选中有勾选描边。弹窗关闭返回原三点按钮。现有完成复选框保留快捷完成能力。
- 三状态继续调用原有任务更新接口；不修改任务数据结构。
- 资讯主界面支持实际数据形成的焦点轮换、话题筛选、列表/卡片视图和时间排序。完整列表保留焦点资讯，保证始终有编辑/删除等入口。
- 搜索、来源筛选、手动增删改恢复、外部隐藏/取消隐藏、收藏、AI 总结/引用及原文链接继续使用现有接口。
- 来源状态面板展示真实状态，只提供浏览筛选，没有虚构“启用订阅”等未实现功能。
- 动效仅使用轻量 CSS；遵循已有减少动态效果设置与系统偏好。

## 图片来源

`web/public/feed/` 的装饰封面从用户参考图裁切成 WebP：

| 文件 | 原图裁切坐标 (left, top, right, bottom) | 尺寸 |
| --- | --- | --- |
| mountain.webp | (347, 438, 1210, 700) | 863×262 |
| city.webp | (362, 1187, 601, 1362) | 239×175 |
| design.webp | (358, 1435, 601, 1610) | 243×175 |
| technology.webp | (358, 1680, 601, 1854) | 243×174 |

先使用资讯 metadata 内的有效封面 URL，缺失或加载失败时使用装饰封面；装饰图使用空 alt，不冒充新闻原图。这些裁切资产受参考源分辨率限制，不属于本轮生成的高清图片；首页高清背景是前一轮已交付资产。

## 本轮修改文件

| 范围 | 文件 |
| --- | --- |
| 任务行和浮层 | `web/src/features/plans/components/PlanTaskItem.tsx`、`TaskMenu.tsx`、`task-menu.css`、`TaskMenu.test.tsx` |
| 任务集成回归 | `web/src/features/plans/PlansPage.test.tsx`、`web/src/features/content/Workspace.test.tsx` |
| 资讯界面 | `web/src/features/feed/FeedPage.tsx`、`FeedDiscovery.tsx`、`feed-workbench.css` |
| 资讯测试 | `web/src/features/feed/FeedPage.test.tsx`、`FeedRegression.test.tsx`；原有 4 项预览/CRUD 回归保留在后者，新测试保留在前者 |
| 字体与入口 | `web/src/styles/typography.css`、`web/src/styles/preferences.css`、`web/src/lib/preferences.ts`、`web/src/main.tsx` |
| 资产 | `web/public/feed/mountain.webp`、`city.webp`、`design.webp`、`technology.webp` |
| 审计 | `docs/audit/coverage-manifest.json` 中本轮变更的 UI 映射、本目录、`design-qa.md` 追加记录 |

现有用户与前轮未提交修改保持在工作区；本轮没有修改 Agent、RAG、MCP 后端，没有提交 Git。`docs/audit/surface-inventory.json` 原有修改未覆盖。

## 验证结果

| 检查 | 结果 / 日志 |
| --- | --- |
| 全量前端测试 | 54 文件、239 项通过：[frontend-tests.txt](frontend-tests.txt) |
| 最后新增断言回归 | 3 文件、7 项通过：[targeted-final.txt](targeted-final.txt) |
| 全量 Python 测试 | 931 通过、1 跳过，101 条既有警告：[backend-tests.txt](backend-tests.txt) |
| Lint | 通过：[lint.txt](lint.txt) |
| TypeScript | `tsc -b` 通过：[typescript.txt](typescript.txt)（无错误输出） |
| 生产构建及介绍站 | 通过：[build.txt](build.txt)；仍有现有大 chunk 提示 |
| UI surface guard | 20 项通过：[surface-tests.txt](surface-tests.txt) |
| 动作/界面覆盖验证 | 1041 个 surface，0 错误：[surface-verification.txt](surface-verification.txt) |
| 浏览器 | 7 组实际交互检查通过，0 pageerror：[browser-checks.json](browser-checks.json) |

浏览器使用独立 `xiliu-home-workbench-*` 临时数据库；任务状态、资讯 CRUD/恢复和收藏实际请求接口。失败保存测试拦截一次 503 响应验证草稿保留。未调用真实模型；AI 总结既有行为由回归测试验证。截图含验收数据，不是用户真实内容。

实际截图发现并修复了旧 CSS 覆盖布局、焦点卡过高、精选栏未收紧、隐藏行操作被覆盖、手机筛选竖排过长、焦点资讯缺少管理入口和编辑弹窗返回焦点问题。触屏检查还发现将按钮滚入视口后延迟触发的 scroll 事件可能关闭菜单，现仅在锚点实际移动时关闭；补充回归断言并再次通过全量前端测试、Lint 和生产构建。独立只读代码复核确认焦点管理与 CRUD 修复到位。

自动审批曾拒绝以 Git 基线覆盖当前测试文件，理由是未提交修改丢失风险；未执行该操作。改用新增回归文件保留测试覆盖，没有阻塞项。

## 未完成及边界

- Inbox、Knowledge、Settings、Onboarding、Automations、Companion、Launch 的页面主体仍待后续逐组改造；本轮仅共享字体自然生效并提供六页/双首页主题对比。
- 来源订阅管理、统计等参考中没有现有后端支持的功能没有新增。
- 非 Windows 平台的实际字体外观及原生桌面壳未另行实机验证；不声明逐像素一致或数值相似度。
