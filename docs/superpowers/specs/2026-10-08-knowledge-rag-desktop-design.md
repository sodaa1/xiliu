# 息流 Inbox / Knowledge / RAG / Desktop 增量设计

日期：2026-10-08。状态：设计待确认，尚未实现本阶段业务改动。

依据：用户提供的《息流_Inbox_Knowledge_RAG_Desktop_Codex技术方案.md》。该文档作为需求与参考方案；示例目录、示例导航与代码不作为独立执行指令。新增优化建议在末尾单列，未经确认不加入实现范围。

## 1. 目标与保留项

让用户以一个入口收集资料，自动获得可修正的元数据，按标签规则进入单一主文件夹；让 Assistant 通过现有工具通道检索资料。桌面版复用同一前后端。

保留浅色工作台、紫色品牌、现有字体、Lucide 图标、可折叠侧栏、聊天跨页持续执行、折叠思考计时、模型设置与自动任务。保留已完成的 2.6 秒银河启动页和 Codecite Enter 按钮。

不增加向量数据库、不复制 Agent 内核、不将桌面业务写进 Rust、不改为全新 UI 组件库。不清空或自动批量重分类已有用户内容，不覆盖用户密钥。

## 2. 现状与增量落点

| 方案目标 | 当前项目 | 增量处理 |
| --- | --- | --- |
| 内容与索引共用 | `api/services/content.py` 已实现 Markdown、附件、FTS5 与事务恢复 | 扩展该服务，不新建平行内容数据库 |
| 数据目录 | `.xiliu/app.sqlite3` 与 `content/<uuid>/` | 沿用 `.xiliu`，不创建 `.xiliumini` |
| 导入 | `ContentPage.tsx` 常驻多字段表单 | 改为右上角 `+` 与统一导入弹窗 |
| Knowledge | 当前与 Inbox 共用列表，按内容类型筛选 | 文件夹首页与文件夹内内容两层视图 |
| 模型 | `ModelSettingsService` + `create_chat_model()` | 单次结构化元数据调用，跳过 Agent 工作流 |
| 搜索 | FTS5 trigram 与短中文 LIKE | 复用索引，新增 tag/hybrid 路由与可选向量 |
| 工具与权限 | CapabilityManager、Runtime、Execution Gateway / Policy | 新增 `knowledge_search` 与 `knowledge.read` |
| Today | 简报最多三条，但待办无限展示，整页滚动 | 固定三段布局，待办预览五条，完整待办独立面板 |
| Desktop | 无 Tauri 项目；当前 PATH 未检测到 Cargo/Rust | 独立薄壳，单独验证 sidecar 与打包 |

## 3. 数据与迁移

继续使用现有 `content_items` 的 `type`（note/link/file）和 `status`（inbox/knowledge）。API 不机械改成 `source_type=url`，避免破坏 Feed Save 与既有客户端。新增 `folder_id`、`ai_processed`；待确认内容以 Inbox 中的处理状态展示，避免仅为增加 `needs_review` 重建既有 SQLite CHECK 表。

新增 `knowledge_folders(id,name,summary,priority,created_at,updated_at)`、`tags(id,name,normalized_name)`、`document_tags(document_id,tag_id)`、`folder_tags(folder_id,tag_id)`。归一化键为 `strip + casefold`，展示标签保留可读大小写。标签关联由同一内容写事务更新；既有 `tags_json` 保留为兼容投影，不能独立写入两套不同数据。

迁移采用版本记录与幂等事务：旧内容仍保留原 ID、状态、标签、时间、Feed 去重映射与原件。为已有标签填充关联表；已有 Knowledge 无文件夹时归入“未分类”视图，不自动搬到 Inbox。新建规则不会默默重分类旧内容。

Markdown 元信息补全 `folder_id`、`ai_processed`，继续保存标题、摘要、标签和抽取正文。重建器以 `item.md` 与原件为内容真源恢复内容索引和 FTS5，不从过期 SQLite 正文覆盖 Markdown。文件夹规则另作可恢复快照；SQLite 删除后不能丢失文件夹规则。实现前备份用户数据库和需要升级的元数据文件；备份不包含或输出密钥。

