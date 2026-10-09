# 息流 0.3 架构

FastAPI 托管 `web/dist`，React 负责界面。对话直接使用现有 Runtime，Skill、MCP、Policy 和 Hook 沿用原执行通道。

带注释的当前架构树、运行循环和分阶段开发过程见 [DEVELOPMENT_PROCESS.md](DEVELOPMENT_PROCESS.md)。

0.2 增加三模式 Graph、规范 Evidence、Agent Registry 与共享 RAG；0.3 增加复用应用服务的写入工具、多会话状态与协作取消。当前版本与验证见 [中文说明](README.zh-CN.md) / [English](README.en.md)。天气搜索与桌面检查点的新修复在独立分支中。

## 服务与界面

- `api/routes/content.py` 与 `services/content.py`：Inbox / Knowledge、Markdown、原件下载、中文 FTS5 检索。
- `api/routes/workspace.py`：Feed、Tasks、Today、自动任务及数据设置；服务分别位于 `services/feed.py`、`tasks.py`、`automations.py`。
- `api/app.py`：服务挂载、静态文件、调度生命周期。对话与模型 API 保留原路由。
- `web/src/app/App.tsx`：路由外 ChatProvider、可折叠导航、助手/Feed/设置快捷入口。设置内嵌自动化；Inbox 共用内容组件，Knowledge 增加规则文件夹页。`lib/preferences.ts` 与 `desktop/bridge.ts` 管理外观和桌面偏好备份。
- `web/src/lib/workspace-api.ts`：内容和工作台接口；`lib/api.ts`：对话和 NDJSON。响应式样式位于 `styles/`。

## 数据

`app.sqlite3` 保存 Web 会话、内容索引、FTS5、资讯缓存及 Save 映射、待办。内容位于 `content/<uuid>/item.md`；原件使用固定磁盘名称，保留原文件名元信息。Inbox 移到 Knowledge 只更新状态和 Markdown，不复制附件。长词用 FTS5 trigram，短中文词用转义 LIKE。

`automation.sqlite3` 和 `automation-reports/` 由现有 AutomationStore / Runner 使用。Web lifespan 启动现有 AutomationScheduler，每 10 秒续租与同步任务；同目录有其他调度 owner 时保留其所有权。任务执行时读取最新模型设置，完成后关闭 Runtime。Today 汇总已有服务，不另建业务数据库。

## 对话与外部信息

ChatProvider 在页面路由外保持请求；切页与弹窗不会卸载执行状态。用户可显式停止，思考过程和耗时随消息保存。`/clear` 删除当前消息和摘要，保留会话及模型选择。

## Knowledge 与桌面增量

`api/services/inbox.py` 管理持久化后台导入与单 worker，`knowledge.py` 提供纯标签规则与文件夹，`extract_text.py` 提取文本/PDF/DOCX。人工修改推进 revision，过期模型结果不能覆盖；`processing.json` 保存恢复所需的 AI 选择。Markdown 和文件夹快照仍为恢复来源，SQLite 保存关联索引与任务状态。

`retrieval.py` 桥接共享 `rag/` 服务，提供标签快路径与 FTS/中文/元数据混合检索；持久化后台作业索引资料片段，查询不全量重建，可选 embedding 仅重算变化片段。`tools/knowledge_search.py` 经既有 Gateway 与 `knowledge.read` Policy 接入 Agent，引用链接回到 Knowledge 资料。未配置专用 embedding 模型时不调用向量服务。`tools/app_tools.py` 复用 Inbox 的真实导入、查询与归类服务，分类保存带 revision 校验。

`desktop/server.py` 是 PyInstaller 服务入口，资源包含生产前端和公开 MCP 默认配置。Tauri 管理窗口、ready 检查、自有子进程、日志和本机偏好；退出请求与管道 EOF 进入 FastAPI lifespan，超时仅回收自有 Child。0.2 / 0.3 Windows 安装包已生成；不同版本的实际安装和行为验收以 [Windows 交付记录](WINDOWS_RELEASE.md) 为准。

Web 传入 `include_workspace_history=False`，SQLite 提供会话上下文；CLI / TUI 保留 True。Ask AI 参考只加入本轮请求，使用数据标签和 JSON 编码，不写入后续历史。界面允许移除参考并标明长文本截取。文件上传保留原件，不做 OCR 或附件正文提取。

AI Hot 经 MCPManager → ExecutionGateway → Policy / Hook 调用 `aihot_get_latest`。GitHub Top 5 来自官方公开 Trending 页面。失败保留缓存，分别显示来源状态；前端不调用外部模型或连接。

## 启动与验证

启动页位于 `features/launch/`，Canvas 绘制银河粒子旋转与向心流动，开场 2.6 秒后仍持续动画。绘制上限 30 fps、像素比上限 1.5，页面隐藏时暂停；reduced-motion 使用静态最终画面。Enter 样式单独限定作用域，离开启动页时清理绘制与监听器。

Windows 使用 `start-xiliu.bat`，或 `xiliu web --open`。配置与运行数据忽略，不进入代码改动。完整验收见 [COMPLETION_REVIEW.md](COMPLETION_REVIEW.md)，阶段记录见 [PHASES.md](PHASES.md)。
