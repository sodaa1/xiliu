# 游客演示版与共用功能指引 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付可静态托管的游客演示版，以及 Web、桌面共用、逐项介绍功能的 Wiki 和首次使用引导。

**Architecture:** 复用现有 React 页面，应用数据请求在构建时选择真实 API 或浏览器演示处理器。Wiki 直接编译仓库 Markdown，功能索引和简短介绍由同一内容生成。引导监听实际操作成功结果，独立保存进度。

**Tech Stack:** React 19、TypeScript、Vite、React Router、TanStack Query、react-markdown、现有 CSS token；浏览器 IndexedDB 保存演示 JSON 快照，不增加运行时依赖。

**Spec:** `docs/superpowers/specs/2026-10-16-web-demo-guide-design.md`

## Global Constraints

- “同步两端”在本次任务中指两端共享功能说明与引导代码、随版本共同更新。用户的个人资料继续使用现有存储方式，不增加跨设备账号或云端数据同步。
- 演示操作不访问或改写真实后端资料；未支持的演示请求返回明确限制，不回退真实 API。
- 正常 `build` 保持真实 API 行为。演示构建与正常构建输出不同目录，避免桌面打包误用演示产物。
- 每个功能小节先用两三句话说明用途、入口和基本操作，再补充限制或详细步骤。
- 不包含真实密钥、运行数据库或私人资料；不自动调用模型，不执行本机工具。
- 不清除正常模式存储，不调用真实 API，也不触发 Tauri 原生写入。
- 不复制业务页面；不改动现有 Rust 桌宠实现。复用已有组件和样式。
- 当前用户确认的 Git 身份：`sodaa1 <soda933693@163.com>`，作者、提交者均使用该身份，不添加 AI 署名。
- 保留现有桌宠、版本号及其他任务的未提交改动。对于已有修改的 `web/package.json`，先记录 diff，只提交本任务新增脚本对应的补丁，不整文件包含其他任务改动。
- 用户已要求在 `codex/web-demo-deployment` 分支工作，继续在该分支执行；本计划不另建工作树。

## Review Focus

1. 正常模式与演示模式同源时，演示不能读写真实偏好或调用 API（Task 2、4）。
2. 聊天途中删除会话或重置后，延迟输出不能污染新状态（Task 3、4）。
3. 破损存档、存储拒绝、配额不足和两个标签页同时操作不能静默丢失修改（Task 2、6）。
4. Wiki 不能遗漏细分功能，也不能把桌面或模型能力描述成静态演示已支持（Task 1、6）。
5. 跳转页面、失败操作和被取消的聊天不能使引导误判完成（Task 5）。

## 文件职责

| 路径 | 职责 |
| --- | --- |
| `docs/wiki/*.md` | 12 类用户指南的唯一正文来源，每项功能含简短介绍 |
| `web/src/features/help/catalog.ts` | 文章目录、平台/路由元数据、从正文提取功能简介和检索 |
| `web/src/features/help/GuidePage.tsx`、`guide.css` | 指南目录、搜索、文章阅读、功能跳转 |
| `web/src/lib/app-fetch.ts`、`runtime-mode.ts` | 显式模式判断和应用请求入口 |
| `web/src/features/demo/types.ts`、`seed.ts`、`store.ts` | 演示快照类型、示例内容、事务与内存降级 |
| `web/src/features/demo/handler.ts`、`workspace.ts`、`chat.ts` | 演示请求分发、业务操作和可取消的模板输出 |
| `web/src/features/demo/DemoBar.tsx`、`demo.css` | 演示标识、限制、保存状态和重置入口 |
| `web/src/features/onboarding/progress.ts`、`Onboarding.tsx` | 引导进度、欢迎与三步面板 |
| `web/vite.demo.config.ts`、`web/src/env.d.ts` | 独立演示构建/预览配置与 Vite 类型 |
| `web/public/_redirects`、`docs/WEB_DEMO_DEPLOYMENT.md` | 静态路由回退和部署/预览说明 |

## Task 1：可搜索的共用 Wiki 与完整功能简介

**Files:** 创建 `docs/wiki/{getting-started,feature-map,feed,inbox,knowledge,assistant,plans,models,automations-extensions,appearance-companion,data-backup,faq}.md`；创建 `web/src/features/help/{catalog.ts,catalog.test.ts,GuidePage.tsx,GuidePage.test.tsx,guide.css}`；修改 `web/src/app/App.tsx`，创建 `web/src/env.d.ts`。

