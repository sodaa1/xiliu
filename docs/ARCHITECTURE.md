# 息流 Web 项目架构

本次截止 Phase 4。根目录保留上游 xiliu 的结构，Web 只增加薄适配层。

```text
xiliu/
├── .env                              # 本地密钥与模型配置（忽略）
├── .env.example                      # 无密钥配置样例
├── pyproject.toml / uv.lock           # Python 依赖与锁文件
├── src/xiliu/
│   ├── config.py                     # 兼容原配置，新增 provider
│   ├── runtime.py                    # 原 Runtime；Web 直接 stream_session
│   ├── graph/memory.py               # 自动/手动压缩共享 summarize_messages
│   ├── cli/__init__.py               # 兼容原命令，增加 web 启动入口
│   ├── api/
│   │   ├── __init__.py                # Web 包
│   │   ├── app.py                    # app factory、错误处理、静态 SPA
│   │   ├── errors.py                 # 稳定且不含密钥的 Web 错误
│   │   ├── schemas.py                # 请求校验与数据契约
│   │   ├── model_catalog.py          # Provider/model 集中预设
│   │   ├── store.py                  # sqlite3、WAL、短连接、事务
│   │   ├── routes/
│   │   │   ├── __init__.py            # 路由包
│   │   │   ├── models.py              # Catalog 与 Settings GET/PUT
│   │   │   ├── conversations.py       # CRUD 与 NDJSON 对话流
│   │   │   └── capabilities.py        # 命令、Skill、MCP 元信息
│   │   └── services/
│   │       ├── __init__.py            # 服务包
│   │       ├── model_settings.py      # 原 .env 复用、校验、密钥保留
│   │       ├── conversations.py       # Context 和无效 override 回退
│   │       ├── chat.py                # Runtime→WebEvent、最终回答持久化
│   │       └── commands.py            # /clear /compress /skill /mcp
│   ├── capabilities/                 # 原 Skill/MCP/Gateway 通道
│   └── automation/                   # 原调度与 AutomationStore
├── web/
│   ├── package.json / package-lock.json # 前端依赖、锁文件与脚本
│   ├── index.html                    # Vite SPA 文档
│   ├── vite.config.ts                # /api 开发代理、Vitest
│   ├── tsconfig.json                 # 严格 TypeScript
│   ├── eslint.config.js              # React/TS 检查
│   ├── .prettierrc.json               # 统一前端代码格式
│   ├── public/favicon.svg            # 复用 Lucide 品牌图标
│   └── src/
│       ├── main.tsx                  # React 挂载、QueryClient
│       ├── app/App.tsx               # Sidebar、路由、后续导航占位
│       ├── components/Brand.tsx      # 轻量品牌图标
│       ├── features/assistant/
│       │   ├── AssistantPage.tsx      # 会话查询、发送、模型覆盖
│       │   ├── ConversationList.tsx   # 分组、新建、切换、删除菜单
│       │   ├── MessageList.tsx        # Markdown、事件分隔、滚动
│       │   ├── Composer.tsx           # 输入、命令及能力名称补全
│       │   ├── AssistantPage.test.tsx # 会话交互、竞态与卸载取消
│       │   └── Composer.test.tsx      # 命令/能力名称与 IME 交互
│       ├── features/settings/
│       │   └── SettingsPage.tsx       # 实际可用的模型设置
│       ├── lib/
│       │   ├── api.ts                # HTTP、错误解析、NDJSON reader
│       │   ├── api.test.ts           # 跨 chunk/UTF-8/错误流测试
│       │   └── types.ts              # 明确的数据契约
│       ├── styles/app.css            # 参考图浅色样式与响应式
│       └── test/setup.ts             # Testing Library 初始化
├── tests/
│   ├── unit/test_model_settings.py   # 厂商、模型、密钥保留/脱敏
│   ├── unit/test_conversation_store.py # CRUD、seq、上下文与并发
│   ├── unit/test_chat_service.py     # fake Runtime 边界、落库、错误
│   ├── unit/test_commands.py         # 清理、压缩、hint、稳定错误
│   ├── unit/test_web_memory.py       # 共享摘要/原自动压缩回归
│   ├── integration/test_api_health.py # 启动、健康、设置错误
│   └── integration/test_conversation_api.py # 完整 API/NDJSON 契约
├── docs/reference/                   # 原文档与 01–08 PNG 参考图
├── docs/superpowers/plans/           # 分阶段计划
├── docs/PHASES.md                    # 进度、测试证据、接口适配记录
├── docs/PHASE4_REVIEW.md              # 本阶段验收入口、结果与边界
└── start-xiliu.bat                   # Windows 双击启动本地预览
```

后续 Phase 5：api/services/content.py、routes/inbox.py、routes/knowledge.py、web/src/features/inbox/ 与 knowledge/；Markdown 原文 + 原附件 + SQLite FTS5。
后续 Phase 6：services/feed.py、tasks.py；routes/feed.py、tasks.py、automations.py、today.py；对应前端 features/feed/、today/、automations/；复用现有 AutomationStore。
Phase 7：完整回归、真实 provider/MCP smoke 与完整交付。

数据边界：app.sqlite3 只存 Web 对话，Runtime workspace/checkpoint 原机制不变。Today 不建独立业务库。前端不接触 API key，也不调用 TUI/CLI 进行对话。

Web 向 Runtime 传入 `include_workspace_history=False`，会话上下文以 SQLite 为准；默认值为 True，保留 CLI/TUI 的原工作区记忆行为。当前轮新增笔记与自动压缩摘要仍可用于 workflow。
