# Xiliu 0.4 统一 App 能力交付

本次在 `codex/v0.4-unified-app-actions` 隔离分支实施，以本地 `main@62e873383599eaf6548a2074a7c7bc59e5b6d844` 为基线。主工作区已有的 Intro/文档迁移未被覆盖；测试使用临时数据目录，没有迁移或清理真实用户数据。

## 实际实现

Agent 面向 Xiliu 业务只公开 `app`，协议为 `catalog / describe / execute`。66 个 ActionSpec 统一声明参数、服务绑定、权限、确认策略、幂等及持久化后置条件。Fast、Standard、Deep、RAG/Research/Code 子 Agent、CLI 和后台任务共享这一个入口和原有 Service；子 Agent 的 action 范围继续受限。

明确的本地业务请求经 `ExecutionGateway → AppTool → AppDispatcher → 原有 Service` 执行，不进入 Supervisor。歧义请求最多进行一次结构化意图解析；对象、范围或时间不明确时要求澄清。URL 只保存时不会抓取网页；明确刷新或抓取标题时才调用对应 Service 的受控网络步骤。通用搜索、代码执行和 MCP 保持原有专业能力。

导入链接、确保文件夹、归档是有界工作流，返回真实对象 ID。默认使用本地归类规则；明确要求 AI 标签时提交可恢复的后台归档任务，返回 pending 和 job_id，页面轮询进度。revision 检查保护人工编辑，取消会传播，已完成部分不会伪装成未执行。

Feed 新增手动资讯的添加、编辑、软删除、恢复，以及外部资讯的隐藏、取消隐藏。页面、HTTP 和 Agent 调用同一个 FeedService；用户资讯和隐藏状态独立持久化，刷新不会覆盖。Today 继续使用原 tasks 表；Knowledge、Inbox、Automations、Assistant 和非敏感偏好使用原服务或受控偏好同步。

删除及自动任务等需要确认的操作使用绑定会话、参数摘要、有效期和一次消费的 token。模型不能批准 token；网页弹窗和 CLI 的真人确认回调负责批准。敏感模型设置、当前会话停止/删除等保持受限，凭证读取脱敏。文件上传仍由原页面执行；尚未开放会话附件授权引用，因此 Agent 文件导入明确受限，不访问任意本机路径。

## 修改文件与用途

完整实际文件清单见 [changed-files.json](audit/changed-files.json)。下表列出核心改动；正式测试、CI 和审计文件也进入 Git。

| 文件或目录 | 改动 |
|---|---|
| `src/xiliu/app/actions.py` | 唯一 ActionRegistry、严格参数、AppServices、服务调用及真实状态验证 |
| `src/xiliu/app/dispatch.py` | 逐 action 权限、短事务请求占位、持久回执、会话绑定确认、取消传播 |
| `src/xiliu/app/intent.py`、`fast.py` | 结构化意图、安全约束、确定性工作流及 Fast 执行 |
| `src/xiliu/tools/app.py` | 唯一业务 BaseTool，缺服务明确报错 |
| `src/xiliu/api/app.py`、`routes/app.py` | 原服务注入、HTTP action/真人确认接口 |
| `src/xiliu/api/services/chat.py`、`commands.py`、`automations.py`、`src/xiliu/runtime.py` | 对话/后台/CLI 共用服务与入口，无密钥本地 Fast；显式 MCP/Skill 保留独立工作流边界 |
| `src/xiliu/graph/*`、`agents/*`、`capabilities/*`、`execution/*`、`policy/engine.py` | 模式共享入口、子 Agent 范围、动态权限、回执证据、取消及审计 |
| `src/xiliu/api/services/feed.py`、`routes/feed.py` | Feed 新增业务、SQLite 持久化、URL 抓取限制、刷新/重启一致性 |
| `src/xiliu/api/services/inbox.py`、`routes/inbox.py`、`services/knowledge.py` | 后台归档任务、跨进程 worker 租约、人工 revision 冲突保护、文件夹去重 |
| `src/xiliu/api/services/preferences.py`、`routes/preferences.py` | 偏好版本同步、白名单、冲突控制和旧偏好迁移 |
| `web/src/features/feed/FeedPage.tsx` | 最小增加手动资讯编辑/删除/恢复及外部隐藏控件 |
| `web/src/features/assistant/AppReceipts.tsx`、`MessageList.tsx` | 操作回执、真人确认弹窗和后台归档进度 |
| `web/src/features/content/ContentPage.tsx` | 删除最近导入的内容后取消旧查询，避免继续请求已删除 ID |
| `web/src/lib/*`、`features/settings/PersonalSettings.tsx` | 复用 HTTP 协议、安全偏好同步 |
| `src/xiliu/rag/embedding_config.py` | 从被删除的工具包装中保留 embedding 配置帮助函数；RAG 算法和数据库继续复用 |
| `desktop/build_sidecar.py` | MCP 收集范围收敛为 client；排除开发测试资源，保留动态依赖 |
| `.gitignore`、`tests/`、`web/**/*.test.*`、`.github/workflows/app-actions.yml` | 正式测试纳入版本管理，CI 自动阻止未登记的新页面/API/Service 动作及零散业务工具 |
| `scripts/audit_app_surface.py`、`verify_all_app_actions.py` | 自动扫描页面、HTTP 和 Service，核对注册、分类、真实 test/方法绑定 |
| `scripts/run_browser_e2e.py`、`tests/e2e/all_pages.mjs` | 真实浏览器点击、UI/Agent 数据库等价与重启检查 |
| `scripts/verify_desktop_service.py`、`measure_sidecar_baseline.py`、`benchmark_app_fast.py` | 发布载荷烟测、启动/内存/体积测量和分层性能原始样本 |
| 版本及 lock 文件、README | 版本统一为 0.4.0；未升级其他运行依赖 |