**Interfaces:** `GuideArticle = {slug:string;title:string;summary:string;markdown:string;features:GuideFeature[]}`；`GuideFeature = {id:string;title:string;summary:string;articleSlug:string;anchor:string;route:string;platform:'all'|'desktop';demo:'interactive'|'simulated'|'unavailable'}`。导出 `guideArticles`、`guideFeatures`、`searchGuide(query:string):{feature:GuideFeature;snippet:string}[]` 和 `GuidePage():ReactElement`。正文用 `?raw` 导入；自定义 h2 渲染和索引使用同一锚点函数。

- [ ] Step 1：写 `catalog.test.ts`，断言文章与功能 ID 唯一、简介非空、每个条目有对应 Markdown 小节、功能入口在应用路由白名单内；空检索返回目录，关键词“批量归类”“停止回复”“Live2D”“/compress”“备份”命中正确文章。
- [ ] Step 2：运行 `npm --prefix web test -- --run src/features/help/catalog.test.ts`，确认因未实现目录而失败。
- [ ] Step 3：实现内容索引与 12 篇正文。每个 h2 功能小节的首段为 2–3 句简介，元数据只存路由、平台与演示能力标记，简介直接从正文读取，避免维护两份内容。
- [ ] Step 4：按以下功能覆盖清单逐项补齐小节；保留原有功能边界，不把内部 Action 或底层图节点当作额外用户功能。

| 分类 | 必须简单介绍的功能 |
| --- | --- |
| 首次使用/Today | 三步流程、主页快速提问、快速收集、个人设置入口、演示保存和重置 |
| Feed | AI Hot、GitHub Top 5、我的资讯、来源状态、手动刷新、搜索/筛选、添加/编辑、隐藏/恢复、收藏、详情与摘要、Ask AI |
| Inbox | 收集文字、保存链接、正常模式文件导入及格式限制、处理状态/重试、详情与原件、编辑标题/正文/摘要/标签、搜索/标签筛选、选择与批量归类、手动归档、移回 Inbox、删除 |
| Knowledge | 全部资料、未分类资料、文件夹概况、创建/编辑/删除文件夹规则、标签与优先级、文件夹内资料、关键词检索与引用、资料详情、Ask AI |
| Assistant | 新建/切换/删除会话、各会话运行状态、模型切换、输入与发送、资料引用与本轮参考、Markdown、思考过程、停止回复、操作回执/确认、`/clear`、`/compress`、`/skill`、`/mcp`、布局调整 |
| 个人计划 | 日/周/目标、层级关联、创建/编辑/完成/删除、日期安排 |
| 模型设置 | 提供商、API 地址、模型名称、Key、多连接、默认连接、连接启停、专用 embedding 与本地检索条件 |
| 自动任务与扩展 | 创建、时区与时间、启停、删除、运行记录、执行前提、Skill/MCP 安装配置条件、工具权限与操作确认 |
| 个人/外观 | 昵称/邮箱/简介/头像、主题、字体/字号/密度、减少动态、恢复默认、内置/留白/自定义背景、删除背景 |
| 桌宠 | 启用/隐藏/显示、拖动、置顶、两种形态和分别缩放、快捷聊天、Inbox 收录、Live2D 导入与 Core 条件、图片表情与真实形变的区别 |
| 数据/帮助 | 资料存储位置、浏览器偏好与服务端资料的区别、桌面目录、备份/升级、演示限制、指南搜索/深链接/重新引导、常见失败恢复 |

- [ ] Step 5：写 `GuidePage.test.tsx`：搜索命中/无结果、文章直达、无效 slug 返回目录、功能跳转、桌面专属标识、原始 HTML 不执行、外链只允许安全协议；先运行确认失败。
- [ ] Step 6：实现指南视图，增加 `/guide`、`/guide/:slug` 和侧栏“使用指南”。复用 `react-markdown`，目录与正文在窄屏上下排列，支持深色、键盘和减少动态效果。
- [ ] Step 7：运行 Task 1 两个测试文件及 `src/app/App.test.tsx`；通过后仅提交 Task 1 文件，提交信息 `feat: add shared searchable feature guide`。

## Task 2：演示隔离、事务存储与统一请求入口

**Files:** 创建 `web/src/lib/{runtime-mode.ts,app-fetch.ts,app-fetch.test.ts}` 和 `web/src/features/demo/{types.ts,seed.ts,store.ts,store.test.ts,handler.ts}`；修改 `web/src/lib/{api.ts,workspace-api.ts,preferences.ts}`、`web/src/features/today/background.ts`。

