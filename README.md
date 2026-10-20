# 息流 · xiliu

![息流主页：内置背景与角色](docs/assets/xiliu-home-background.png)

[简体中文](README.zh-CN.md) · [English](README.en.md)

[在线体验游客演示](https://sodaa1.github.io/xiliu/#/today) · 免安装、免 API Key，使用示例数据和演示回复。

*应用主页截图（已启用内置背景），可在设置中切换主页背景。*

**信息有归处，思考自成流。** 息流是本地优先的个人信息与 AI 助手，把 Feed、Inbox、Knowledge、Assistant 和 Today 连接成从发现到行动的信息流。

当前版本：**0.4.5**。React 界面和 FastAPI 业务层复用 Runtime / LangGraph；Windows 桌面使用 Tauri 2。资料与会话保存在本机，启用模型或联网工具时，对应请求会发送至用户配置的服务。

## 完整网页版部署包

完整版支持注册登录、独立资料空间、自带模型 API，以及可选的每账号累计 5 次公共模型试用。免登录游客入口保留示例数据和演示回复。

按 [Docker 部署指南](docs/CLOUD_WEB_DEPLOYMENT.md) 自行部署，账号资料保存在服务器持久化卷中；备份和账号恢复见 [运维说明](docs/cloud-operations.md)。目前提供可部署源码包，尚未上线公共完整版服务；上方 GitHub Pages 链接仍为游客演示。桌面账号登录和双向数据同步留待后续实现。

云端不开放本机文件、进程、Skill / MCP 和公共搜索凭据；AI Hot 与联网搜索暂不可用。Windows 0.4.5 安装包仍为本地桌面版本。

## 0.4.5 更新

- 白灰与淡紫的统一工作台，保留原版首页与山水首页两种主题；重做助手、资讯、收件箱、知识库与设置。
- 个人计划支持未开始、进行中、已完成状态，以及悬停/键盘/触屏可用的三点任务菜单。
- 内置 16 张有来源署名的高清照片，按主题随机轮换，支持高 DPI、响应式尺寸和本地加载；文章原图与上传背景保持优先。
- 改进收集、阅读、编辑、自动化和新手引导，兼容移动布局、深色、大字号及减少动态效果设置。
- [Windows 安装包与 SHA256](https://github.com/sodaa1/xiliu/releases/tag/v0.4.5)；验收与边界见 [Windows 交付记录](docs/WINDOWS_RELEASE.md)。

## 0.4.4 更新

- 首次打开的分步功能引导，网页和桌面共用；支持跳过和手动重看。
- 统一中文界面和六项导航，合并桌宠拖放反馈与立绘发梢、裙摆惯性。
- [在线演示](https://sodaa1.github.io/xiliu/#/today)免安装体验示例资料与演示回复；此静态站不提供账号与云同步。

## 0.4.3 更新

- 首页默认显示内置背景；保留用户已保存的留白或自定义背景。
- Windows 安装包内置独立桌宠，支持 Q 版与常规比例切换、分别缩放、快捷对话和 Inbox 收录。
- 补齐待机眨眼与微笑、清晰拖动反馈及原生窗口命令权限。默认使用图片表情，真实 Live2D 形变需另行导入模型与 Core 资源。

## 0.4 更新

- 应用业务统一通过一个 `app` 工具和 ActionRegistry，复用页面原有 Service。
- 明确的本地操作走 Fast，零模型、零 Supervisor；可选 AI 元数据归档作业持久化并支持重启恢复。
- Feed 支持手动添加、编辑、删除和恢复，外部资讯支持隐藏和恢复；非敏感偏好通过版本检查同步。
- 人工确认、逐项权限、取消与真实写入校验在执行路径中统一。
- 实测结果见 [0.4 交付记录](docs/XILIU_04_UNIFIED_ACTIONS.md)、[全页面能力矩阵](docs/audit/all-pages-capabilities.md)、[性能](docs/audit/fast-performance.md)和[包体积对比](docs/audit/package-size-before-after.md)。

## 0.3 更新

- **资料操作接入 Agent**：`inbox_import`、`inbox_list`、`knowledge_folders`、`knowledge_folder_create`、`inbox_classify` 复用页面服务。多个 URL 分别导入，用户明确要求保存时可将未匹配文件夹的卡片保存到 Knowledge。
- **多会话与停止回复**：每个聊天单独保存运行状态和请求控制器；可同时使用其他聊天，只停止选中的会话，保留已收到的思考内容与已完成操作。
- **可调整布局**：主侧栏最小 144px，对话侧栏最小 160px，输入框高度 48–98px；支持拖动、键盘调整和刷新后保留尺寸。
- **桌面与模型连接**：上传区使用 HTML5 拖入；保留 SDK 思考流与聊天历史。字面本地模型地址绕过系统代理，外部地址保留代理；连接和认证错误直接返回，不被路由器转成重复任务重试。
- **AIHot 默认配置**：首次启动补入公开 MCP 配置，保留已有用户配置；读取资讯不依赖模型 API Key。

详见 [0.3 修复记录](docs/XILIU_03_FIXES.md) 与 [0.3.1 天气检索及桌面检查点修复](docs/XILIU_031_FIXES.md)。0.3.1 补齐实时天气检索、统一搜索重试预算及 Windows Git 子进程启动。[0.3.2](docs/XILIU_032_FIXES.md) 补齐文件夹创建与指定归档，保留 Inbox 生成的标签。

## 功能与工作流

**发现 → 收集 → 整理 → 提问 → 行动**

| 模块 | 功能 |
| --- | --- |
| Feed | AI Hot、GitHub Top 5、来源状态、收藏与 Ask AI。 |
| Inbox | 收集文字、URL 和文件；保留来源与原件，后台提取、可选 AI 整理、编辑与归类。 |
| Knowledge | 标签与规则文件夹、中文混合检索、原资料引用、可选 embedding。 |
| Assistant | 多会话、Markdown、模型切换、思考过程、本轮参考、停止回复、Skill / MCP。 |
| Today | 资讯与待办聚合，创建、编辑与完成任务。 |
| Settings | 模型、个人、外观、数据与自动任务；浅色 / 深色 / 跟随系统、减少动态效果。 |

## Windows 安装

从 [GitHub Release v0.4.4](https://github.com/sodaa1/xiliu/releases/tag/v0.4.4) 下载 `Xiliu-0.4.4-x64-setup.exe` 与 SHA256 校验文件。安装包作为 Release 附件发布，不存入 Git 源码。

1. 双击安装包，使用中文向导安装并启动「息流」。无需另装 Python、Node.js 或 Rust。
2. 首次启动在设置中自行填写模型提供商、API 地址、模型名称和 API Key。安装包不包含开发者密钥、个人模型配置、数据库、测试或项目文档。
3. 将资料收集到 Inbox，归类到 Knowledge，再在 Assistant 中引用资料提问。

支持 Windows x64，需要 WebView2；缺少时安装引导程序需联网下载。当前安装包未签名。桌面资料位于 `%APPDATA%\io.xiliu.desktop`，开发 Web 默认使用项目 `.xiliu/`。升级前退出应用并备份完整数据目录，无需为升级删除已有资料。

构建与验收边界见 [Windows 交付记录](docs/WINDOWS_RELEASE.md) 和 [桌面说明](desktop/README.md)。

## 从源码运行

需要 Python 3.12+、uv、Node.js / npm，在项目根目录执行：

```powershell
uv sync --dev
cd web
npm ci
npm run build
cd ..
uv run xiliu web --open
```

Windows 可双击 `start-xiliu.bat`。默认 `http://127.0.0.1:8765`。开发前端执行 `npm run dev`，另一个终端在项目根目录执行 `uv run xiliu web`。CLI 命令见 `uv run xiliu --help`。

Windows 源码打包还需要 Rust MSVC 与 Microsoft C++ Build Tools / Windows SDK：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

脚本依次构建前端、冻结服务、Tauri / NSIS，导出版本对应的 `.exe` 和 SHA256 到 `dist/`。

## 模型与联网配置

通过设置页填写模型配置，或复制 `.env.example` 为本地 `.env`。不要提交真实密钥。

| 配置项 | 用途 |
| --- | --- |
| `XILIU_PROVIDER` | 模型提供商。 |
| `XILIU_BASE_URL` | 模型兼容 API 地址。 |
| `XILIU_MODEL` | 对话模型名称。 |
| `XILIU_API_KEY` | 模型密钥；接口不回显明文。 |
| `XILIU_DATA_DIR` | 数据目录。 |
| `XILIU_EMBEDDING_MODEL` | 可选专用 embedding 模型；留空使用本地检索。 |
| `TAVILY_API_KEY` | Search 工具使用的搜索服务密钥，与对话模型 API 分开。 |

对话模型、网页资料识别、AIHot MCP 与 Search 工具是不同调用链；其中一个能联网，不代表其他服务已配置。MCP 可按服务需要提供各自运行环境和配置。完整变量见 [.env.example](.env.example)。

## 内核与 RAG

**Fast** 处理轻量聊天和简单本地查询；**Standard** 使用计划、工具执行与有界验证；**Deep** 按需组织 Todo 与子 Agent。API 的可选 `mode` 参数支持指定模式，省略时自动路由；沿用 NDJSON 流和 Gateway 权限链。

工具结果统一为 Evidence，进入 GraphState、Memory 和 Verifier。RAG 与 Knowledge 共用 SQLite；资料变化进入持久化后台队列，查询不触发全量索引，向量只重算变化片段。默认全文与元数据检索不需要向量服务；首次 RAG 迁移保留 `app.pre-rag.sqlite3` 备份。

数据目录 `agents/` 提供 `rag`、`research`、`code` 模板，子 Agent 权限按父级范围收窄。详见 [0.2 内核交付](docs/XILIU_02_KERNEL_RAG.md)。

## 验证与当前边界

2026-10-09 本次主干回归：后端 **124 passed / 1 skipped**，前端 **33 passed**。跳过项为 Windows 缺少创建符号链接权限的既有静态资源用例。详细记录见 [项目进展](docs/DEVELOPMENT_PROCESS.md)。

```powershell
uv run python -m pytest
uv run ruff check src/xiliu
uv run pyright src/xiliu
uv run python scripts/verify_kernel_rag.py
cd web
npm test -- --run
npm run lint
npm run build
```

测试代码随源码维护；开发日志、临时资料和测试工具不进入安装包。离线证明脚本使用假模型，不需要真实供应商密钥。

- PDF / DOCX 可提取文字，扫描件暂不做 OCR；保存 URL 不等于自动抓取全文。
- 停止回复不撤销已完成的写入，也不提供断点继续；同步外部请求可能等待下一段流数据或超时后才释放。
- 节点内部工具批次崩溃时尚不提供逐工具 exactly-once 恢复；知识库面向单用户，工具权限不等于系统网络隔离。
- 桌面包不携带开发解释器、pytest、ruff；Code Agent 的 Python 脚本与测试执行请使用源码开发环境。
- 0.3 SDK / Graph / HTTP 链路用本地虚拟 API 验证，没有使用用户真实密钥；原生桌面窗口拖入和全新设备的 WebView2 下载流程尚未进行交互式验收。

## 文档与来源

[中文文档](docs/README.zh-CN.md) · [English documentation](docs/README.en.md) · [开发进展](docs/DEVELOPMENT_PROCESS.md) · [English progress](docs/DEVELOPMENT_PROCESS.en.md) · [架构](docs/ARCHITECTURE.md) · [阶段记录](docs/PHASES.md)

源内核来自 [sodaa1/xiliumini](https://github.com/sodaa1/xiliumini)，基线 `6d3689583f93b3fafd6381b2b65c31d9613464e5`；本项目品牌、包名、CLI 与配置使用 `xiliu`。

产品介绍网站源码、脚本与设计资料位于 [`docs/web/`](docs/web/README.md)，应用构建继续提供 `/intro/` 入口。公开介绍：[息流 · xiliu](https://933693.xyz/projects/xiliu/)。

## 产品介绍概念图

![息流产品介绍](docs/web/assets/xiliu-intro-concept-a.png)

*上图为产品介绍页的视觉概念，卡片内容为设计示意。*
