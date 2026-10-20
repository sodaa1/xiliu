# 息流剩余页面 UI 改造验收 · 2026-10-19

本轮已直接修改代码，依次完成 Inbox、Knowledge、Settings 五个分类、Automations、Onboarding、Companion 控件与独立收集窗口、Launch。首页两种主题、原版左侧图标导航与个人计划布局沿用此前成果。未新增依赖，未提交 Git。

[打开截图目录](index.html) · [打开本地验收实例](http://127.0.0.1:5200/inbox)

## 参考与实现

每组开始前读取了用户 ZIP 中对应 JPG：Inbox 的主列表、收集、详情、空态；知识库的主界面、阅读、搜索、标签文件夹；设置的总览、个人资料、模型服务和外观。最终再次并排检查参考与真实 Edge 截图，未使用生成的界面图冒充实现截图。源图按宽度 1440 等比缩放；右侧为 1440×900 CSS 像素、DPR 1 的浏览器截图，不拉伸、不计算虚构还原率。

- Inbox：浅灰背景和白色纵向列表、淡紫分类与按钮；共享三点菜单、独立编辑弹窗、元信息阅读侧栏、两种真实收集模式、空态与保存失败提示。保留筛选、选择、归档、处理重试、原件下载和引用提问。
- Knowledge：彩色文件夹与最近内容分区；全文列表、搜索和完整阅读路由；文件夹创建、编辑与确认删除。数量、时间、摘要来自原有 API。
- Settings：桌面内侧分类栏、手机横向分类条、分组表单；保留个人信息、外观、模型连接、自动化、数据存储，以及背景、阅读、桌宠和 Live2D 子面板。三种外观预览支持键盘，保存时保持焦点。
- Automations：真实任务与启用数量、日程行、创建表单和运行记录。原有时区、开关、删除与接口保持。
- Onboarding：淡紫进度和步骤提示，桌面与手机实际走完 12 步。修复经过山水首页切换布局后丢失返回位置的问题。
- Companion / Launch：沿用已批准的桌宠画作，仅统一工具、菜单、输入与收集表面；启动页使用项目已有高清山水素材和轻量入场效果。减少动态效果时可立即进入。

明确适配：保留用户指定的原版图标导航和右上胶囊；参考中尚不存在于产品的账号安全、云同步、模型推荐等能力未伪造。个人信息仅展示当前可保存字段。知识库装饰封面复用已有 `public/feed` 图片（空 alt），并非文档原始图片；启动页复用已有 `workbench-panorama-hd.webp`。Onboarding、Automations、Companion、Launch 没有单独提供参考图，沿用上述已批准的视觉系统。

## 截图与修正

15 组实际前后对比、5 组用户参考对比；另有阅读、编辑、搜索、确认删除、文件收集、自动化创建与历史、完整引导、紧凑桌宠、浅色/深色/大字号截图。旧图为本轮开始时正在运行的构建，不是 Git HEAD。截图使用独立验收数据库中的真实接口及测试内容，前后数据数量可能因增删改测试而变化。

逐组截图修正了旧 CSS 的复选框绝对定位、标题列方向、弹窗顶栏覆盖、主题卡保存焦点丢失、移动端文件导入框溢出、模型名称逐字换行、收件箱窄屏标题区域和知识库导航换行。最终并排检查字体层级、留白、颜色、圆角和交互状态。与参考存在真实能力和数据差异，不声称逐像素一致。

## 验证结果

| 检查 | 结果 | 原始记录 |
|---|---|---|
| 前端完整 Vitest | 56 文件，243 项通过 | [日志](frontend-tests.txt) |
| Python 完整测试 | 931 通过，1 跳过，101 条警告 | [日志](backend-tests.txt) / [JUnit](backend-results.xml) |
| ESLint | 退出码 0 | [日志](lint.txt) |
| TypeScript `tsc --noEmit` | 退出码 0 | [日志](typescript.txt) |
| 生产构建 `npm run build` | 主应用与 intro 均通过 | [日志](build.txt) |
| UI surface guard | 1073 个 surface，0 错误 | [摘要](surface-verification.txt) / [详情](coverage-results.json) |
| 实际 Edge 浏览器 | 所有以下流程通过，报告中的脚本错误均为 0 | 见下方 |

浏览器报告：[Inbox](inbox-browser.json)、[Knowledge](knowledge-browser.json)、[Settings 与自动化](settings-browser.json)、[背景/Live2D/桌宠/模型表单子面板](settings-subpanels-browser.json)、[启动/桌宠/收集/12步引导](extra-browser.json)、[30组响应式矩阵](responsive-matrix.json)、[最终11页桌面布局](after-layout.json)。响应式覆盖 320px 浅色小字号、390px 深色大字号、768px 浅色中字号；同时检查文档和设置内层水平溢出。

收集、个人信息、文件夹和自动任务使用 `5200` 独立临时数据库真实 API；验证脚本检查数据目录包含 `xiliu-home-workbench-` 才允许写入。空态 GET 和失败保存 POST 仅为两张状态截图做请求拦截，已在矩阵报告单独注明。文件上传使用真实小型文本文件；未触发真实模型调用或等待定时任务执行。

回归测试覆盖菜单键盘与焦点、归档后的查看结果、失败文档重试、主题保存焦点、新手引导跨布局返回位置。后两项记录了修复前失败与修复后通过的日志。只读代码复核发现的独立详情操作遗漏已补齐，复核后未报告新的 P1/P2。完整 surface guard 起初暴露新增 UI 未登记，已仅更新本轮改变文件的映射并重新运行全量测试与检查。

## 修改文件

以下列表按本轮前保存的文件字节比较，避免把前几轮及用户已有改动算成本轮成果；完整机器列表见 [changed-files.json](changed-files.json)。

- `docs/audit/coverage-manifest.json`
- `web/src/app/App.test.tsx`
- `web/src/app/App.tsx`
- `web/src/features/automations/AutomationsDrawer.tsx`
- `web/src/features/content/CaptureDialog.tsx`
- `web/src/features/content/ContentPage.tsx`
- `web/src/features/content/Workspace.test.tsx`
- `web/src/features/knowledge/KnowledgePage.test.tsx`
- `web/src/features/knowledge/KnowledgePage.tsx`
- `web/src/features/launch/LaunchPage.tsx`
- `web/src/features/onboarding/Onboarding.tsx`
- `web/src/features/settings/AppearanceSettings.tsx`
- `web/src/features/settings/PersonalSettings.tsx`
- `web/src/features/settings/SettingsPage.test.tsx`
- `web/src/features/settings/SettingsPage.tsx`
- `web/src/main.tsx`
- `web/src/components/ActionMenu.tsx`
- `web/src/components/ActionMenu.test.tsx`
- `web/src/styles/ui-workbench.css`
- `web/src/features/content/collection-workbench.css`
- `web/src/features/content/ContentDocument.test.tsx`
- `web/src/features/knowledge/library-workbench.css`
- `web/src/features/settings/settings-workbench.css`
- `web/src/features/automations/automations-workbench.css`
- `web/src/features/onboarding/onboarding-workbench.css`
- `web/src/features/launch/launch-workbench.css`
- `web/src/features/companion/companion-workbench.css`

另追加 `design-qa.md`，新增执行计划和本目录验收材料。`docs/audit/coverage-manifest.json` 仅更新本轮发生改变的 UI surface；未重写已有 `surface-inventory.json`。仓库里先前未提交的个人计划、后端和其他页面改动保留。

## 未完成与验证边界

- 本轮所列页面的代码改造与浏览器验证已完成；原生 Windows 窗口宿主、跨屏混合 DPI 拖动、真实 Cubism/Live2D 变形，以及 macOS/Linux 字体表现未实测。
- 模型连接的密钥验证与真实推理、定时任务到点执行不属于本次视觉浏览器验证；已有回归测试通过，未据此声称外部服务可用。
- 独立 `AutomationsDrawer` 当前没有主应用路由入口，完成样式并通过现有组件 CRUD/焦点测试；实际截图与 API 验证使用设置中的自动化面板。
- 构建仍提示应用 chunk 大于 500KB；未为视觉任务扩大范围改动打包策略。后端跳过项和警告详见原始日志。
- 仅启动本地验收实例，没有部署、提交或推送。

## 参考站点与前轮入口

组件反馈、焦点和轻量过渡沿用此前对 [React Bits](https://www.reactbits.dev/) 与 [Uiverse](https://uiverse.io/) 的筛选成果，使用本项目 React/TypeScript/CSS 实现，无新增动画依赖。字体沿用前轮统一层级并尊重用户字号/字体偏好。Refero 本轮检索返回订阅不可用，未把不可见内容作为证据；用户参考图为主要依据。

[首页主题](../home-workbench-2026-10-19/index.html) · [导航与 Assistant](../navigation-assistant-2026-10-19/index.html) · [任务菜单、Feed 与字体](../task-menu-feed-2026-10-19/index.html)
