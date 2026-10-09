# Phase 进度与证据

开发过程概览、当前架构树及执行循环见 [DEVELOPMENT_PROCESS.md](DEVELOPMENT_PROCESS.md)；本文件保留各阶段的历史验收证据。

## Phase 0
- 上游 main：6d3689583f93b3fafd6381b2b65c31d9613464e5。
- .env 已存在；仅读取变量名称、model/data_dir 等非密钥字段；不修改原配置。
- 原始 uv run pytest -q：4 个 collection errors。上游 tests/agent_fakes.py 与 tests/__init__.py 没有包含在版本控制中；受影响：test_automation_runner、test_extension_verification、test_hook_lifecycle、test_scheduler。
- 后续以 python -m pytest 核对路径因素；不重写无关测试。
- 执行决策：在空的用户工作区拉取独立源码后，在 feature/xiliu-web-phase4 工作，不再创建第二份 worktree；用户已要求到 Phase 4 后检查，跳过中途审批。
- 测试文件在上游被 tests/ 忽略；新增本次测试用 git add -f 明确提交，避免扩大 .gitignore 对原仓库的影响。
- 计划与原设计冲突时以现有公共接口最小适配；最后保留工作目录供用户检查。

- python -m pytest 排除入口路径问题后仍有 2 个 collection errors：test_extension_verification、test_hook_lifecycle 均缺 tests.agent_fakes；后续全量验证分别报告原始失败与排除这两文件的结果。
- 本机 Git 无 author identity：本次本地提交显式使用 Codex 自动化身份，不更改全局 Git 配置。

## 用户补充范围
- 全面改名 xiliu：Python 包、CLI、XILIU_* 环境变量、.xiliu 数据目录、Skill 名称。原 .env 备份为忽略的 .env.pre-xiliu.backup，密钥值未变。
- 已授权清理原版测试与过时 specs/plans/PRD；保留当前测试、原始 UI 参考和所有 Runtime 模块。基线问题已记录，不再作为本次测试集的一部分。
- 原始 docs/reference 保持附件原文，仓库 origin 保持上游地址，以便追溯来源。

## Phase 1 完成
- src/xiliu/api：App factory、错误脱敏、模型 catalog、ModelSettingsService；新增 Settings.provider。
- 测试先因缺少 api 包失败，再实现通过：10 passed；Ruff passed；整个 src compileall passed。
- DeepSeek preset 使用本地已配置 deepseek-flash 为 canonical，保留 v4-flash 别名；来源 https://api-docs.deepseek.com/api/responses 。
- 本地配置已迁移 XILIU_*，未进行任何付费 API 调用。

## Phase 2 完成
- 新增 AppStore、ConversationService、ChatService 与 conversations API。
- 原 Runtime 的唯一行为扩展：公开 close() 释放短生命周期 MCP 资源；不改 stream_session 调用约定。
- RED：模块不存在导致 2 collection errors；GREEN：全部 19 passed，涵盖 12 并发追加、同会话忙保护、context 不重复当前问题、错误无密钥、删除级联、NDJSON 中文与换行。
- 未调用真实 provider；下一阶段 React Assistant。

## Phase 3 完成
- React/TypeScript/Vite SPA，三列浅色 Assistant、会话分组/切换/删除、独立 Query cache、Markdown 与 Settings。
- readNDJSON 支持逐字节 UTF-8 中文、跨行缓冲、HTTP/JSON 错误。
- 测试先失败于组件/reader 缺失；空初始会话额外复现了 null status 问题并修复。前端 6 passed。
- 为用户 Phase 4 检查提前加入 xiliu web --open、静态 SPA 托管、start-xiliu.bat。后端 SPA/CLI 测试先失败再通过。
- 下一阶段命令执行与 Runtime Memory 共享压缩。