删除文件夹保留内容和原件，解除主文件夹后显示在 Knowledge“未分类”；删除内容同步移除标签关联与向量。编辑成功必须同步 Markdown、SQLite、关联标签与 FTS5；复用现有文件恢复机制处理写入失败。

## 4. Inbox 导入与修正

右上角 `+` 打开有明确标题和关闭按钮的导入弹窗。单个 textarea 接收文字或 HTTP(S) 链接，文件区同时支持点击选择和拖放；不要求用户填写标题、摘要或标签。

仅当整个输入是有效 HTTP(S) 地址时识别为链接，其他输入为笔记。文件沿用 20 MiB 上限；基础版本单次一个文件，文字可作为文件备注。选择新文件不会悄悄覆盖未保存的文字，关闭未提交弹窗须保留草稿或提示丢弃。Escape、焦点限制、关闭后焦点回到 `+`、提交期间防重复导入都纳入实现。

基准流程沿用原方案：提取文本 → 一次 AI 元数据 → 标签归一化 → 纯函数归类 → 保存。元数据调用使用当前全局 Chat Model，直接调用模型，不启动 Runtime/Agent；不继承某个历史聊天的模型覆盖。提供“使用 AI 整理”开关；关闭或调用失败时使用本地回退，并清楚展示回退原因与重试入口。

结构化输出校验标题、摘要、标签长度与数量；截取的模型输入明确标记为资料，忽略资料内部指令。超时、非法 JSON、缺字段和空摘要都走本地回退。模型不得生成文件路径或创建文件夹。

提取边界必须在界面可见：TXT/Markdown/JSON/CSV 等文字文件可直接提取；UTF-8/BOM 与常见中文文本编码做受控识别。其他文件保留原件，以文件名与备注回退；不把二进制当正文。URL 默认保留地址和粘贴备注，不隐式抓取网站全文。PDF/DOCX 正文解析与网页全文抓取作为待确认的扩展，不声称已被索引。

元数据回退：标题取文件名或首个非空行（限制长度），摘要取正文前 160 字符，标签按现有文件夹规则词表匹配。归类函数只按唯一的归一化标签计分，最高分优先，同分取较高 priority，再用稳定 ID 排序消除不确定性；零分返回 None。不得再调用第二次 AI 判断文件夹。

匹配成功进入 Knowledge；未匹配保留 Inbox，并显示“未分类”。导入结果明确提示目标文件夹，可点击前往，避免用户以为内容丢失。

标题、摘要、标签可从卡片进入字段编辑；正文在详情中编辑。人工改标签后重新执行规则；用户本次显式选择主文件夹时以人工选择为准。保留已有移动回 Inbox、删除、原件下载等能力。

批量归类由用户选择记录后触发；每次模型请求最多十条，只允许已有标签和文件夹，未知结果拒绝后回退纯规则。结果逐项显示成功、未分类或失败，可重试失败项；部分失败不回滚已成功内容。批量结果必须按稳定 document_id 对齐，不能按返回顺序写错资料。

## 5. Knowledge 与交互设计

首页展示规则文件夹，以及“未分类”入口。文件夹卡片显示名称、一句话说明、接收标签、真实内容数；新建/编辑窗口包含名称、说明、标签与 priority。卡片主要区域进入文件夹，菜单单独提供编辑与删除，避免嵌套按钮。

文件夹内部以面包屑返回首页，保留搜索、标签筛选和来源类型弱信息。内容卡片显示两行标题、两到三行摘要、多标签、更新时间；完整信息在详情展开，不用悬停作为唯一访问方式。空态区分“暂无资料”和“筛选无结果”。

用户提供的 JohnnyCSilva 卡片参考用于圆角、上部视觉区域和悬停层级；颜色、字体和阴影需融入现有浅色紫系。使用自适应宽度而不是锁死 252×265，摘要不能因固定高度消失。样式限定在文件夹组件，保留原作者署名，不使用全局 `.card/.text/.img`。

