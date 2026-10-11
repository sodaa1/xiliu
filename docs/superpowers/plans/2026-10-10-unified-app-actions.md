# Xiliu v0.4 Unified App Actions Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task. Independent Feed, preferences and audit work uses superpowers:dispatching-parallel-agents.

**Goal:** Expose every authorized application operation through one `app` tool, with Fast local execution and reproducible surface/permission/persistence tests.

**Architecture:** `ActionRegistry` binds strict schemas and handlers to existing services. `AppDispatcher` checks action-level policy, confirmation, idempotency and persisted postconditions. The same service context is injected into Graph and private agents; a bounded typed intent resolves local commands without Planner/Supervisor.

**Tech Stack:** Python / FastAPI / Pydantic / LangGraph / SQLite; React / Vitest / browser E2E; PyInstaller / Tauri / NSIS.

**Spec:** ../specs/2026-10-10-unified-app-actions.md

## Global constraints

- Preserve current 0.3.2 fixes, user data and the primary checkout's pending documentation migration.
- Only one Agent-visible App tool: `app`; reuse Service methods, never arbitrary local HTTP or SQL mutations in handlers.
- No UI redesign or replacement RAG/LLM/SQLite core. Existing CLI, UI and desktop remain usable.
- Strict schemas, action-level policy and scope, local-only URL saving, bounded network fetch, real persisted verification.
- Formal tests are committed; every new UI/HTTP/Service operation requires audit coverage or CI fails.

## Review focus

- Negation and questions never accidentally mutate user data.
- Private RAG/background agents cannot escalate through the unified tool.
- Replayed request IDs and confirmation tokens cannot duplicate or broaden writes.
- Async metadata is pending until complete; user revisions and partial cancellation are retained.
- Refresh/restart retain manual Feed items and hidden external items.

## Task 0 — Baseline and complete inventory

Files: scripts/audit_app_surface.py, docs/audit/all-pages-capabilities.md, docs/audit/baseline.json.
- [ ] Scan all UI events/API calls, HTTP routes and public Service methods; record gaps and exceptions.
- [ ] Measure current installer SHA/bytes, uncompressed sidecar, startup and local workflow overhead using disposable data.
- [ ] Verify current baseline tests before product changes.

## Task 1 — Registry, dispatcher and policy

Files: src/xiliu/app/actions.py, dispatch.py, tools/app.py, execution/gateway.py; tests/unit/test_app_dispatch.py.
Interfaces: `get_registry() -> dict[str, ActionSpec]`; `AppServices.from_state(state)` and `AppServices.open(data_dir)`; `AppDispatcher(services, context).execute(action_id, arguments, request_id=None, confirmation_id=None) -> dict`.
- [ ] Red tests for unique registry entries, strict arguments, unavailable context, per-action denial, role allowlist, confirmation and durable request replay.
- [ ] Implement catalog/describe/execute, bounded receipts and persisted postconditions through existing services.
- [ ] Bind one AppTool in Fast/Planner/private agents; move embedding helpers out of old wrappers.

## Task 2 — Complete Feed service, HTTP and UI

Files: api/services/feed.py, feed routes, FeedPage, workspace-api types; tests/integration/test_feed_actions.py and Feed UI tests.
Interfaces: `list(source='', q='', include_hidden=False)`, `add_manual(payload)`, `update_manual(id,payload)`, `remove_manual(id)`, `restore_manual(id)`, `hide_external(id)`, `unhide_external(id)`.
- [ ] Red tests for manual CRUD, stable IDs, refresh/restart, hide/unhide, safe optional fetch and HTTP errors.
- [ ] Add separate persistent tables, controlled one-fetch metadata, page controls and same-service API.
- [ ] Register all Feed actions and verify UI/Agent equivalence.

## Task 3 — All existing domains and safe preferences

Files: app/actions.py; api/services/preferences.py, preferences routes; web/src/lib/preferences.ts; tests/integration/test_preferences_actions.py.
Interfaces: `PreferencesService(store).get/update/reset`; UI synchronization must preserve prior browser/desktop settings with revision/conflict checks.
- [ ] Register Today tasks, Inbox/content, Knowledge folders, conversations, automations, settings read and capabilities read.
- [ ] Red tests for sync, sensitive model/credential restrictions, attachment grant and destructive confirmation.
- [ ] Implement bounded bulk/local classification and restartable async URL workflows via dispatcher; preserve revisions.

## Task 4 — Fast typed intent and tool migration

Files: app/intent.py, graph/routing.py, modes/fast.py, nodes.py, agents/runtime.py, agents/rag_agent.py, manifests, runtime.py and chat.py.
- [ ] Red semantic tests for all module verbs, synonyms, negation, explanatory questions, references and ambiguous objects.
- [ ] Execute high-confidence local intents without model planning; at most one bounded typed-model parse for ambiguity.
- [ ] Remove old App/RAG BaseTools, duplicated prompts/registrations and legacy tool consumers after migration tests pass.

## Task 5 — Coverage guard and complete regression

Files: scripts/audit_app_surface.py, verify_all_app_actions.py, coverage manifest, CI workflow, formal pytest/Vitest/browser tests.
- [ ] Red CI guard tests for a newly added unregistered route, Service method, UI mutation/button and business BaseTool.
- [ ] Generate the final matrix from actual code/Registry/test evidence; report failures by page and action.
- [ ] Test UI and Agent paths against equal fixtures, persisted DB/files, all modes/scopes, negative policy and replay cases.

## Task 6 — Measured cleanup and release

Files: desktop/build_sidecar.py, version metadata, docs/audit/package-size-before-after.md and performance/results reports.
- [ ] Measure top files and duplicates before trimming; retain required dynamic imports and CLI/TUI dependencies.
- [ ] Run full pytest/Ruff/Pyright, Vitest/lint/build, browser E2E, surface guard and frozen lifecycle smoke.
- [ ] Build NSIS; compare bytes/uncompressed size/startup/memory against baseline, and record honest limits.
- [ ] Commit source, tests and reports in reviewable phases; preserve primary checkout changes and do not push without instruction.