## Phase 4 完成
- 实现四个命令及 metadata API：/clear 更新 cutoff 保留可见消息；/compress 合并前摘要并复用公开 summarize_messages，失败不覆盖；/skill 与 /mcp 生成 hint，经原 Runtime/Gateway 执行。
- Composer 支持命令和能力名称筛选、键盘 Enter/Tab/方向键、IME 组合输入保护。
- 先写命令/共享 Memory 失败测试再实现；独立审查发现 5 项问题，补充失败回归并逐项修复：旧工作区记忆恢复、Host 检查、首次重复发送/卸载、模型 PATCH 跨会话缓存、默认 endpoint 不一致。
- Runtime 增加兼容关键字 include_workspace_history=True。Web 为 False，不载入前轮 HISTORY_SUMMARY/NOTEPAD；只保留本轮追加笔记与 state 摘要，CLI/TUI 默认不变。文件不删除、不改写清空。
- 实际 Runtime + LangGraph 的 chat/workflow 接入通过离线模型验证；关闭生成器释放 Runtime 和会话保留锁。
- 最终后端 44 passed，前端 12 passed；Ruff、Pyright（项目 .venv）、ESLint、Prettier 全通过；Vite 生产构建成功。
- 浏览器：1600×1000 与 390×844 页面通过，空会话、新建/切换、模型覆盖、Skill/MCP 补全、clear 分隔、Settings 密钥不回显均检查；无 pageerror/console error。窄屏会话栏改为横向，聊天区域恢复可用宽度。
- npm audit 0 vulnerabilities。Vitest 升级 4.1.11，兼容本机 Node 24 / Vite 7，官方修复依据：https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9 。前端源码统一 Prettier，仅格式变化。
- web/tsconfig.tsbuildinfo 属构建产物，从 Git 移出并忽略。原 .env 与 SQLite 未加入提交。
- 真实付费 provider/MCP 执行烟雾测试留待 Phase 7；当前只读取本地能力元信息。Phase 5/6 未实现。
- 自动审批拒绝按消息内容批量删除早期浏览器样例，因为无法证明来源；保留该会话。后续只清理脚本本轮明确记录的新建 ID，安全清理已成功。
- 按用户要求，到此等待 Phase 4 检查，保留工作区与本地预览。

## Phase 4 用户修复与 Phase 5–7 完成（2026-10-07）
- 修复侧栏折叠、思考折叠与分秒计时、切页继续对话、实际模型身份、简单聊天思考预算、clear 删除内容、DeepSeek 旧预设迁移。
- Inbox / Knowledge 支持三类收集、保留原件、Markdown、中文检索、编辑标签、状态迁移、Ask AI 本轮参考；20 MiB 文件边界和安全路径已验证。
- Feed 复用既有 Gateway / Policy / Hook 读取 AI Hot；GitHub 读取官方 Trending Top 5。支持缓存、来源失败提示、搜索、Read / Save / Ask AI。
- Tasks 与 Today 聚合完成；Automations 抽屉复用既有 AutomationStore / Scheduler / Runner，支持每日创建、启停、删除及最近运行记录。Settings 增加数据状态，品牌启动页与 reduced-motion fallback 已实现。
- 独立审查复现并修复跨实例 Save 重复入库，以及停止调度时过早释放 owner；内容事务去重与关闭期间续租/等待资源释放均加入回归。
- 最终后端 72 passed；前端 16 passed；Ruff check / format、Pyright、ESLint、Prettier 通过；生产构建成功（515 kB 单包大小提示，不影响构建）。
- 浏览器隔离数据：1600×1000 与 390×844，全部七页无横向溢出；收集/编辑/移动/原件下载、Feed 筛选保存、Ask AI 临时参考、切页继续对话、clear、待办全操作、自动任务创建暂停记录删除均通过。pageerror 为 0，截图已人工查看。
- 真实 DeepSeek 当前配置 deepseek-v4-pro 正确回报模型身份，本次 2.66 秒；compress 成功。AI Hot 10 条、GitHub 5 条真实资讯刷新成功；修正了 AI Hot 的嵌套 links 原始格式。
- 新增测试与实现保留为本地改动供审阅；原 UI 参考文档、已有密钥与用户数据保留。完整验收入口：docs/COMPLETION_REVIEW.md。
- 收尾复审修复了关闭后排队 sync 重启 scheduler 的竞态，以及 ISO basic date 使待办编辑器崩溃的问题。
- 真实 MCP 命令发现 Planner 缺少 todo_update，导致资讯已读取仍以 pending 重试。补齐工具、提示与严格参数校验；离线回归先失败后通过，真实命令首次验证通过（57.22 秒）。最终全量更新为 72 后端 / 16 前端。
- 8765 正式预览已更新并验证 health、15 条真实 Feed 缓存、Today、Settings；无页面异常。临时验收服务已关闭。

