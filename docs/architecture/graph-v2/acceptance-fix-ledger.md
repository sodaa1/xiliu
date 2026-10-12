# 网页验收修复记录

用户授权沿用现有密钥、不新建密钥；语义匹配仅在读取工具规则入口添加，保留 Chat 和现有 12 节点图。
新增需求：MiMo V2.6 为第三厂商；多个厂商/模型连接并列配置、会话切换、自定义接口。

## 实施顺序

1. 配置隔离及安全本机密钥输入弹窗。
2. Direct 规则读取的完整语义匹配；Fast/Planner 读取规则使用当前模型匹配。
3. Inbox 原文/目的地/后台生命周期验证；Planner 可纠正错误反馈，保留权限和确认。
4. 中文执行步骤、错误和支持厂商的推理摘要。
5. 多表达回归、真实配置模型测评、网页验收；用户确认后才打包。

## 已运行

- 模型配置后端 RED：3 failed；GREEN：13 passed。
- 设置页密钥草稿串用 RED：1 failed；GREEN：4 passed。
- 密钥表单/隔离测试使用虚构密钥；之后用户授权沿用实际配置进行 DeepSeek API 验收，未新建密钥。

## 界面参考锁定

使用 refero-design。在线参考查询因 NO_SUBSCRIPTION 不可用，采用其 craft-details 表单/焦点规则。
主参考为现有 Xiliu ModelForm、ModelPicker、Modal 和 settings.css：保留白底、淡紫色选中态、
现有字号、间距、GlideSelect 与弹窗关闭/焦点行为。新增连接列表展示厂商、模型、配置状态；
单项展开编辑，密钥 type=password、不回显、不阻止粘贴、不写 localStorage。
不重做整体 UI，不添加装饰素材。

MiMo 官方地址/ID： https://mimo.mi.com/docs/zh-CN/quick-start/summary/first-api-call。
普通接口 https://api.xiaomimimo.com/v1；Token Plan 地址以用户账户配置为准。

## 后续执行与审查

- 完整语义规则匹配 RED：9 failed、3 passed；GREEN：12 passed。
- 原文虚构写入在 RED 被复现，修复后未执行该写入。
- Inbox/TODO/流终结 RED：3 failed；与测评集联合 GREEN：88 passed。
- MiMo 与多模型独立配置回归：16 passed；前端相关 6 passed。
- 独立审查发现默认连接旋转密钥未生效、旧裸模型名串用默认凭据；RED：2 failed，修复 GREEN：18 passed。
- 自定义接口回归改用实际 HTTP 传输捕获，以验证绑定参数是否发送；RED 拒绝厂商专属 thinking 参数，GREEN 传输/适配：6 passed。
- 真实 Flash 8 表达、Pro 3 表达、Flash 数据库任务最终通过；详见 web-acceptance-results.md。
- 用户选择仅中文执行步骤、原文折叠；二次摘要功能没有加入。
- 用户明确批准模型连接审计提案。登记 14 条，并补齐实际具名 UI 测试，不更改权限及测试门槛。
- 全量 Python：693/1/1；全量前端 62 通过、1 个旧 Intro 文件加载失败。保留原失败项并报告。
- 独立浏览器实查模型列表及空密码表单；后端预览已重启。尚待 MiMo 密码保存及真实切换测试；未整合安装包。