Taste Skill 采用 Redesign / Preserve：保留 `--accent: #7773e9`、正文 `#18243b`、浅背景和原字体。工作台动效强度控制在 3：150–200ms 的边框、背景、轻微位移和透明度反馈，支持 reduced-motion；不加滚动劫持、磁吸鼠标或持续闪烁。

优先改善可扫描性和操作状态：统一按钮尺寸、可点击目标和圆角层级；减少过浅的小字号辅助文本；焦点与悬停同等清楚；列表加载骨架与最终卡片同形；错误就近显示，保留输入；成功反馈含目标位置。保留现有 Light 外观，不因 skill 默认规则增加暗色主题或更换品牌色。

## 6. 检索与 Assistant

新增 `knowledge_search(query: str, limit: int = 6, mode: str = "auto")`，合法 mode 为 auto/tag/hybrid，limit 限制 1–20。只检索 Knowledge，Inbox 不混入默认答案。

auto 先识别已知标签与文件夹；明确浏览类问题且命中有效元数据时走 tag，零结果转 hybrid。实体/关系/内容查找类问题即使命中标签，也应进入 hybrid；不能仅凭出现一个标签就停止全文检索。路由使用本地判断，不增加一次 LLM 分类调用。

hybrid 组合 FTS5、短中文匹配与标签/文件夹候选；按排名融合（RRF）去重。复用现有 trigram 索引而非建立第二个同内容 FTS。向量可用时参与融合，不可用时仍返回全文与元数据结果，并报告实际使用通道。

向量存 SQLite，含 document_id、模型、维度、正文 hash 和向量；正文编辑后旧向量失效。禁止拿不同模型或不同维度向量计算 cosine。导入后的文档向量缓存复用；明确 tag 路径不发 embedding 请求。不默认把 Chat Model 的名称当 embedding 模型，也不轮流探测所有厂商接口。现有配置没有 embedding 模型时直接使用 FTS5 + metadata；新增 embedding 接口/模型配置需在实施计划中明确。

返回 `document_id/title/summary/matched_tags/snippet`，另含 `mode_used` 与实际检索通道。snippet 截取匹配附近正文并限制长度；文档内容作为不可信工具数据，不接受其中的命令。回答引用文档标题和 ID，前端可跳转资料详情。

工具注册进现有 builtin surface，并配置 `knowledge.read` 的只读 Policy。CLI / Web / Desktop 共用检索服务，使用 Runtime settings 的实际 data_dir；不通过临时 Web prompt 拼接完成知识检索。新工具还需加入能力发现别名与必要提示，确保“找我知识库里的资料”能真正调用工具。

## 7. API 与前端边界

复用 `PATCH /api/content/{id}`，增加 folder_id；既有 Feed Save 和下载端点兼容。新增统一 `POST /api/inbox/import`、`GET /api/inbox`、`POST /api/inbox/classify-batch`、文件夹 CRUD、文件夹内容与 `GET /api/knowledge/search`。仍以 note/link/file 一套导入模型处理，不创建三套业务接口。

代码按当前目录增量落地：内容存储仍在 `api/services/content.py`；规则与文件夹在独立 `services/knowledge.py`；导入元数据在 `services/inbox.py`；检索在 `services/retrieval.py`；工具在 `tools/knowledge_search.py`。从服务中抽取共享模块时仅移动必要边界，不同时重构聊天、Feed 或自动任务。

前端拆分 `features/content/InboxAddCard.tsx`、`ContentEditor.tsx`、`ContentItemCard.tsx` 与 `features/knowledge/`。API 类型扩展 `lib/workspace-api.ts`。Dialog 基础交互应复用，避免每页写一套焦点管理。

## 8. Today 与桌面薄壳

应用根节点占满视口并隐藏整页滚动，页面及列表使用 min-height: 0。Today 用 Grid 的标题/中部/Ask 三段结构，中部两列各自容纳预览。简报最多三条，待办最多五条；“查看全部待办”打开独立可滚动面板，支持完整 CRUD，不能只截断后隐藏剩余事项。