## 银河启动页（2026-10-08）

- 用 Canvas 银河替换简化 SVG 曲线：星点旋转并向中心汇聚，开场 2.6 秒后保持流动；支持立即跳过、页面隐藏暂停与 reduced-motion 静态画面。
- Enter 接入用户提供的 Uiverse / Codecite 渐变、高光与悬停样式，并保留键盘焦点提示。
- 前端全量 17 passed，ESLint、Prettier 与生产构建通过。浏览器检查开场时长、持续动画、跳过、Enter 导航、390px 布局与 reduced-motion，pageerror 为 0，桌面/手机截图已人工查看。后端本次未改动。

## Knowledge / Settings / Desktop 增量（2026-10-08）

- 完成统一 Inbox 后台导入、文字/PDF/DOCX 抽取、规则文件夹、批量归类、人工修正版本保护、索引迁移和恢复。
- 完成默认本地混合检索与可选 embedding，知识库工具经既有权限链供 Assistant 调用，证据链接可返回原资料。
- 设置新增个人/外观/模型/自动化/数据分组；GlideSelect、快捷导航、字体主题和减少动态真实生效。Today 五项预览及完整待办面板适配桌面尺寸。
- 后端全量 88 passed，前端 24 passed；静态与构建检查通过。实际浏览器无运行错误，独立打包服务启动、关闭、端口释放通过。
- Tauri 薄壳与桌面偏好备份代码完成；系统缺 Rust/Cargo/MSVC，安装授权待答复，因此安装包构建和安装验收仍未完成。完整记录见 `COMPLETION_REVIEW.md` 与 `desktop/README.md`。

## 2026-10-09 · 0.2 内核与 Windows 安装包

- 三模式 Fast / Standard / Deep、Evidence、Agent Registry、共享 RAG 与后台增量片段索引已接入，保持原 API / CLI 和 NDJSON 兼容；内核交付验证为后端 111 passed / 1 skipped、前端 30 passed，静态检查与构建通过。见 [0.2 内核记录](XILIU_02_KERNEL_RAG.md)。
- 补齐 Rust MSVC、C++ 构建工具及 SDK；完整发布脚本生成中文 NSIS 安装包 `dist/Xiliu-0.2.0-x64-setup.exe`，38,323,101 字节（36.55 MiB），附带 SHA256。
- 按用户要求仅分发核心运行代码、生产前端和必要依赖；排除项目文档、测试框架、开发工具、CLI / TUI、source map、日志、数据库、开发者配置和密钥。用户首次启动自行设置模型 API。
- 实际安装到项目临时目录，安装后服务的 ready 令牌、前端、Knowledge 查询、API Key 未配置、退出及端口释放通过；真实窗口、WebView2 和服务启动通过，关闭窗口后自有服务退出。测试安装已卸载。
- 中文 README、桌面构建说明和项目进展已更新。代码未签名，未验证全新设备缺少 WebView2 时的下载流程，未请求真实模型 API。详细证据见 [Windows 交付记录](WINDOWS_RELEASE.md)。

## 2026-10-09 · 0.3 主干文档与 GitHub 上传

- 更新根目录及 docs 中的完整中文 / English README；现有产品介绍图位于 README 开头，并标明视觉概念的示意性质。
- 项目进展补入 0.3 应用写入工具、多会话与停止回复、布局调整、思考流、连接错误及代理处理、AIHot MCP 默认配置；另提供英文进展与双语文档索引。
- 重新验证主干源码：后端 124 passed / 1 skipped，前端 33 passed；Ruff、Pyright、ESLint 和 TypeScript / Vite build 通过。现有 0.3 安装包的字节数和 SHA256 重新核对。
- 主干上传至既有 GitHub 仓库的 main；测试、日志、密钥、用户资料与安装产物不进入 Git。天气搜索循环和桌面检查点的新修复保留在独立 codex/fix-desktop-search 分支，不声明已解决。
