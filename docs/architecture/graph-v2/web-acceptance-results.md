# 网页反馈修复验收

## 2026-10-12 语义拦截清点与只读修复

- 已修复只读 scope=all 被当作批量写入的问题；只读操作使用注册表领域，自报 confidence 不再作为只读执行门槛。
- 新增持久化 semantic_decision 和 reason_code，仅含动作、类型、范围及置信度，不记录密钥或参数正文。
- 真实 DeepSeek Flash 4 种待办查询全部执行 tasks.list 并核验成功：目前待办有哪些、列出待办事项、全部待办给我看看、待办清单有什么。日志 read-scope-live.json。
- 定向回归 29 通过、2 失败。两个失败是预先添加的待实施行为：相对日期/归纳标题，以及非固定词语的全部归类；未修改测试期望。
- 更广的语义拦截减少方案被自动审批拒绝，理由为同时删除对象与参数来源校验可能扩大模型驱动写入的范围。原整批补丁未应用，当前只应用不放宽写入保护的安全子集。
- 剩余方案、关键保护及受影响文件详见 semantic-boundary-review.md，等待用户明确批准后继续。

## 2026-10-12 多轮记忆修复

- Direct Action 使用原 MemoryManager.assemble 提供的规则、工作记忆和历史层；语义匹配读完整有效会话与压缩摘要，不限于上一条。
- ConversationService 从本会话已验证 App 回执构建 object_memory（对象 ID、名称、操作和对应用户请求）。对象回执跨压缩保留，/clear 后不可引用；执行前仍通过真实工具读取最新状态。
- 历史用户数据和回执可作为参数来源；历史助手文字、摘要、附件不赋予新的执行权限。现有联网/AI 授权、危险操作确认和策略检查保留。
- 泛化关键词无法解析跨轮指代时交给已有意图分类器；显式说明 preferred_capability 仅用于用户要求的 Skill/MCP，避免普通追问误入 Planner。
- 保留模型给出的具体澄清问题；用户回答“全部”后可延续未完成的 Inbox 归类，并调用已有 classify_all。
- 回归：115 通过（包含原始 51 项测评与安全恢复）；最后定向回归 39 通过。Ruff 通过，Pyright src 0 errors。
- 真实 DeepSeek Flash 两组共 12 轮对话：9 次写操作全部通过节点、回执及数据库核验；2 次闲聊走 Chat；1 次范围澄清后，“全部”成功执行。覆盖隔两轮引用、压缩后指代、多个对象中选择较早对象；其余对象保持 Inbox。
- 最初真实运行的路由失败，以及第二次范围澄清丢失，分别保存在 live-context-first.json、live-context-second.json；修复后结果为 logs/graph-v2/live-context.json 和 live-context-older-object.json。未修改测试期望掩盖失败。
- 文件：src/xiliu/app/memory.py、executor.py；api/services/conversations.py；graph/nodes/execution.py；routing/__init__.py、classifier.py；tests/integration/test_app_conversation_memory.py。另补正模型启停字段的类型注解（model_settings.py）。
- 测试仅使用隔离目录和合成资料，未归类用户真实 Inbox；安装包未整合。

## 2026-10-12 模型启停补充

- 每个连接可启停；停用从对话选择列表隐藏，在设置页“已停用”折叠区恢复。密钥、地址及名称保留。
- 默认模型需先更换默认后再停用；服务端拒绝绕过界面停用默认模型。旧对话引用停用连接时明确提示切换，不静默借用其他模型。
- 根据 OpenAI 官方模型清单补充 gpt-6.1-sol、gpt-6-astra、gpt-6-luna，保留原 5.6 连接。
- 本次模型配置测试 9 通过；设置/助手前端测试 19 通过；Ruff 通过。
- 配置与审计合跑 28 通过、1 失败（旧 Intro 失效分类）；TypeScript 仍仅报旧 LandingPage 引用缺失。
- 登记六个 restricted 界面记录，替换一个新增停用条件的默认按钮记录；逐项等价验收仍为 not_run，旧 Intro 记录保留。
- 本次没有调用模型 API，也没有修改用户实际密钥或主动停用任何连接。

当前源码已修改，开发网页 http://127.0.0.1:5173/assistant；安装包未整合，等待用户网页确认。
本记录补充原 P0–P5 报告，不替换之前的失败记录。

## 完成内容

