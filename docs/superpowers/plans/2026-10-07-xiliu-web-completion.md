# 息流 Web v0.1 剩余阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. 用户要求持续执行到完成，不再逐阶段停下确认。

**Goal:** 完成 Phase 5–7，使全部 v0.1 导航与数据流可用。
**Architecture:** 保留 React/Vite、FastAPI、Runtime 与现有自动化调度。内容、资讯缓存和 Tasks 共用 app.sqlite3；Markdown 与原附件放在 content/<id>/；自动化复用 automation.sqlite3。
**Tech Stack:** 现有 Python/sqlite3/FTS5、React/TypeScript、TanStack Query。
**Spec:** docs/reference/息流_UI_v0.1_技术方案.md §8–18；此前用户修复要求优先于原文。

## Global Constraints
- 保留未提交的 Assistant 修复、现有密钥与用户数据；不得提交运行数据。
- 复用 Runtime/Gateway/Policy/Hook 调用 AI Hot；前端不访问外部 provider。
- 内容支持 note/link/file，原件保留，不做 OCR、embedding 或全文抓取。
- 浏览器无工程实现概念，保持浅色与蓝紫主色；桌面和 390px 布局可用。
- 按模块少量关键测试，最后完整回归；无需为低影响样式另建测试。

## Review Focus
- 文件名、ID、超限上传不可越过 content 目录；Markdown 可搜索和迁移。
- 中文与 FTS 特殊字符查询稳定，Inbox→Knowledge 不复制附件。
- Feed 外部连接失败保留缓存，分别反馈来源状态；Save 幂等。
- 自动化调用已有调度器，避免两个 owner，停用确实停止后续调度。
- Ask AI 的内容仅作为本轮参考数据，切页请求不中断，原对话不被覆盖。

### Task 1: 内容后端
Files: api/services/content.py、api/routes/content.py、tests/unit/test_content_service.py。
Interfaces: ContentService(store).create(payload), list(status,q,tag), get(id), update(id,changes), delete(id), original(id)；router GET /api/content?status=inbox|knowledge&q=&tag=、POST /api/content、GET/PATCH/DELETE /api/content/{id}、GET /api/content/{id}/original。
Content item: id,type(note|link|file),status(inbox|knowledge),title,content,summary,source,tags:string[],created_at,updated_at,filename:string|null。POST file: filename,data_base64；上限20MiB。使用 UUID、事务和安全文件名，更新 Markdown 和 FTS。
- [x] 最小回归涵盖三种创建、中文搜索、移动不复制、非法附件与缺失项。
- [x] 实现并运行模块测试；报告实际接口及限制。

### Task 2: Feed、Tasks、自动化后端
Files: api/services/feed.py、tasks.py、automations.py、api/routes/workspace.py、tests/unit/test_workspace_services.py。
Interfaces: app.state.feed=FeedService(store,content)、tasks=TaskService(store)、automations=AutomationService(data_dir,model_settings)。GET /api/feed?source=&q= 返回 {items:FeedItem[],sources:SourceStatus[]}；POST /api/feed/refresh；POST /api/feed/{id}/save。FeedItem: id,source(aihot|github),title,summary,url,published_at,tags,metadata。GitHub 使用后端真实公开 Trending 来源/缓存；AI Hot 经现有 Gateway（aihot_get_latest）。
GET/POST /api/tasks、PATCH/DELETE /api/tasks/{id}。Task: id,title,completed,due_at,created_at,updated_at。
GET/POST /api/automations、PATCH /api/automations/{id} body enabled、DELETE /api/automations/{id}、GET /api/automations/{id}/runs。POST: name,prompt,hour,minute,timezone（默认Asia/Shanghai），生成合法id、每日 cron。Service expose start/shutdown/sync methods for app lifespan, existing scheduler only. GET /api/today returns {feed:FeedItem[],tasks:Task[],inbox_count:number}。GET /api/settings/data {data_dir,database,content_count,scheduler_active}。
- [x] 模块关键回归覆盖 Feed 标准化/失败缓存/Save、Task CRUD、Automation Store 启停和 Today 聚合。
- [x] 实现接口，调度设置变更在下一次任务执行生效。

### Task 3: 前端页面
Files: web/src/features/content/*、feed/*、today/*、automations/*、launch/*、lib/workspace-api.ts、features/settings/SettingsPage.tsx、app/App.tsx、features/assistant/AssistantPage.tsx。
Consumes Tasks 1/2 exact HTTP interfaces above. Inbox capture/edit/upload/move/delete/search/tags/download/Ask AI；Knowledge browse/filter/edit/search；Feed source/search/refresh/read/save/ask；Today tasks CRUD/brief/quick ask；Automations secondary drawer create/toggle/runs/delete；Data settings；品牌启动页 SVG/CSS 可跳过。
Ask AI creates conversation then navigate /assistant?c=id with location.state {draft:string,reference:{title:string,content:string}}；Assistant forwards reference string through ChatProvider.send fourth optional context arg. Root implements provider/API/server optional context support.
- [x] 实现页面及少量核心交互回归，不访问真实模型做单元测试。
- [x] 格式、类型与 build；独立模块不改其它任务文件。

### Task 4: 集成与完整验收
Files: api/app.py、schemas.py、services/chat.py、web/lib/api.ts、ChatProvider.tsx、chat-context.ts；docs/ARCHITECTURE.md、PHASES.md、COMPLETION_REVIEW.md。
- [x] 接入服务、路由、lifespan、Ask AI 本轮附加上下文与附件下载边界。
- [x] 独立审查并处理实际问题。
- [x] pytest、Ruff check/format、Pyright、Vitest、lint、format、production build。
- [x] 隔离数据的桌面/窄屏浏览器全功能联调。
- [x] 使用现有DeepSeek配置完成一次真实对话、compress与现有Skill/MCP smoke；只记录脱敏结果，控制调用规模。
- [x] 更新本地预览和交付文档，报告真实外部依赖失败而不伪造数据。

## 执行记录
- 2026-10-07：原 Phase 4 修复已验证49后端/13前端，通过完整检查；当前分支继续，保留全部未提交修改。将独立模块分配给独立实现者，根任务集成。
- 完成：全部实施项已核对；后端72 / 前端16通过，静态检查与构建通过。独立审查的Save、调度关闭/排队sync、日期问题均已修复。真实模型、压缩、命令元信息、Gateway资讯与实际MCP工作流完成；正式预览8765已更新。
