# Phase 4 检查

预览：http://127.0.0.1:8765/assistant 。本地服务已启动；下次可双击根目录 start-xiliu.bat。

## 已实现

- Assistant 浅色三列布局、Markdown、多会话持久化、新建/切换/删除、当前会话模型选择。
- Settings 的 Provider / Model / API Key / Base URL，保存到 .env；空 key 保留已有密钥；GET 不返回密钥。
- /clear：清除当前对话的消息和上下文摘要，保留对话及模型选择，仅显示清除确认。
- 主导航可折叠为图标栏，折叠选择会保留。
- 思考区默认折叠，可展开处理步骤和模型返回的思考内容；显示分、秒耗时，并随回答保存。
- 切换页面不取消正在运行的对话，返回 Assistant 恢复原对话和处理状态。
- 对话提示包含本轮配置的模型 ID；DeepSeek 列表按用户要求仅保留 V4 Flash / Pro，旧 Flash 设置兼容迁移。
- 保留路由与工作流，DeepSeek 分类请求关闭思考，普通回答使用 low；OpenAI 支持的模型使用 low。
- /compress：把现有有效历史与前摘要合并压缩，保存 summary 和 through_seq；重复调用无新消息不产生额外请求。
- /skill 与 /mcp：名称補全；只有名称时查看元信息，附加指令时交给原 Runtime/Gateway。
- 完整改名 xiliu、XILIU_*、.xiliu；原始附件与仓库来源链接保留用于追溯。原 .env 的密钥值未变。

## 建议检查

1. 打开 Assistant，新建两段对话，切换和刷新确认历史仍在。
2. 检查页面布局、消息样式、命令菜单与 Settings；API Key 输入框应为空但提示已配置。
3. 在会话模型选择中切换 DeepSeek 模型，再切到另一会话确认互不覆盖。
4. 输入 /skill xiliu-debugging 查看说明，或 /mcp aihot 查看元信息；这些操作不调用付费模型。
5. 在已有上下文的会话发送 /clear，旧消息消失，仅显示清除确认。真实聊天或 /compress 会使用已配置的模型。
6. 发送消息后切换 Settings，再返回 Assistant，确认处理继续；完成后展开思考区，再刷新确认内容及耗时仍在。

## 验证证据与边界

- 本轮集中验证 49 个后端测试、13 个前端测试；包括跨页继续对话、思考与耗时持久化、供应商 SSE 思考字段、真实 FastAPI/Runtime 流式上下文、CLI 路由兼容，以及现有回归。
- Ruff / Pyright / ESLint / Prettier 通过；Vite build 成功。此前 npm audit 零项，本轮未重复依赖审计。
- Edge headless 的桌面和 390px 窄屏检查通过；无页面异常或控制台错误。截图和浏览器报告在本地忽略目录 .preview/，不提交运行数据。
- 本轮供应商数据使用离线 SSE 模拟；未进行付费 provider/MCP 外部联调，未测量真实供应商提速幅度。
- Today、Feed、Inbox、Knowledge 尚未开放，显示后续阶段提示；未启动 Phase 5。
- 早期测试保留一段 New Chat 示例。按内容批量清理曾被自动审批拒绝，后续仅清理明确记录的本轮创建 ID。

当前不需要补充文件。若真实接口调用报鉴权、额度或模型权限错误，再依据实际错误处理。