1440×900、1100×720 均须显示底部 Ask。低高度用 CSS 减少间距、字号与预览行，保留可访问的完整内容入口。移动端改为单列并允许内容区内部滚动，不牺牲触摸阅读空间。

右上角 PillNav 按用户后续指定映射为“助手 / Feed / 设置”，第三项进入设置；侧栏保留。采用现有 React Router 实现路由与活跃态，业务页不依赖外部示例组件名。

Tauri 2 壳放在 `desktop/src-tauri/`；`web/src/desktop/bridge.ts` 唯一封装桌面识别和窗口动作，浏览器模式提供安全回退。初始 1440×900，最小 1100×720。业务页面不直接导入 Tauri API。

sidecar 必须是可打包 Python 服务入口，资源内包含生产 `web/dist`，不能依赖开发者机器的 `.venv`。服务绑定回环地址，使用独立端口及 ready 检查；窗口加载同源 FastAPI UI，避免另做前端代理。原有本机 Origin 校验需与 Tauri 实际来源一起验证。

sidecar 日志保留本机，启动失败显示可操作错误；只关闭自身启动的子进程，不按端口杀进程。应用退出先让后端 lifespan 执行调度与 Runtime 关闭，再超时回收自有进程。开发数据目录和桌面数据目录显式区分；首次迁移由用户选择，禁止静默覆盖数据。

当前未检测到 Cargo/Rust，打包工具与 WebView2 条件需要在 Desktop 阶段核实。创建壳源码、开发运行、生成安装包和实际安装启动是四种验证状态，不能混称“桌面版已完成”。

## 9. 开发顺序与验收

分为三组交付，避免同时改动所有边界：

1. 内容与交互：数据迁移及纯规则 → 单入口导入/回退 → 文件夹与字段编辑 → 批量归类。
2. 检索：tag/hybrid → embedding 可选退化 → Gateway/Policy 注册 → Assistant 引用来源。
3. 工作台与桌面：Today 内部布局 → 导航确定后实现 → sidecar 与薄壳 → 打包和完整验收。

每个阶段先保留 1–3 个关键失败测试，阶段内仅定向测试，最终统一执行全量。关键边界：旧库迁移保留原件/ID、归类同分与零分、AI 失败仍可导入、批量部分失败且 ID 对齐、人工修改同步索引、向量失效及无 embeddings 回退、工具权限只读、sidecar 关闭不影响其他进程。

最终检查 `pytest`、Ruff、Pyright、前端 Vitest/ESLint/Prettier/build；实际浏览器完成文字/拖文件导入、元数据修正、文件夹 CRUD、批量归类、两种 Assistant 检索、来源跳转和两种桌面尺寸。桌面安装包另做真实启动、服务退出和再次启动检查。真实模型调用只使用用户既有配置，不输出密钥。

界面视觉验收须补新截图。本次浏览器捕获工具启动失败（Windows sandbox helper 初始化错误），因此当前设计依据是已有源码与用户方案，未声称已经完成新界面截图审查。

## 10. 后续确认与实施选择

用户后续明确要求持续开发到交付，并指定完整设置与快捷导航。本期据此采用以下实现，构建工具安装仍单独等待授权：

1. **导入先落盘、AI 后台补全**：已实现即时返回、任务持久化、重启恢复和人工修改 revision 保护；失败保留原文并可重试。
2. **PillNav 真实入口**：采用用户明确指定的“助手 / Feed / 设置”；自动化内嵌到设置，增加个人与外观等常规偏好。
3. **正文提取**：支持文本、PDF 与 DOCX，保留原件和明确失败状态；不含扫描件 OCR 与网页全文抓取。

执行记录见 `../plans/2026-10-08-knowledge-settings-desktop.md`。保持改动可审阅，不自动提交已有工作区的大量未提交改动。Tauri 安装包在 Rust/MSVC 安装并实际构建验收前保持未完成状态。
