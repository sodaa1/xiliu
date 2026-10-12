# Graph v2 验证报告

日期：2026-10-11。直接修改 `E:/Learning/xiliu` 的真实源码；未创建项目提交。
按用户确认的修订 ZIP 实施 P0–P5，原方案、目标图、51 条测评与 ZIP 逐字节一致，
SHA256 见 [input-integrity.json](input-integrity.json)。

## 架构一致性检查与实施结果

| 检查 | 重构前 | 当前结果 |
| --- | --- | --- |
| GraphState | intent 仅 chat/task；已有 tool_events/evidence；缺少 candidates/result | 结构化 intent、capability_candidates、tool_events、evidence、execution_result 与执行 IDs/results 齐全 |
| Capability Registry | 支持 builtin/Skill/MCP/Agent，App 只有通用入口 | 逐 Action 元数据；同时服务 App/Skill/MCP/SubAgent，沿用原权限与确认策略 |
| Automation Runner | 必须 VerifierEvent 才能报告成功 | 真实 Runtime 集成测试验证后台只读成功、禁止写入失败，报告持久化 |
| CLI | 会话历史和 stable events，原来依赖入口图 | 同一工作流；clear/空 compress 不要求模型配置，压缩保留摘要 |
| Desktop streaming | ChatService App 旁路和双图 | 移除旁路；保持 Progress/Planner/Verifier/Final，Final 在检查点进度之后 |
| Checkpoint | 旧 node/type 白名单 | 全部新节点、序列化待调用、旧快照迁移、固定执行身份、重放回执仍核验权限 |

唯一 StateGraph 恰好注册 12 个节点，完整边集合接受精确测试；实际图见
[runtime_workflow.mmd](runtime_workflow.mmd)，主架构见 [ARCHITECTURE.md](../../ARCHITECTURE.md)。
附带图的 Registry/GraphState 框落实为 discovery/collect；补齐 chat→final、澄清及有界工具轮次。
旧执行模式、Supervisor 转发、重复 Fast 实现、ChatService 前置旁路已移除。

AppDispatcher、Action Registry、原业务服务、SQLite/Markdown、权限/Hook、RAG、Skill、MCP、
SubAgent、Checkpoint 保留。兼容导出 `app/fast.py` 和 `build_entry_workflow` 仅复用唯一实现。

## 实际测试记录

所有 Python 命令使用 `.venv/Scripts/python.exe`；TEMP/TMP 与 pytest basetemp 指向 E:。
首次默认 C: 临时数据库因磁盘已满无法构成有效基线；迁移临时目录后的结果才作为基线。

| 检查 | 实际结果 | 本地日志 |
| --- | --- | --- |
| P0 完整基线 | 573 passed / 1 failed / 1 skipped | `logs/graph-v2/baseline.txt` |
| P1 State/Registry/权限/Evidence | 11 passed；此前 contract RED 3 failed | 阶段 ledger |
| P2 两层路由与 App Intent | 75 passed | 阶段 ledger |
| P3 唯一图、真实写入/拓扑 | 22 passed；此前 RED 4 failed | 阶段 ledger |
| P3 Chat/Checkpoint/Automation 适配 | 29 passed | 阶段 ledger |
| P4 测评、权限、恢复、拓扑 | 60 passed | `logs/graph-v2/p4-verified.txt` |
| P5 强化测评/恢复/适配/RAG | 80 passed | `logs/graph-v2/p5-final-focused.txt` |
| P5 最新 Verifier 回执上下文相关回归 | 58 passed | `logs/graph-v2/p5-verifier-context.txt` |
| P5 最后控制命令、恢复权限与业务回归 | 55 passed | `logs/graph-v2/p5-final-controls.txt` |
| P5 完整回归（最后复跑前） | 667 passed / 1 failed / 1 skipped | `logs/graph-v2/p5-final-full.txt` |
| P5 交付版本完整复跑 | 668 passed / 1 failed / 1 skipped，309.14 秒 | `logs/graph-v2/p5-delivery-full.txt` |
| 现有前端 Vitest | 56 tests passed；14 文件通过，1 文件无法加载 | `logs/graph-v2/p5-web.txt` |
| Ruff `check src tests` | All checks passed | `logs/graph-v2/p5-lint.txt` |
| Pyright `src` | 0 errors / 0 warnings | `logs/graph-v2/p5-pyright-src.txt` |
| Git diff 检查 | 无 whitespace 错误 | `git diff --check` |

