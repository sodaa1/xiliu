# 息流 Web Phase 0–4 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, task by task. 用户授权一步步实现，到 Phase 4 完成后检查，期间不再要求审批。

**Goal:** 构建可浏览、可设置模型、可持久化多会话、直接调用 Runtime 的 Assistant，完成四个斜杠命令。
**Architecture:** 在原 src/xiliu 加 FastAPI 薄层，用 sqlite3 WAL 保存 Web 会话；Vite React TS 通过 HTTP/NDJSON 消费服务。Runtime/Gateway 维持原行为。
**Tech Stack:** FastAPI/Uvicorn/sqlite3；React/TypeScript/Vite/Router/Query/Lucide/Markdown/Vitest。
**Spec:** docs/reference/息流_UI_v0.1_技术方案.md

## Global Constraints
- 不将 TUI/CLI 当成 Web 对话后端；不修改 TUI UI。
- Web approval_mode="deny"；不新增危险操作审批通道。
- Web 历史与 TUI session.json 分离；conversation UUID 等于 Runtime session_id。
- .env 是密钥与设置源；GET 永不返回密钥，PUT 空 key 保留已有值。
- 模型 preset 集中维护，兼容用户已经配置的 deepseek-flash，依据官方文档采用当前 canonical ID。
- 用户本次截止 Phase 4；后续导航明确未开放，不伪造内容。
- 先写失败测试，再实现，阶段定向验证。保留上游基线问题，不大修无关部分。

## Review Focus
- chunk 跨行和中文 UTF-8 截断：不丢消息。
- 并发发送/切换/删除：同会话只有一轮，旧响应不污染新会话。
- /clear 后的旧上下文和重复 /compress：保留 UI 历史，已有摘要不丢失。
- 不完整配置/空 key/无效厂商模型：仍可打开设置且错误脱敏。
- provider 切换、失效 override：回退默认，普通 / 文本后端稳定校验。

### Task 0: Baseline and context
- [x] 拉取 main，记录 SHA，读取文档第 1 节接口与参考图。
- [x] 安装原依赖并全量 pytest，记录原始失败，不修改不相关核心。
- [x] 写 docs/ARCHITECTURE.md 与计划。

### Task 1: Model settings and skeleton
**Files:** config.py, pyproject.toml, api/app.py, schemas.py, errors.py, model_catalog.py, services/model_settings.py, routes/models.py。
**Interfaces:** create_app(data_dir=None, env_file=Path('.env')); ModelSettingsService.read()/update(ModelUpdate)/runtime_settings(model=None)；api_key_set 且无 plaintext。
- [x] 先写 test_model_settings.py / test_api_health.py；校验空 key 保留、错误中不泄密、缺配置可启动、厂商模型不匹配拒绝。
- [x] uv run python -m pytest 对上述测试确认缺功能失败。
- [x] 实现 .env 明确加载与 process env 优先级、provider 推断兼容旧配置、原子 set_key 更新。
- [x] 定向测试与 Ruff，提交 Phase 1。

### Task 2: Durable conversations and Runtime chat
**Files:** store.py, services/conversations.py, services/chat.py, routes/conversations.py。
**Interfaces:** AppStore CRUD/append_message/context；ConversationService；ChatService.stream_turn(id,text) -> Iterator[dict]。
- [x] 写 Store CRUD/seq/删除级联/并发测试；fake Runtime 验证 session/context/deny，final 落库，error 不落成功消息；写 API stream 集成测试。
- [x] 执行失败测试。
- [x] 实现 sqlite 短连接、BEGIN IMMEDIATE、FK、同会话 busy gate、NDJSON，错误映射复用 classify_provider_error。
- [x] 定向测试与 Ruff，提交 Phase 2。

### Task 3: Assistant UI
**Files:** web/（见 ARCHITECTURE.md）及轻量预览启动入口。
**Interfaces:** API types 与 GET/PATCH/POST，ReadableStream WebEvent；React Query 按会话 key 缓存。
- [x] 建立 Vite/测试工具，先写四个 Assistant 交互测试及 stream 中文 chunk 测试。
- [x] 执行失败测试。
- [x] 实现三列、导航、模型选择、Markdown、composer、Settings；响应式、空/加载/错误状态。
- [x] npm test -- --run，npm run lint，npm run build，提交 Phase 3。

### Task 4: Commands and shared memory
**Files:** services/commands.py, routes/capabilities.py, graph/memory.py, Composer.tsx。
**Interfaces:** CommandService.resolve(id,text,model) -> CommandResult(task or message/event)；summarize_messages(model,messages,state)。
- [x] 写 clear 保留可见消息、compress 前摘要合并及失败不损坏、missing 能力错误、valid hints 经 Runtime、自动压缩回归。
- [x] 执行失败测试。
- [x] 抽取共享公共摘要 helper；使用 SkillRegistry.scan 与 MCPManager.servers 元信息；自然语言 hint 走 Runtime。
- [x] 补全 Skill/MCP 名称及键盘交互；模块测试、生产构建、浏览器验证；提交 Phase 4。
- [x] 记录原始基线限制，保存验收报告，本地预览交由用户检查，到此停止。

## Final evidence
- Backend 44 passed；Frontend 12 passed；Ruff / Pyright / ESLint / Prettier 通过；Vite build 成功。
- 独立审查发现的 5 项问题全部补充回归测试并修复；浏览器验收结果与范围见 docs/PHASE4_REVIEW.md。
- 保留本地 feature/xiliu-web-phase4，等待用户检查；不执行 Phase 5、push 或 merge。
