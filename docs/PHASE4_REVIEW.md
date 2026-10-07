# Phase 4 检查

预览：http://127.0.0.1:8765/assistant 。本地服务已启动；下次可双击根目录 start-xiliu.bat。

## 已实现

- Assistant 浅色三列布局、Markdown、多会话持久化、新建/切换/删除、当前会话模型选择。
- Settings 的 Provider / Model / API Key / Base URL，保存到 .env；空 key 保留已有密钥；GET 不返回密钥。
- /clear：保留页面历史，后续模型上下文排除旧消息/旧摘要/旧笔记的自动注入。
- /compress：把现有有效历史与前摘要合并压缩，保存 summary 和 through_seq；重复调用无新消息不产生额外请求。
- /skill 与 /mcp：名称補全；只有名称时查看元信息，附加指令时交给原 Runtime/Gateway。
- 完整改名 xiliu、XILIU_*、.xiliu；原始附件与仓库来源链接保留用于追溯。原 .env 的密钥值未变。

## 建议检查

1. 打开 Assistant，新建两段对话，切换和刷新确认历史仍在。
2. 检查页面布局、消息样式、命令菜单与 Settings；API Key 输入框应为空但提示已配置。
3. 在会话模型选择中切换 DeepSeek 模型，再切到另一会话确认互不覆盖。
4. 输入 /skill xiliu-debugging 查看说明，或 /mcp aihot 查看元信息；这些操作不调用付费模型。
5. 在已有上下文的会话发送 /clear，页面保留旧内容并出现分隔。真实聊天或 /compress 会使用你已提供的模型配置。

## 验证证据与边界

- 44 个后端测试、12 个前端测试通过；包括并发消息 seq、同会话忙保护、首次双击发送、卸载取消、跨会话 PATCH、clear、压缩失败/重复、真实 Runtime 路由、UTF-8 增量读取。
- Ruff / Pyright / ESLint / Prettier 通过；Vite build 成功；npm audit 零项。
- Edge headless 的桌面和 390px 窄屏检查通过；无页面异常或控制台错误。截图和浏览器报告在本地忽略目录 .preview/，不提交运行数据。
- 真实 provider 请求与 MCP 工具执行尚未进行付费/外部联调，按设计留在 Phase 7。
- Today、Feed、Inbox、Knowledge 尚未开放，显示后续阶段提示；未启动 Phase 5。
- 早期测试保留一段 New Chat 示例。按内容批量清理曾被自动审批拒绝，后续仅清理明确记录的本轮创建 ID。

当前不需要补充文件。若真实接口调用报鉴权、额度或模型权限错误，再依据实际错误处理。
