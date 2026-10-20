# 导航统一、任务状态与 Assistant 改造 · 2026-10-19

本轮已直接修改代码：恢复原版图标左栏，将胶囊导航融入各工作区页面右上角，主题切换改为两个图标；换入重新生成的高清山水背景；补上计划任务行的三态选择；继续按用户参考图重做 Assistant，未保留旧 Assistant 样式分支。

## 截图

| 页面 | 修改前后 | 当前实现 |
| --- | --- | --- |
| 原有首页 | [对照](compare-today.png) | [桌面](after-today.png) |
| 山水首页 | [对照](compare-workbench.png) · [背景细节](panorama-detail-comparison.png) | [桌面](after-workbench.png) · [手机](after-workbench-mobile.png) |
| Assistant | [前后对照](compare-assistant.png) · [参考图对照](assistant-reference-comparison.png) | [欢迎区](assistant-welcome-desktop.png) · [对话与执行记录](assistant-conversation-desktop.png) |
| Feed | [对照](compare-feed.png) | [桌面](after-feed.png) |
| Inbox | [对照](compare-inbox.png) | [桌面](after-inbox.png) |
| Knowledge | [对照](compare-knowledge.png) | [桌面](after-knowledge.png) · [详情导航](knowledge-detail-navigation.png) |
| 个人计划 | [对照](compare-plans.png) | [进行中筛选](plans-in-progress.png) |

补充：[Assistant 手机](assistant-mobile.png)、[平板](assistant-tablet.png)、[暗色大字号](assistant-dark-large.png)、[模型选择器](assistant-model-picker.png)、[设置中的导航](settings-navigation.png)。

桌面截图为实际 Edge 1440×900、DPR 1；手机 390×844，平板 768×1024。原始 Assistant 参考图 2244×1384，按宽度 1440 归一对照。截图使用此前创建的独立临时 API 数据库，未读写用户工作区。三态验收会改变该临时数据库的任务计数，因此前后图中的数值可能不同。

## 本轮行为

- 两种首页和各工作区共用同一份原版 `WorkspaceSidebar`：无文字，顺序为今日、助手、资讯、收件箱、知识库、个人计划，底部保留引导和设置。品牌、尺寸与原路由保持一致。
- `PageToolbar` 放进页面自身的标题或搜索区域，原有首页则直接覆盖在背景右上方；移除独立的 `global-topbar` 行。主题按钮仅显示图标，保留可访问名称、提示和键盘焦点。窄屏胶囊可横向滚动。
- 主题选择仍只切换首页；Assistant 直接使用新样式，其余页面本轮只统一导航位置。知识库详情只显示一套导航。设置弹窗内再次点击设置胶囊，会保留原返回页及查询参数。
- 计划任务行新增「未开始 / 进行中 / 已完成」选择，直接调用既有更新接口，状态与 `completed` 同步。保留勾选完成的快捷操作和既有新建/编辑弹窗。
- Assistant 改为浅灰会话区、对话搜索和真实日期筛选、欢迎说明、四个可操作的提示入口、淡紫色消息、柔和输入框与执行记录样式。保留创建、切换、删除、模型选择、命令补全、调整侧栏/输入区尺寸、停止回复和后台会话运行机制。
- 欢迎入口使用现有提示与 `/mcp` 命令，没有把参考图中未接入的图片生成或文件上传画成不可用按钮。执行记录继续显示既有实际执行步骤，不增加后端推理内容。

## 高清背景

使用内置 imagegen 重新绘制，原生输出 **2039×771**，不是将旧图放大。已转为约 185 KiB WebP，并连接桌面和手机首页：

`web/public/themes/workbench-panorama-hd.webp`

生成说明见 [image-generation.txt](image-generation.txt)。原图保留在生成工具返回的位置，项目使用的是工作区内资源，无新增依赖。

## 验证

| 检查 | 结果 | 记录 |
| --- | --- | --- |
| 全量前端测试 | 52 文件、236 项通过 | [日志](frontend-tests.txt) |
| 全量 Python 测试 | 931 通过、1 跳过 | [日志](python-tests.txt) |
| 界面分类保护 | 20 通过 | [日志](surface-tests.txt) |
| ESLint | 通过 | [日志](lint.txt) |
| TypeScript `tsc -b` | 通过 | [日志](typescript.txt) |
| 生产构建及 Intro 构建 | 成功，保留 Vite 主包体积提示 | [日志](build.txt) |
| 真实浏览器 | 六个页面及两种首页布局核对；13 项交互检查，0 个页面脚本错误 | [布局坐标](after-layout.json) · [交互](browser-checks.json) |

交互覆盖任务三态、进行中筛选与刷新持久化、欢迎入口填入、对话搜索/日期筛选/选择/删除、模型选择器键盘关闭、移动和平板布局、暗色/大字号/减少动态效果、设置返回路径及知识详情单套导航。对话和任务增删改使用真实临时 API；仅对话消息 GET 使用明确标注的录制样例以检查 Markdown 与折叠执行记录，未调用真实模型。

修正过的实际问题：资讯旧网格把导航挤到左侧、手机助手继承旧横排高度导致创建按钮被覆盖、设置胶囊丢失返回位置、知识库详情重复导航、任务行悬停操作遮挡状态选择。均在修改后重新截图和检查。

## 修改文件

新增：

- `web/src/components/WorkspaceChrome.tsx`、`workspace-chrome.css`、`WorkspaceChrome.test.tsx`。
- `web/src/features/assistant/assistant-workbench.css`、`ConversationList.test.tsx`、`MessageList.test.tsx`。
- `web/public/themes/workbench-panorama-hd.webp`。

修改：

- `web/src/app/App.tsx`、`App.test.tsx`：共享左栏、移除独立导航行、设置内导航及返回路径回归。
- `web/src/components/PillNav.tsx`：保留设置背景路由。
- `web/src/features/today/WorkbenchShell.tsx`、`HomeThemeSwitch.tsx`、`TodayPage.tsx`、`WorkbenchHome.tsx`：共用左栏、图标切换、页内导航、高清图。
- `web/src/features/feed/FeedPage.tsx`、`web/src/features/content/ContentPage.tsx`、`web/src/features/knowledge/KnowledgePage.tsx`：页内工具栏及详情去重。
- `web/src/features/plans/PlansPage.tsx`、`PlansPage.test.tsx`、`components/PlanTaskItem.tsx`：直接选择三态与回归测试。
- `web/src/features/assistant/AssistantPage.tsx`、`ConversationList.tsx`、`MessageList.tsx`：新 Assistant、筛选与减少动态效果适配。
- `docs/audit/coverage-manifest.json`、`design-qa.md`：本轮界面分类与验收记录。

其余已有未提交修改保留；未改 Agent、RAG、MCP、模型服务或任务后端。后续 Feed、Inbox、Knowledge、Settings 等页面的主体重绘尚未实施，本轮不是全站重绘完成声明。
