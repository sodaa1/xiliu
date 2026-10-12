# 0.4 内核与桌面发布验证

## 本次行为

唯一 LangGraph 保持 12 个节点与两层路由。工具语义匹配读取过滤后的 Capability Registry、完整会话记忆和真实候选对象。聊天路径不添加 App Action 清单。

工具调用前以注册表校验工具 ID、读写类型、批量能力、参数 schema 与日期。普通错标或参数错误反馈给同一模型纠正，最多追加两轮；纠正完成前不执行工具。不在权限清单内的工具和未知 schema 字段直接拒绝，不通过重试扩大权限。澄清结果不反复重试。修正轨迹以 semantic_repairs 记录。

保留原文和链接来源校验、候选集 ID、危险操作确认、Checkpoint、数据库回执核验。写入保护兼容旧消息格式的跨轮补充；“全部”可以承接归类请求，但不会替代危险操作授权。

模型连接独立保存，支持 OpenAI、DeepSeek、MiMo 与自定义配置及启用开关。界面默认显示中文执行步骤，原始摘要折叠，不增加翻译调用。Intro 源码迁移后的测试仍使用原有断言，审计旧记录完整归档，新记录未执行项仍为 not_run。

## 验证范围

- 新增修正、上下文、自动任务、写入边界定向回归：38 passed。
- 前端：65 passed，16 个测试文件；生产构建成功。
- Ruff（src、tests、审计扫描器）：通过；Pyright（生产 src）：0 errors。
- DeepSeek 真实模型错标纠正：2 次解析，1 次修正，得到正确 automation 工具与确认回执，未写入数据库。
- 全量默认 Pyright 尚有 103 项错误，来自测试替身、脚本及 tmp 生成的扫描夹具；此处不把生产 src 的通过解释为全仓类型检查通过。

最终全量 Python：742 passed、1 skipped，291.01 秒，无失败。跳过项为 Windows 符号链接权限检查，未计为通过。51 条测评的自动化断言全部通过，但这不意味着 51 条均完成业务操作：原测评状态包括 27 completed、15 clarification_required、1 confirmation_required、4 failed、2 chat、2 context_updated。详细任务与真实节点/回执/数据库证据见 eval-results.json；其中模型及远程 transport 为可重复夹具，不宣称全部真模型成功。

Windows 安装包已重新构建为 dist/Xiliu-0.4.0-x64-setup.exe（36.81 MiB），SHA256：93ebcd7f61b94ea170394da15885e4b04d7c3ed383111f985dd3ff644e0c0412。冻结服务在隔离用户目录、空 PATH 下通过启动鉴权、前端与 Intro、知识检索、隔离模型聊天、Inbox/知识库/自动任务业务链、重启持久化和端口释放检查；未启用的 MCP、公网搜索和专门的 checkpoint 选项不计为本轮验证。

原始日志：logs/graph-v2/release-complete-python.txt、release-complete-installer.txt、release-complete-frozen.json。安装器构建和冻结服务验证不等于已在用户 Windows 环境完成安装验收。包内不含开发密钥或用户数据。

## 修改清单

核心改动位于 src/xiliu/graph、routing、app（contracts、executor、memory、selection）、capabilities、runtime、core、api 与 providers；新增回归与 51 条测评位于 tests。模型设置与执行步骤位于 web/src/features；迁移后的 Intro 位于 docs/web。架构、测评证据与审计说明位于 docs/architecture/graph-v2 和 docs/audit。desktop/README.md 更新安装包入口。具体版本文件列表以本次 Git 提交为准。