**Interfaces:** `isDemo:boolean` 仅由构建模式决定；`appFetch(input:string,init?:RequestInit):Promise<Response>`。`DemoState` 包含 `schemaVersion:1`、`revision:number`、`generation:string`、现有类型对应的 feed/content/folders/tasks/conversations/messages、preferences 快照。`readDemoState():Promise<DemoState>`、`mutateDemo<T>(change:(draft:DemoState)=>T):Promise<T>`、`resetDemoState():Promise<void>`、`subscribeDemo(listener:()=>void):()=>void`、`getDemoStorageStatus():'persistent'|'memory'`。`handleDemoRequest(input:string,init?:RequestInit):Promise<Response>`。

- [ ] Step 1：写请求隔离测试，普通模式把请求原样交给 stub fetch；演示模式访问已知和未知 API 均不调用原生 fetch；未知路由返回包含 `demo_unavailable` 的 400 响应。运行对应测试确认失败。
- [ ] Step 2：实现构建模式和请求入口。演示处理器通过动态导入隔离，不替换全局 fetch；为现有 API 访问替换调用点，保持外部函数签名与错误处理不变。
- [ ] Step 3：写存储测试：示例关系完整、schema 不支持时恢复并提示、数据返回副本、正常存储 key 未读取/未删除、首次持久化不可用时当前页仍可用、使用中超量写入被拒绝且旧状态保留。用可注入的 `DemoPersistence.transact<T>(change:(state:DemoState)=>T):Promise<T>` 边界测试存储失败，不增加 mock IndexedDB 依赖。
- [ ] Step 4：实现 IndexedDB 数据库 `xiliu-demo-v1`、单记录 JSON 快照的 readwrite 事务，变更在同一事务内读/校验/写，正文总量上限 2 MiB；事务内不 await 非数据库操作。首次存储不可用时降级内存并显示状态；使用中写入失败时保留最后成功版本并报告，不静默声称持久保存。
- [ ] Step 5：跨标签页用 BroadcastChannel 通知重新读取 revision；不支持时在 focus 时重读。演示偏好使用独立 `xiliu-demo-*` 命名空间，正常模式原 key 保留；阻止演示原生桥接调用。
- [ ] Step 6：运行新测试以及现有 `src/lib/api.test.ts`、`src/lib/preferences.test.tsx`、`src/features/today/background.test.ts`；通过后提交 `feat: isolate browser demo requests and storage`。

## Task 3：可操作的演示业务与模板聊天

**Files:** 创建 `web/src/features/demo/{workspace.ts,workspace.test.ts,chat.ts,chat.test.ts}`；完善 `seed.ts`、`handler.ts`；按需只对演示入口做小范围能力提示。

**Interfaces:** `handleWorkspaceRequest(url:URL,method:string,body:unknown):Promise<Response|undefined>`；`startDemoChat(cid:string,body:{text:string;context?:string},signal?:AbortSignal):Promise<Response>`；`stopDemoChat(cid:string):boolean`；`cancelAllDemoChats():void`。返回类型与现有 API 一致，聊天响应为 `application/x-ndjson` 的现有 WebEvent 序列。

- [ ] Step 1：写业务测试，串联收藏资讯→更新标签→归档→文件夹列表→关键词检索，断言每次读取看到实际变更；覆盖重复收藏不制造多份资料、无效 ID、删除非空文件夹后资料保留、任务层级与完成、批量归类。运行确认缺少实现而失败。
- [ ] Step 2：按现有 `workspaceApi` 路径实现 Feed/资料/文件夹/计划 CRUD、筛选、归类、Today 聚合；引用当前快照。重试和刷新返回明确示例状态，不抓取远程内容。正文里保存的外链只作为链接，不用于本地 HTTP 请求。
- [ ] Step 3：写聊天测试：会话 CRUD、引用资料被模板使用、每条回复包含“演示回复”、未知问题给示例问题、正常 final 可持久化、停止/abort/重置/删除会话后旧流不写入、并行会话互不停止；运行确认失败。
- [ ] Step 4：实现模板和可取消 NDJSON 输出。每次 stream 写入前核对 generation/cid；取消清理计时器和活跃流。`/clear` 真实清除演示会话；其他不支持命令返回限制，不虚构执行。
- [ ] Step 5：读取模型/命令/能力/数据设置/默认背景的接口返回可用演示状态，模型连接标识为演示。偏好保存校验 `expected_revision`，旧修订返回 409，不能覆盖新偏好；加入对应接口测试。模型写入、后台自动任务执行、上传、MCP/Skill 和原件下载返回明确限制；演示不返回任何真实设置。
- [ ] Step 6：运行 Task 3 测试和现有 Assistant/Feed/Content/Knowledge/Plans 测试；通过后提交 `feat: support interactive browser demo workflows`。

