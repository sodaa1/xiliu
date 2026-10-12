# Xiliu Agent Graph v2 重构方案（Codex执行版）

## 目标

将 Xiliu Agent 执行架构统一为：

User Query
→ Intent Router
→ Capability Router
→ Execution
→ Verification
→ Final

删除：
- ChatService 前置 run_app_fast 旁路
- mode_router
- standard/deep/fast 模式体系
- supervisor_node（其本质调用 planner_node）

保留：
- Action Registry
- Execution Gateway
- Capability Registry
- MCP
- Skill
- RAG
- AppDispatcher
- GraphState
- Checkpoint

---

# 一、Graph节点设计

workflow.py 必须形成以下节点：

1. intent_router
2. capability_router
3. chat_responder
4. app_executor
5. fast_react
6. planner
7. capability_discovery
8. tool_execute
9. state_collect
10. execution_verifier
11. clarification
12. final

所有节点必须真实注册到 StateGraph。

---

# 二、Intent Router

Intent Router 是一个节点，但内部包含两阶段识别：

## 第一阶段：Intent Recognition

顺序：

1. Command Adapter
2. Rule Matcher
3. Embedding Matcher
4. LLM Classifier

输出 Structured Intent。

输出字段：

```json
{
"intent":"",
"domain":"",
"action":"",
"complexity":"",
"source":"",
"preferred_capability":"",
"confidence":0
}
```

---

## Command处理

控制命令：

/clear
/compress

直接进入 CommandControl，不进入Agent循环。

任务命令：

/skill
/mcp

进入 Intent Router，并作为能力偏好约束。

---

# 三、Capability Router

根据 Structured Intent 选择：

## Chat

进入 chat_responder


## Direct Action

已有明确Action：

AppExecutor
→ Gateway
→ Action


## Fast ReAct

适合：
- 少量工具调用
- 无需任务拆解
- 3-5步以内

必须：

Capability Registry
→ 候选工具检索
→ ReAct循环


## Planner

适合：
- 多步骤目标
- 需要中间规划

流程：

Planner
→ Capability Registry
→ LLM选择Skill/MCP/SubAgent
→ Tool Execute

取消Standard/Deep。

---

# 四、执行验证

所有工具执行必须写入：

GraphState:

- tool_events
- evidence
- results
- execution_ids

Verifier根据路径验证：

Direct Action:
检查真实回执

Fast:
检查目标完成情况

Planner:
检查计划目标完成情况

失败：
允许重新规划或请求澄清。

---

# 五、代码迁移

删除：

- run_app_fast 前置调用
- graph/modes/*
- supervisor_node
- mode_route

新增：

graph/nodes/
- intent_router.py
- capability_router.py
- command_adapter.py
- fast_react.py

routing/
- rules.py
- embeddings.py
- classifier.py