- 各厂商/模型独立密钥、地址和显示名称。预设 OpenAI 3 项、DeepSeek Flash/Pro、MiMo V2.6 Pro/Flash。
- 会话选择连接 ID，不覆盖其他配置；保留旧裸模型名。默认连接编辑后立即更新实际默认运行配置。
- 增加其他 OpenAI 兼容接口；密码输入留空保留原密钥，切换连接清空草稿，服务响应不含密钥。
- Direct Action 读取完整工具规则后做语义匹配；Fast/Planner 只在原调用中加入当前路径规则。Chat 不发清单。
- 不允许模型生成待保存原文或对象标识，否定、解释和假设请求不授权写入。
- Inbox 原文/目的地与后台元数据生命周期验证；TODO 拒绝反馈可按合法状态修正；网页完成流排空后终结 Trace。
- 默认中文执行步骤，原始模型摘要折叠；按用户选择不增加二次总结调用。
- 按用户批准登记 14 项模型界面审计记录，保持 restricted 写权限和 not_run 的逐项验收状态。

## 实际测试

| 验证 | 实际结果 | 日志 |
|---|---|---|
| Python 最终全量 | 693 passed, 1 failed, 1 skipped | logs/graph-v2/final-reviewed.txt |
| 后续模型/语义/流修复定向回归 | 36 passed | logs/graph-v2/final-model-scope.txt |
| 传输级自定义接口兼容与推理适配 | 6 passed | logs/graph-v2/custom-transport-green.txt |
| 全部集成测试 | 388 passed, 1 skipped | logs/graph-v2/integration-green-final.txt |
| 原始测评文件全部 51 项 | 自动化测评通过，包含实际节点、工具、持久化和权限检查 | 上述集成运行及 acceptance-batch.txt |
| 前端全量 | 62 passed；1 个 Intro 测试文件无法加载 | logs/graph-v2/web-final.txt |
| 后续设置/助手定向回归 | 18 passed | logs/graph-v2/final-ui-scope.txt |
| 新界面审计证据补齐后 | 19 passed, 1 failed；只剩旧 Intro 失效分类 | logs/graph-v2/approved-audit-evidence.txt |
| Ruff | 通过 | 最终命令输出 |
| Pyright src | 0 errors, 0 warnings | logs/graph-v2/acceptance-pyright-final.txt |
| 前端 TypeScript | 旧 LandingPage.test.tsx 引用被删除的 LandingPage，失败 | logs/graph-v2/web-typecheck-final.txt |

原始 51 项使用受控模型安排调用，真实工具、服务和数据库执行；这不等于 51 项均完成真实模型语义测试。

真实 API 额外执行：

- DeepSeek Flash：8 种“保存同一原文到 Inbox”的中文表达，8/8 核验通过，均只有一次规则匹配和一个保存回执。
- DeepSeek Pro：其中 3 种表达，3/3 核验通过。
- DeepSeek Flash：“建立研究数据库”，最终生成 research.db，5 张实际表，全部 TODO 完成、实际命令及数据库核验通过。
  最初失败原因依次为工具预算/扩展任务范围、企图直接写 Runtime 管理的 TODO；规则清单补齐这些已有约束后复测通过。
- 日志：live-deepseek-deepseek-v4-flash.json、live-deepseek-deepseek-v4-pro.json、live-database.json，位于 logs/graph-v2。
- 测试数据位于隔离的 tmp/graph-v2；没有用验收任务修改用户实际内容库。

浏览器实查：7 个预设连接同时出现；MiMo 密码框初始为空；使用独立浏览器页面，未读取用户正在输入的密钥。
截图 logs/graph-v2/model-picker.png、model-connections.png。

## 未通过与尚未运行

1. 原先 Intro 页面删除，审计清单仍有该页面的旧记录；保留失败，没有修改审计测试或恢复用户已删除源码。
2. LandingPage.test.tsx 仍引用已经删除的 LandingPage；前端测试文件加载和 tsc 被这个原有问题阻塞。
3. MiMo 当前尚未保存密钥，真实 MiMo↔DeepSeek 切换和答复测试未运行；OpenAI 也未检测到独立配置密钥。
   隔离测试已证明模拟三厂商切换不串用密钥，但不代替真实 API 验收。密钥应在本机密码框保存，勿发送到聊天。
4. 51 项真实模型全量执行尚未运行；已完成上述 12 项真实模型测试。

## 本轮源码与测试修改清单

