# Phase 进度与证据

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