## Task 4：演示构建、状态栏与限制提示

**Files:** 创建 `web/vite.demo.config.ts`、`web/src/features/demo/{DemoBar.tsx,DemoBar.test.tsx,demo.css}`、`web/public/_redirects`；修改 `.gitignore`、`web/package.json`、`web/src/app/App.tsx`、`web/src/features/content/{CaptureDialog.tsx,ContentPage.tsx}`、`web/src/features/settings/{SettingsPage.tsx,AppearanceSettings.tsx}`。不编辑当前正在改动的桌宠组件。

**Interfaces:** `DemoBar():ReactElement`；`resetDemo():Promise<void>` UI 操作按顺序取消流、重置存储、清理演示 QueryClient 和引导进度、重载到 `/today`。`build:demo = tsc -b && vite build --config vite.demo.config.ts --mode demo`，输出 `web/dist-demo/`；`preview:demo = vite preview --config vite.demo.config.ts --mode demo --host 127.0.0.1 --port 5184`。

- [ ] Step 1：写 DemoBar 测试：模式标识/内存提示可见、取消重置保留状态、确认重置恢复示例且清理查询和活跃流，普通模式不显示状态栏。运行确认失败。
- [ ] Step 2：实现状态栏和确认式重置。正常模式配置与数据说明保持现有行为；演示模式模型配置、文件上传、Live2D 导入、自动任务编辑区域换成带指南链接的解释；主题和个人资料仍可修改。
- [ ] Step 3：修正原件链接：演示中显示已保存正文或引导到限制说明，不生成需要服务器的链接；检查所有直接媒体请求，演示仅用内置静态资源。
- [ ] Step 4：演示配置继承生产的插件与依赖解析，但移除开发 API proxy 和 `/intro` 服务中间件，指定独立 outDir；不运行写入 `web/dist/intro/` 的介绍站打包脚本。正常 `npm run build` 保留原脚本。在 `.gitignore` 加入 `web/dist-demo/`，防止提交生成产物。
- [ ] Step 5：添加 SPA 回退 `/* /index.html 200`，在部署文档解释适用平台与其他服务器需要的等效配置。对 `web/package.json` 的已有变更仅叠加两个脚本，保留版本与其他任务修改。
- [ ] Step 6：运行 DemoBar 测试、`npm --prefix web run lint`、两种构建。核对目录独立、演示不请求 API、普通产物无演示状态栏；提交 `feat: package static demo with clear capability limits`，混合修改文件仅暂存任务补丁。

## Task 5：欢迎、操作驱动的三步引导与页面帮助

**Files:** 创建 `web/src/features/onboarding/{progress.ts,progress.test.ts,Onboarding.tsx,Onboarding.test.tsx,onboarding.css}`；修改 `web/src/app/App.tsx`、`web/src/lib/workspace-api.ts`、`web/src/features/assistant/AssistantPage.tsx`、`web/src/features/content/{useAskAI.ts,ContentPage.tsx}`，并在主布局添加按路由选择的功能简介/指南链接。

**Interfaces:** `GuideProgress = {version:1;status:'new'|'active'|'dismissed'|'completed';step:0|1|2|3;itemId?:string;referenceTitle?:string}`；`getGuideProgress():GuideProgress`、`startGuide():void`、`dismissGuide():void`、`resetGuide():void`、`recordGuideAction(action:GuideAction):void`、`subscribeGuide(listener:()=>void):()=>void`。`GuideAction = {type:'saved';item:ContentItem}|{type:'archived';items:ContentItem[]}|{type:'asked';documentId?:string;referenceTitle:string;outcome:ChatOutcome}`；`AssistantReference` 新增 `documentId?:string`，保留已有字段。