## 删除与保留

物理删除 `src/xiliu/tools/app_tools.py` 和 `src/xiliu/tools/knowledge_search.py`，共 211 行旧工具包装。迁移了 `inbox_import`、`inbox_list`、`knowledge_folders`、`inbox_classify`、`knowledge_search`、`knowledge_get` 等模型入口，删除相应旧注册、权限别名、特殊上下文和重复验证分支。生产调用不再依赖这些名称。

保留 ContentService、InboxService、KnowledgeService、TaskService、AutomationService、RAGService、SQLite/Markdown 数据格式、CLI/TUI、MCP client、TLS/加密运行时和中文字体。新增代码用于原本缺失的 Feed 业务、权限/回执/异步状态及可复现验证；没有以删除用户数据换取体积下降。

## 测试与覆盖证据

- [全页面功能矩阵](audit/all-pages-capabilities.md)：逐条源码操作面、UI/HTTP/Service/Action/权限及测试引用。
- [覆盖门禁结果](audit/coverage-results.json)：静态清单完整性与未实现项；静态绑定不等于浏览器已点击。
- [实际测试运行结果](audit/test-execution-results.json)和 [pytest JUnit](audit/backend-results.xml)：以最终运行记录为准。
- [真实浏览器报告](audit/browser-e2e/report.json)：全页面访问、关键业务按钮、UI/Agent 同 fixture 状态对照及两次服务重启。
- [独立核心审查](audit/core-review.md)：曾发现的问题、实际复现和修复后的证据。

测试使用真实临时 SQLite 和 Markdown，检查实际 ID/status/folder_id/tags/文件及 revision，不以模型声称完成作为断言。浏览器没有 mock App API 或业务 Service；外部资讯提供方用受控 fixture。模型兼容协议测试使用本地受控 provider，不能据此宣称任意外部模型和网络提供方均已通过。

## Fast 性能

[性能报告](audit/fast-performance.md)及 JSON 保留原始样本、环境和源码指纹。最终 Gateway 路径每组 10 个新写入样本：

| 请求 | Fast p50 / p95 | Chat p50 / p95 |
|---|---:|---:|
| 链接 → Inbox → 文件夹 → Knowledge | 183 / 269 ms | 196 / 288 ms |
| 100 条 Inbox 本地归档 | 2.33 / 3.33 s | 2.13 / 2.42 s |

这些样本的模型、Supervisor 和外部网络调用均为零。计时包含真实持久化，排除 fixture 准备、断言和 HTTP/浏览器传输。批量本地归档仍同步逐项保存；不能把单项性能目标解释为任意规模批量均在两秒内完成。1000 条的较早 Service 基线约 20.87 秒 p50，已与最终 Gateway 样本分开标注。

## Windows 构建与体积

[发布包对比](audit/package-size-before-after.md)和原始 JSON 给出实际 installer SHA256、字节数、载荷、Top30、重复文件、启动和内存测量。安装包位于隔离工作区 `dist/Xiliu-0.4.0-x64-setup.exe`，发布产物不提交 Git。

旧包来源为已有 0.3.2 发布产物，未独立重建旧依赖缓存，因此不能把总差值全部归因于 MCP 收集裁剪。安装包压缩体积与部署载荷占用分别报告。NSIS 提取后的真实发布程序使用独立空白 data_dir 验证；注册安装、卸载及 WebView2 桌面壳 GUI 操作尚未执行。远端 GitHub CI 尚未运行，当前报告是本机实际结果。

## 复现

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
uv run pytest -q
uv run ruff check src/xiliu scripts tests
uv run pyright src/xiliu
uv run python scripts/audit_app_surface.py
uv run python scripts/verify_all_app_actions.py
cd web
npm test -- --run
npm run lint
npm run build
cd ..
./scripts/build-windows.ps1 -SkipDependencyInstall
```

浏览器运行依赖的独立 Playwright、浏览器路径及 Windows 冻结程序参数见 CI 和验证脚本的 `--help`。测试不需要使用真实用户数据或凭证。

## 最后收敛

按用户要求未继续扩展调度或功能：显式 AI 指令复用原队列；失败重试恢复原 job；归档内容及成功回执在原 ContentService 事务中一起提交，删除版本猜测恢复。新增内部提交钩子不对 HTTP/Agent 参数开放。完整后端 570 passed / 1 skipped；前端 54 passed；浏览器 26 项；覆盖门禁 660 源码项 / 66 actions。最终安装包 38,514,440 bytes，较旧包减少 232,281 bytes。

性能 JSON 保留测量时的源码指纹。Gateway 的本地路径数据在最后的 AI 队列边界修复前采样；本次没有将其改标为新包的重新计时结果。注册安装、卸载和桌面壳 GUI、外部真实模型账户、远端 GitHub CI 尚未执行。