独立只读复核实际复现了回执时停止后重复写、部分写入后重新规划重复写、读取冒充移动、
旧读/写回执快照误判、已有数据库冒充创建、批量回执部分对象被覆盖的误判。
均修复并添加实际数据库/文件回归。复核另验证后台权限恢复拒绝写入重放，数据未增加。

## 51 条测评：测试通过与业务完成分开记录

原 `eval_50.jsonl` 实际有 **51 条**，全部保留。逐条真实路径、工具回执摘要、执行状态、
数据库任务数与内容/文件夹状态见 [eval-results.json](eval-results.json)，从 JUnit properties
生成；原 fixture 与 ZIP 完全相同。测试通过表示实际结果符合安全与业务断言，
不表示每个含糊或被禁止的任务都完成了执行。

| 实际结果 | 数量 |
| --- | --- |
| completed，verified=true 的执行 | 27 |
| clarification_required，verified=false | 15 |
| confirmation_required，verified=false | 1 |
| failed，verified=false | 4 |
| Chat 回答 | 2 |
| 控制命令更新上下文 | 2 |

明确未完成的任务 IDs：3、4、7、9、10、11、19、26、27、28、29、32、33、35、38、39、
40、43、48、49。原因包括不明确对象/范围/时间、无上下文的恢复请求、破坏性操作需确认、
工作区越界、没有归档效果、未持久化创建自动任务。没有自动批准确认或伪造业务成功。

模型输出和远程搜索/MCP transport 使用可重复 fixture；LangGraph 节点、Gateway、Policy、
AppDispatcher、RAG、SQLite 和文件操作是真实实现。测评 44 实际编辑文件；46 实际 compileall；
47 实际运行 pytest 并读回测试报告；50 核对两个不同文档 ID；51 实际执行建库脚本并检查
SQLite 表及 integrity_check。MCP 另验证 schema、allowlist 与禁止联网时零远程调用；
SubAgent 验证 RAG 子回执和 hit/evidence IDs 进入父 State。
没有进行付费真实模型/公网质量测评，这些结果验证执行架构与可观察业务效果。

## 初次重构验证未通过项（历史记录）

后续 Intro 迁移兼容与审计身份更新已修复前两项。当前发布结果见 [release-0.4.md](release-0.4.md)；以下保留初次失败证据。

1. `tests/unit/test_app_surface_guard.py::test_current_repository_surface_and_registry_contracts_are_fully_classified`：
   26 个 stale UI classification。P0 已复现；重构前工作区已移除 Intro 页面，coverage 清单
   仍引用这些控件。本次仅迁移被改名测试的声明引用，保留历史执行记录和这些失败。
2. `web/src/features/intro/LandingPage.test.tsx`：Vitest 无法解析 `./LandingPage`；该源码在
   重构前已被删除，测试仍引用。未改写测试期望、恢复用户删除的文件或隐藏测试文件。
3. `test_directory_index_symlink_cannot_escape_static_root`：Windows 缺少创建符号链接的权限，原有测试跳过；不计为通过。

这些未通过项与重构前已有的 Intro 改动有关。README、web 构建与 docs/web 原有改动保持原样。
本次文件清单见 [change-list.md](change-list.md)。

## 复现

```powershell
$env:TEMP = 'E:\Learning\xiliu\tmp\graph-v2'
$env:TMP = $env:TEMP
.venv/Scripts/python.exe -m pytest -q --disable-warnings --basetemp=tmp/graph-v2/verify `
  --junitxml=logs/graph-v2/verify.xml -o junit_family=legacy
.venv/Scripts/python.exe -m ruff check src tests
.venv/Scripts/python.exe -m pyright src
cd web
npm test -- --run
```
