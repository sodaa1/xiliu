# App 多步执行与全模式测评

## 路由和执行

原 capability_router 判定为 app_executor 的请求改为 planner，附带 tool_scope=app。
复用 planner → capability_discovery → tool_execute → state_collect 循环与 execution_verifier。
仅提供 App Action schema 和规则，模型每轮结合请求、完整记忆与回执进行语义匹配。
执行端只装配 app 工具，catalog/describe/execute 同时受 allowed_actions 约束，排除 capabilities.*。
Skill、MCP、子 Agent、工作区和联网工具不能在 App 专用路径执行。

需要联网的复杂混合任务继续使用完整 planner 工具范围，每轮仍提供 App Action 规则与语义匹配提示。
聊天不发工具清单。App 请求保存历史回答时，模型从会话记忆提取正文，使用真实工具 ID 和对象回执处理依赖。

验证收到原始请求、验收条件和实际回执；App 专用路径漏做步骤时保留原工具消息和成功回执继续执行，避免重新创建对象。
确认回执立即停止后续调用。澄清保留 pending domain，后台写入仍受 PolicyEngine 拒绝。
App 循环和验证调用计入执行模型调用统计，不再错误显示零次。
旧 app_executor 节点暂保留用于已有 checkpoint 兼容；新请求不再从该单动作入口执行。

## 新测评

数据源：tests/fixtures/graph-v2/multistep_50.jsonl；运行器：tests/integration/test_multistep_eval.py。

|类别|数量|检查|
|---|---:|---|
|App 多步|12|历史回答、原文、真实卡片 ID、文件夹复用与归属|
|简单联网多步|8|两个独立搜索步骤、来源回执、fast_react 路径|
|复杂联网|10|三步检索、来源证据、planner 验证|
|App 与联网混合|10|检索→保存→建目录→归类，SQLite 状态|
|文件任务|5|实际写入与回读；研究报告额外检索本地依据|
|聊天边界|5|多部分解释、零工具调用|

因此 50 条包含 45 条实际多步工具任务和 5 条聊天边界；没有把聊天伪装成工具多步任务。
模型与远程搜索响应使用可重复夹具；图、网关、权限、文件和数据库为真实实现。
每条 JUnit 记录实际节点、工具结果、App 回执与相关数据库状态；scripts/report_multistep_eval.py 导出 multistep-results.json。
另有 App 专用回归：验证后补齐不重复、禁止其他工具、人工确认停下、后台权限与澄清状态。

## 真实模型

沿用已有 DeepSeek Flash 配置，隔离数据库测试三种中文表达，3/3 完成。
第一条创建文件夹和卡片，第二条复用目录，第三条跨越闲聊引用先前解释。
均核对原文完全一致、只有一个目录和一个卡片、归属正确。原始证据 logs/graph-v2/live-app-loop.json。
这三条未使用联网搜索，不宣称 50 条真模型或公网端到端全通过。

## 完整回归状态

本次全量快照：741 passed、53 failed、1 skipped（logs/graph-v2/app-loop-full.txt）。
已确认失败包含旧 app_executor 路由断言、零模型调用约定、只实现 with_structured_output 的旧模型替身以及单次规则读取断言。
涉及旧记忆、CLI/Automation、停止恢复和无密钥入口的失败不能仅以新测评通过来替代，仍需逐项迁移复核。
未删除或跳过这些失败测试，也未把失败改为预期通过。本次暂不重建安装包或称为可发布版本。
