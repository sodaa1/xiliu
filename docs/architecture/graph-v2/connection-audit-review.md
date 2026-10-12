# 模型连接界面审计变更提案

用户已批准本提案，并已更新 coverage-manifest.json。权限、确认和 App settings.model.update 的 restricted 状态保持原约束。

新增源码扫描有 14 个 SettingsPage 词法记录：

- 保存单个连接的 mutation：restricted，绑定 settings.model.update，仅用户密码表单可保存。
- 切换厂商事件：ui_only，恢复厂商字段、清空未保存密钥草稿。
- 模型名输入事件：ui_only，仅本地草稿。
- 显示名输入事件：ui_only，仅本地草稿。
- api.xiaomimimo：ui_only，扫描器识别到提示文字中的地址，实际不是客户端 API 调用。
- 设为默认 mutation：restricted，使用已存连接，不返回密钥。
- 默认选择 api.saveSettings：restricted，用户操作；不允许 Agent 写配置。
- 默认选择 mutationFn 词法记录：restricted，同一用户操作。
- 编辑连接按钮及事件：ui_only，共 2 项，只展开表单。
- 设为默认按钮及事件：restricted，共 2 项，未配置密钥的连接禁用。
- 添加自定义连接按钮及事件：ui_only，共 2 项，仅打开空表单。

旧保存表单 ui_mutation:f67c4bde95fe63bb112f:1 的函数表达式已被新保存表单替换，
需由新记录 ui_mutation:4e5953f491b91f1df538:1 继承同一 restricted 分类和审计依据。
格式化后该记录的实际扫描 ID 为 ui_mutation:23934144a3544508d4ee:1。
其余旧 Intro 的失效记录不在本提案修改范围。

测试依据：tests/unit/test_model_profiles.py、ModelProfiles.test.tsx、settings 写入权限拒绝测试。
这些测试不等于所有界面操作都做过真实 UI/Agent 等价验收；verification 仍应标为 not_run。
