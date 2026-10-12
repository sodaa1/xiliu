# Xiliu Graph v2 — P0–P5 execution ledger

Spec: `Xiliu-Agent-Graph-v2-Codex.md` (the user confirmed the revised ZIP on 2026-10-11).
The supplied evaluation fixture has 51 records; all are retained verbatim.

## P0 — consistency audit and baseline

- GraphState currently has ID-deduplicated tool_events/evidence but only a chat/task intent,
  no capability_candidates or execution_result, and obsolete mode/supervisor fields.
- CapabilityManager already supports builtin/skill/mcp/agent. Actions need individual
  metadata, not a single generic app entry. Discovery is metadata, not execution authority.
- Runtime has an entry graph and execution graph; ChatService has a third App Fast bypass.
- AutomationRunner consumes Runtime.stream and requires VerifierEvent before success.
- CLI consumes stable runtime events; Desktop uses Runtime.stream_session and SSE.
- Checkpoint validates node names and GraphState types; both must migrate together.
- Existing working-tree README/intro changes are unrelated and will be preserved.
- Initial baseline was invalid because C: temporary SQLite databases reported disk full;
  rerun with TEMP/TMP and pytest basetemp under E:/Learning/xiliu/tmp/graph-v2.

## P1 — state and registry contracts

Add structured intent, candidates, serialized loop state, execution results/IDs.
Register App Actions separately; retain Skill/MCP/SubAgent and policy boundaries.
Verify state contracts, existing registry/security/evidence tests.

## P2 — two-layer routing

Command Adapter → rules → optional embedding matcher → strict LLM classifier.
Control commands terminate outside execution; skill/mcp constrain capability selection.
Capability Router selects chat, app, bounded Fast ReAct or Planner without execution modes.
Verify command parsing, source scope, ambiguous/destructive requests, classifier fallbacks.

## P3 — one StateGraph and real execution

Register exactly the 12 nodes from the spec. Planner/Fast invoke the model;
capability_discovery retrieves registry metadata; tool_execute alone invokes Gateway;
state_collect ingests actual receipts, child events, evidence and persisted todos.
State collection returns to discovery for subsequent tool rounds, then verifier.
AppExecutor prepares direct dispatch; App business steps run inside tool_execute.
Chat → final; ambiguity → clarification → final; verifier → final/retry/replan/clarification.
These edges complete the supplied diagram's abstract Registry/State boxes and omitted nodes.
Keep public event contracts and persistence; update Runtime, Desktop and recovery atomically.
Verify graph nodes/edges and actual streamed node paths, App writes, bounded loops and resume.

## P4 — verification and all 51 evaluations

Verify actual receipt/database state, tool failures, plan acceptance and source scope.
No success from model prose alone; confirmation/ambiguity are explicit incomplete outcomes.
Deterministic model/network fixtures drive the production graph and real temporary SQLite
services/Gateway/policy, with expectations stored separately from the original JSONL.
Check traces, receipts, database rows/files, denied permissions and no unintended effects.

## P5 — cleanup and regression

Delete graph/modes and Supervisor forwarding, remove mode HTTP/runtime parameters and bypass.
Document new graph, migration and test commands; run full pytest and lint.
Report every remaining failure, distinguishing baseline failures and obsolete contracts.
Do not weaken original tests or alter their expectations to hide defects.

## Results

Each phase records its commands, actual results and implementation rulings below.

### P0 result
E: baseline: `pytest -q --disable-warnings --basetemp=tmp/graph-v2/baseline` →
573 passed, 1 skipped, 1 failed (test_current_repository_surface_and_registry_contracts_are_fully_classified).
This failure existed before the graph changes and reflects the pre-existing intro removal.

### P1 result
Contract tests RED: 3 failed. Registry confirmation metadata uses confirmation_policy,
not confirmation_required. Permission is the existing knowledge.write; no new delete grant.
P1 GREEN: contracts + agent registry + shared evidence + kernel security → 11 passed.

### P2 result
Routing + contracts + existing App Intent tests → 75 passed.
Embedding stage is optional and only accepts an explicitly configured local matcher.
No implicit embedding-provider network call is introduced.

### P3 result
Topology/real execution tests RED: 4 failed. Unified graph tests GREEN: 22 passed.
Adapter regression found checkpoint progress after FinalEvent and CLI chat history marked
as workflow by checkpoint events; both defects are fixed in the event adapter.
Chat identity + ChatService + Desktop checkpoint + Automation resources + graph integration
regression → 29 passed.

### P4 result

All 51 original JSONL tasks are parameterized against Runtime's production graph, the real
ExecutionGateway/AppDispatcher, isolated SQLite/services and actual filesystem. Only model
and remote provider responses are deterministic fixtures; this is not a live-model quality score.
The initial 51-task run exposed three routing/tool-surface defects; those source defects were fixed.
Evaluations + security/recovery + topology → 60 passed before the later review additions.
Every task now also records real node visits, execution status, receipt verification and database
read-back in JUnit properties; the final focused suite → 80 passed.

Ambiguous, confirmation-gated, denied and incomplete tasks explicitly assert verified=false.
Tasks 11/19/35/38 cannot be counted as completed in these controlled scenarios: workspace escape,
unconfirmed deletion, search without archive effects, list without persisted automation creation.
The remaining incomplete IDs are 3/4/7/9/10/26/27/28/29/32/33/39/40/43/48/49.

### P5 review and cleanup

Removed graph/modes, the old nodes.py implementation, Supervisor forwarding, runtime/API mode
arguments, dual entry/execution graph use and ChatService App bypass. app/fast.py remains a
three-line import compatibility shim; business implementation lives only in app/executor.py.
build_entry_workflow is a compatibility alias to the same twelve-node graph.

An independent read-only review reproduced and helped verify fixes for:
- receipt-time stop/resume duplicating an App write (stable execution identity + receipt replay);
- automatic replanning after successful App writes (stop for clarification);
- file_read falsely proving file movement (real filesystem effects required);
- historical App reads/writes conflicting with later legal writes (per-object final state);
- an existing unrelated SQLite database falsely proving creation (hash change + real execution);
- partial batch supersession (recheck unsuperseded records individually).

Regression fixtures were migrated only where the removed execution-mode API was directly used:
intent routing assertions now use two layers; RAG manifests use planner paths; the existing
Fast error test explicitly sets max_attempts=1 to test a single failure. Actual permissions,
receipt assertions, persisted rows, hit IDs, failure budgets and child evidence remain checked.
Coverage manifest tests entries now name the actual migrated tests; historical execution data
and pre-existing stale Intro classifications were not rewritten.

New public adapter tests run real AutomationRunner with Runtime, CLI history controls, old
checkpoint migration, MCPManager discovery/schema/allowlist/policy, and SubAgent RAG evidence.
The exact graph topology test compares every registered node and every edge, including recovery.
MCP/SubAgent + partial batch regression → 4 passed. Production type checks → 0 errors;
source/tests Ruff → all checks passed. Final full results are in validation.md.

Delivery-source full regression: **668 passed, 1 failed, 1 skipped in 309.14s**.
All 51 supplied evaluations passed against real node paths, receipts and database assertions.
The sole Python failure is the unchanged P0 Intro classification failure. Existing frontend:
56 tests passed, 14 files passed, 1 suite failed to load the pre-existing deleted LandingPage.
Final JUnit: `logs/graph-v2/p5-delivery-full.xml`; task evidence: `eval-results.json`.
