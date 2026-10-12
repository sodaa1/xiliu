# 混合多步任务恢复（v0.4.1）

修复外部来源被本地保存目标遮蔽的问题；外部调研与知识库保存组合进入 Planner。
Planner 在核验失败后保留工具消息、成功回执和对象 ID，自动继续剩余步骤。
TODO 从 pending 直接 completed 的拒绝仍保留在日志中，模型可以合法修正；权限确认与不可重试错误仍停止。
明确要求 Markdown 文件时，必须存在真实 file_write/file_edit 回执及内容读回验证。

本次原始 GitHub Python 项目调研任务使用现有 DeepSeek 和真实网络检索，单次用户请求完成，内部 2 次执行尝试。
生成 Markdown、保存卡片、确保“优质项目”目录并归类均通过；仅 1 张卡片、1 个目录，文件与卡片正文一致。
检索证据与实际节点记录位于本机 logs/graph-v2/live-mixed-recovery.json。
该测试验证流程、持久化和来源证据，不证明报告的全球 GitHub 排名覆盖完整。

最新针对性回归：63 passed，含 50 条多模式多步用例（模型与搜索使用夹具，App/SQLite/文件实际执行）。
静态检查：Ruff 通过，Pyright 0 errors。
此前全量回归：741 passed、53 failed、1 skipped；主要为旧单步 App 路径与模型夹具兼容性，未声称全量通过。
完整失败记录保留在 logs/graph-v2/app-loop-full.txt。本次未修改旧测试期望来隐藏失败。