- [ ] Step 1：写进度测试：首次 welcome、跳过后不自动弹出、重新打开、刷新续接、普通/演示存储隔离；路由变化不推进，失败操作不推进，不同资料归档不推进，匹配引用且成功回复才完成。先运行确认失败。
- [ ] Step 2：实现独立版本化进度存储，模式命名空间分别为 `xiliu-guide-v1` 与 `xiliu-demo-guide-v1`。保存失败提示当前页进度有效，不阻止实际业务操作；不向后端写示例数据。
- [ ] Step 3：在 `workspaceApi.saveFeed` 成功后记录 `saved`；`updateContent` 返回 Knowledge 状态或 `classifyBatch` 成功后记录 `archived`。保留 API 外部签名，不在网络失败时发事件。
- [ ] Step 4：`useAskAI` 引用增加可选 `documentId`，资料页传入 ID；引导记录选中资料及标题。Assistant 在 `sendTurn` 返回成功 outcome 且本轮引用的 documentId 匹配时记录 `asked`；旧调用没有 documentId 时仍可正常聊天，但不自动完成本次教程。单纯打开助手、清除引用、失败/停止均不完成。若标题变动，以 documentId 关联当前资料；缺失资料则提供重新选取动作。
- [ ] Step 5：写并实现面板测试：首次三选项、跳转到实际来源资料、返回/关闭/继续、模型未配置提示、已删除资料恢复路径、帮助中“重新开始引导”。使用真实按钮事件和 API 成功结果推进，不使用坐标遮罩。
- [ ] Step 6：在主布局按当前路由显示一行功能简介与 Wiki 链接；Wiki 文章内提供重新引导入口。对桌面独立窗口路由不显示 onboarding，首次欢迎等待进入主工作区。
- [ ] Step 7：运行新增引导测试和受影响的 App、Assistant、Content 测试；通过后提交 `feat: guide first use through real app actions`。

## Task 6：集成验证、静态托管复核与交付说明

**Files:** 更新 `docs/WEB_DEMO_DEPLOYMENT.md`；创建 `docs/audit/web-demo-guide-2026-10-16.md`；必要时新增 `scripts/qa/web-demo-guide.cjs` 复用已有浏览器 QA 运行时。只因发现新问题补充功能或测试，不做无关重构。

- [ ] Step 1：运行 `npm --prefix web test -- --run`、`npm --prefix web run lint`、`npm --prefix web run build`、`npm --prefix web run build:demo`；记录真实结果。测试日志不提交，验收说明记录命令和数量。
- [ ] Step 2：独立启动 `preview:demo`，浏览器访问 `http://127.0.0.1:5184`；确保该预览没有 `/api` 代理，即使本机另有正常 Python 服务，演示也不能依赖它。
- [ ] Step 3：浏览器完成 Feed 收藏→Inbox 标签/归档→Knowledge 检索→引用问答→计划完成；刷新与重开验证持久化，确认式重置恢复示例。抓取网络请求与控制台，要求没有 `/api` 网络访问和未处理错误。
- [ ] Step 4：两个同源标签页同时保存不同内容，IndexedDB 事务保留两次变更；清理、存储拒绝与容量上限按设计提示。验证取消聊天、删除会话、重置不出现迟到回复。
- [ ] Step 5：正常本地 Web 打开完整指南、搜索、深链接和重开引导；模拟 Tauri 只用于检查桥接调用边界，不把模拟结果写成原生验收。具备可用安装包时做实际桌面帮助离线阅读和首次引导检查，否则记录验证限制。
- [ ] Step 6：检查 1440px 与 390px、深色、键盘、减少动态；逐项对照 Task 1 功能清单，确认每项都有简介，限制与当前源码一致。
- [ ] Step 7：补充构建/预览/发布步骤、根域名假设与 SPA fallback，明确 `web/dist-demo/` 是待发布产物。全量检查不再扩大到无关后端测试，除非确实改动了后端。
- [ ] Step 8：检查最终 diff 和身份，仅提交本任务变更。用户未请求推送、PR 或外部发布时不进行这些操作。最终报告说明构建、测试、可预览地址、平台验证边界与已有修改保留情况。

## 计划自检

- 演示构建/隔离/能力限制：Task 2–4；多标签页和静态网络检查：Task 6。
- Wiki 的 12 类正文、每个细分功能简介、检索与平台标识：Task 1；覆盖复核：Task 6。
- 首次欢迎、真实结果推进、重新进入、普通与演示隔离：Task 5。
- 视觉沿用已有应用，无新素材或框架依赖；桌面 Wiki 使用相同构建正文，无远程内容依赖。
- Task 5 的 GuideAction、AssistantReference 和资料详情使用相同 documentId 关联，旧调用没有 ID 时不误判教程完成。
- 需要用户评审本计划并选择执行方式后，才开始产品代码实现。