- src/xiliu/api/model_catalog.py、schemas.py；src/xiliu/config.py。
- src/xiliu/api/services/model_settings.py、conversations.py、chat.py、inbox.py。
- src/xiliu/app/dispatch.py、executor.py、actions.py。
- src/xiliu/providers/openai_compatible.py。
- src/xiliu/graph/nodes/common.py、execution.py；12 节点与条件边未增加。
- web/src/features/settings/SettingsPage.tsx、settings.css。
- web/src/features/assistant/AssistantPage.tsx、ModelPicker.tsx、ThinkingPanel.tsx。
- web/src/lib/api.ts、types.ts。
- tests/unit/test_model_profiles.py、test_model_reasoning_adapters.py。
- tests/integration/test_semantic_rule_matching.py、test_web_acceptance_repairs.py。
- web/src/features/settings/ModelProfiles.test.tsx；AssistantPage.test.tsx 增加原始摘要默认折叠并手动展开的检查，符合用户新要求。
- docs/ARCHITECTURE.md；docs/audit/coverage-manifest.json；graph-v2 网页问题、修复记录、审计提案和本报告。

原 P0–P5 文件修改清单见 validation.md；原先用户 README/Intro 改动和 ort 未清理。
未修改测试目标来冒充原文保存、执行权限或实际数据库成功。安装包未打包，Git 未提交。

## 2026-10-12 已批准的语义边界修复

已按 semantic-boundary-review.md 实施，先前相对时间与批量范围两个失败已解决。118 项集成/安全/测评回归通过；对象候选校验新增两项集成测试，定向20项通过。真 DeepSeek Flash 3项通过（查询、带时区相对日期写入、空集合归类），结果在 logs/graph-v2/semantic-boundary-live.json。旧 Intro 失败未在本次修复或重测。

新增 selection.py 负责基于真实候选与完整有效记忆消歧。修改 executor.py、intent.py、actions.py、dispatch.py，新增/扩展 test_app_object_selection.py、test_app_semantic_boundaries.py。测试期望未放宽，安装包未整合。

## 2026-10-12 新闻查询误入 App 分支修复

复现：非空 action（web.search/search/自然语言动作）一律被送入 app_executor；低于0.55的自报置信度直接澄清。新增4条测试修复前失败，修复后通过。现仅注册的 App action 和受限 App 匹配标记进入 App 分支；网络查询交给 fast_react，按模型 network 域提供 current_time/web_search，并保留 local_only 与执行权限。App 匹配返回 None 不再生成泛化信息不足，转入有工具的模型继续处理。12节点和条件边不变。

验证：路由/51测评/安全恢复/工作流85项通过；最后兜底变更后路由/工作流/语义边界38项通过；Ruff/Pyright通过。DeepSeek真模型2种新闻问法均成功调用 current_time 与 web_search，无 App 回执、无写入。结果 logs/graph-v2/news-routing-live.json。此结果验证检索链路与回执，未单独审核所有新闻事实。

文件：routing/__init__.py、routing/classifier.py、graph/nodes/execution.py、tests/unit/test_graph_v2_routing.py。本次未修改安装包。

## 2026-10-12 自动任务一句话创建与跨轮补充

历史实际元数据：完整请求的模型 action_id=null（不是权限拒绝）；补充句的 domain=automations、kind=workflow，被代码专用链接归档分支处理。另复现补充句本地规则先固定到 tasks，未让模型结合待补充状态进行路由。记忆此前只有历史和已执行对象，没有明确未完成请求状态。

新增 pending_requests 从会话执行结果构建，包含原请求、后续补充、领域及澄清问题；压缩后仍保留，/clear 后清除；查询不清除，已验证写入/确认完成后清除。存在待补充状态时，先让模型判断续接还是新请求，不能由当前句关键词抢先覆盖。App 匹配提示明确自动任务是 automations.create 一次提供名称、时间、时区和未来执行提示；workflow 仅为真实链接归档。自动任务提示允许忠实概括并由原有确认界面审阅，导入原文与链接来源核验保留。

新回归修复前1项通过3项失败；修复后相关124项全部通过，包含51条测评、语义匹配、多轮记忆、安全恢复和路由。Ruff/Pyright通过。真 DeepSeek 一句话完整创建正确生成确认；另3轮（名称请求、插入闲聊、压缩后补充）正确延续 AI晨报，09:00 Asia/Shanghai，提示涵盖昨日新建/已完成/未完成。隔离库模拟界面确认后真实落库一个自动任务，没有替用户创建正式自动任务。结果：logs/graph-v2/automation-one-sentence-live.json、automation-followup-live.json。

修改：api/services/conversations.py、app/memory.py、app/executor.py、routing/__init__.py、routing/classifier.py；新增 tests/integration/test_automation_semantic_context.py。本次未修改安装包。
