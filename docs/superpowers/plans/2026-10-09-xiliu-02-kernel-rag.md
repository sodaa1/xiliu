# Xiliu 0.2 内核与 RAG 实施记录

依据：用户提供的《Xiliu 三阶段内核与 RAG 重构实施方案》，按 P0/P1/P2 顺序在当前工作区实施。现有大量 staged/unstaged 修改是基线，不能覆盖或混入本次阶段提交；测试继续按项目约定保留本地。

## P0
1. `tests/unit/test_shared_evidence.py` 复现本地 document_id 命中但 research_notes 为空的验证失败。
2. `execution/evidence.py` 实现稳定事件 ID、幂等 reducer 和严格工具来源映射；`agents/react.py` 写入调用 ID。
3. `graph/state.py/nodes.py/memory.py/verification.py` 接通共享证据，保留旧字段和派生 research_notes。
4. `graph/routing.py/modes/` 与 `workflow.py` 实现 Fast/Standard/Deep，复用单节点 ReAct，不重写工具循环；Fast 不需 Todo/SubAgent/LLM Verifier。
5. `capabilities/agent_registry.py` 与 `agents/runtime.py` 实现受约束的 Agent 发现、调用基座。
6. 运行新增回归、全量后端、Ruff 和 API/CLI 兼容检查。

## P1
1. `rag/chunking.py/service.py/ingestion.py` 在既有 AppStore 建立幂等 chunk 和持久索引作业。
2. `ContentService` 写入时原子入队；应用后台 worker 执行独立索引状态机，修订号保护、失败退避、删除清理。
3. 复用 `RetrievalService` 的检索/向量实现，工具和 API 共用 RAGService，搜索不执行正文索引。
4. 测试创建/编辑/删除、重复任务、旧 revision、降级与迁移兼容。

## P2
1. 增加本地多轮 rag Agent、knowledge_get、显式父子事件映射、模式和网络约束。
2. 测试多轮查询、引用真实性、预算、零命中、非法 manifest、父证据幂等。
3. 更新实际实现文档和 0.2 版本；输出验证结果、状态图和风险。

## 记录
- 初始后端测试：执行 `.venv/Scripts/python.exe -m pytest -q`，退出成功，无失败，1 项跳过。
- 已确认根因：直接工具结果未映射 evidence，research 验证强制 SearchAgent + URL。
- 决定：在当前工作区保留用户未提交基线实施；独立提交须只纳入本次增量，不能提交用户已 staged 的桌面/UI 变更。

## 实施结果
- P0：三模式条件路由、稳定工具事件、共享 evidence、Memory/Verifier 映射、Agent 目录与 Fast checkpoint 恢复已实现；本地命中和 Planner 直调 MCP 回归均先失败后通过。
- P1：共享 RAGService、后台持久作业、稳定片段、仅变化片段向量缓存、revision/正文指纹保护、过滤前置和删除清理已实现。
- P2：manifest 模式/工具/路径限制、本地多轮 RAG、引用 ID 校验、显式父子事件映射、新 Code Agent 兼容与有界退出已实现。
- 最终后端：111 passed, 1 skipped；跳过原因 Windows 符号链接权限。前端 30 passed；Ruff/Pyright/frontend lint/build/CLI 均通过。
- 离线真实状态流：`scripts/verify_kernel_rag.py` → `logs/development/xiliu-02-proof.json`。
- 独立只读审查发现的否定联网、Code Agent 来源、过滤顺序、启动线程泄漏已修复并验证。
- 权限决定：自动审批拒绝降低全局 capability_search 权限，最终保留原权限，新增独立只读 agent_catalog。
- 集成决定：保留用户原 staged/unstaged/index，没有自动生成阶段提交；混入原 UI/Desktop 修改的风险已避免。
- 交付边界：真实网络/模型和 Tauri 安装未验收；同步调用取消和 ReAct 批次中途崩溃的动作级 exactly-once 限制列入 `docs/XILIU_02_KERNEL_RAG.md`。
