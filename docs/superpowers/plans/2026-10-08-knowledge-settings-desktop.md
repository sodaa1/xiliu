# 息流知识库、完整设置与桌面交付计划

> **For agentic workers:** 使用 superpowers:executing-plans 执行当前任务；独立领域按 dispatching-parallel-agents 拆分，最后统一审查与验证。不自动提交或改写已有未提交改动。

**Goal:** 完成统一导入、规则文件夹、知识检索、常规设置、工作台适配和可运行桌面薄壳。

**Architecture:** 复用现有 ContentService、AppStore、Runtime 与 React 路由。元数据后台处理直接调用当前模型；索引与原件共用，不复制 Agent。Tauri 仅管理自有 Python sidecar。

**Tech Stack:** Python/FastAPI/SQLite/React/Vite/Tauri 2。

**Spec:** ../specs/2026-10-08-knowledge-rag-desktop-design.md；用户追加批准快捷导航“助手 / Feed / 设置”、设置内自动化、个人信息/主题/字体大小及 GlideSelect 交互，并要求持续开发到交付。

## 共享契约

- 内容 API 保留 type=note/link/file、status=inbox/knowledge，增加 folder_id: string|null、ai_processed: boolean、processing_status: pending|ready|failed、processing_error: string|null。
- Folder: id/name/summary/tags:string[]/priority:number/item_count:number/created_at/updated_at。
- POST /api/inbox/import 接受 text?:string、filename?:string、data_base64?:string、use_ai?:boolean，立即返回 ContentItem；后台最多一次模型元数据调用，匹配文件夹后进入 Knowledge。
- GET /api/inbox；POST /api/inbox/classify-batch {item_ids:string[]} 返回 {items:ContentItem[]}；POST /api/inbox/{id}/retry 返回 ContentItem。任务状态在 SQLite 持久化，生命周期恢复与关闭可等待。
- Folder CRUD /api/knowledge/folders；GET /api/knowledge/folders/{id}/items；GET /api/knowledge/search?q=&mode=auto&limit=6 返回 {mode_used,channels,items:[document_id,title,summary,matched_tags,snippet]}。
- PATCH /api/content/{id} 支持 folder_id，人工变更标签重新归类，显式 folder_id 优先。删除文件夹不删内容，未分类仍为 Knowledge。
- KnowledgeService(content:ContentService)，list_folders/create_folder/update_folder/delete_folder/folder_items；RetrievalService(content:ContentService, knowledge:KnowledgeService)，search(query,limit=6,mode='auto')。
- 所有生产改动采用现有根目录，共享文件归属单一负责人；不要编辑其他领域文件。测试使用隔离临时数据，无真实密钥输出。

## Task 1：完整设置与选择交互（主执行者）

- [x] 新增关键失败回归：个人/外观持久化、快捷导航真实入口、设置内自动化、选择器键盘行为。
- [x] preferences.ts 校验本机偏好与跨页应用；GlideSelect controlled/uncontrolled、滑动高亮、键盘/焦点/减少动态。
- [x] Settings 分组个人、外观、模型、自动化、数据；自动化复用现有管理面板；App 快捷导航助手/Feed/设置。
- [x] 全局字体大小、字体、主题、密度、减少动态设置真实生效，默认保留原风格；验证定向测试、ESLint、构建。

## Task 2：内容与后台导入（content 领域）

- [x] 关键失败测试：迁移保留资料、归类同分/零分、AI 失败保留导入、人工编辑期间后台不覆盖修正。
- [x] 扩展 content.py 的事务与 Markdown、关联表和版本迁移；knowledge.py 规则/文件夹服务。
- [x] inbox.py 持久化后台导入/恢复/重试/批量；extract_text.py 支持文本、PDF、DOCX，不含 OCR。
- [x] 新 routes/inbox.py、knowledge.py，并在 app.py 注册与管理后台生命周期；记录定向验证。

## Task 3：检索与 Agent 工具（retrieval 领域）

- [x] 关键失败测试：明确标签快速路径、关系问题 hybrid、无 embedding 回退、Gateway 只读权限。
- [x] retrieval.py 实现 FTS/中文/元数据融合、片段与稳定文档引用；可选 embedding SQLite 缓存、模型/维度/hash 校验。
- [x] tools/knowledge_search.py 接入 core/agent、CapabilityManager、Policy 与 Runtime 数据目录；记录定向验证。

## Task 4：Inbox / Knowledge UI（content frontend 领域）

- [x] 用统一弹窗替换常驻多字段表单，拖放/选择/粘贴，列表轮询 pending，状态重试和目标文件夹反馈。
- [x] 文件夹首页与二级内容页、CRUD、人工修正、批量选择与归类、来源跳转；复用字段/API 契约，保留原件下载。
- [x] 保持现有风格；文件夹卡片参考署名与自适应；覆盖导入与文件夹关键交互测试。

## Task 5：Today / Desktop / 整体收尾（主执行者）

- [x] Today CSS 三段布局，最多三条简报/五条待办，完整待办面板，1440×900/1100×720 不出现整页滚动。
- [x] Tauri bridge 与窗口、Python sidecar 打包入口、ready 检查、自有进程关闭；核实构建环境。独立服务包启动与退出实测通过。
- [ ] Rust/MSVC 安装、Tauri 编译、生成 NSIS 并实际安装验收：等待系统构建工具安装授权。
- [x] 全量 pytest/Ruff/Pyright 与前端 Vitest/ESLint/Prettier/build；真实浏览器关键流程与独立服务生命周期检查。安装版另验。
- [x] 整合审查、更新文档和验证记录，明确实际交付物及限制。

## Review Focus

- 旧 SQLite CHECK、原件与用户数据迁移恢复。
- 后台元数据与人工修改竞态、任务重启恢复。
- 缺少 embeddings 时不可把 Chat Model 当向量模型。
- 大字号/深色/窄窗口、键盘选项与弹层裁切。
- sidecar 仅回收自身进程，并完整关闭已有调度资源。

## 执行记录

- 2026-10-08：用户要求持续开发直至最终交付，不再做阶段性继续确认。原工作区有大量先前改动，全部保留；本期不自动提交。
- Task 1 RED：新增 3 项前端回归失败，原因是组件/快捷导航/设置内自动化尚未实现。

- 最终验证：后端 88 项，前端 24 项；Ruff/Pyright/ESLint/Prettier/build 通过。真实浏览器与打包服务检查通过；桌面安装包保持未完成，cargo metadata 失败于缺少 Cargo。
