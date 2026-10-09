# Xiliu development history and project progress

Updated: October 9, 2026. Current mainline version: **0.3.0**. [简体中文](DEVELOPMENT_PROCESS.md). Usage and setup: [English](README.en.md) / [中文](README.zh-CN.md).

## Current mainline and independent repair work

Version 0.3 builds on the 0.2 three-mode kernel and shared RAG service. It adds Agent adapters for application writes, independent concurrent chats, per-conversation cancellation, adjustable sidebars and composer, preserved reasoning, direct model connection errors, and default public AIHot MCP configuration. See the [0.3 change record](XILIU_03_FIXES.md).

Agents reuse the actual Inbox import, listing, and classification services. URLs create separate cards. Explicitly requested saving can move unmatched cards to Knowledge without a folder. Classification and saving share revision checks to protect manual edits made while a model request is in progress. Chat execution and cancellation controllers are stored per conversation. Stopping one chat does not stop the others or undo completed writes. Layout sizes support pointer and keyboard adjustment and persist locally in the browser.

The current Windows artifact is `dist/Xiliu-0.3.0-x64-setup.exe`, 38,696,736 bytes (about 36.90 MiB), with a checksum file beside it. Users configure their own model API. Public AIHot defaults are bundled; developer credentials, tests, project documents, and user data are excluded. The 0.2 installation and native window lifecycle results remain historical evidence, rather than acceptance evidence for every new 0.3 behavior.

Fresh verification before this mainline upload:

| Check | Result |
| --- | --- |
| Backend regression | 124 passed / 1 skipped in 20.82 seconds. The skip is an existing Windows symlink privilege test. |
| Frontend regression | 10 files, 33 passed. |
| Python static checks | Ruff passed; Pyright reported 0 errors and 0 warnings. |
| Frontend checks and build | ESLint and TypeScript / Vite production build passed. |
| Existing 0.3 source and frozen-service reports | Owner token, unset API key, Knowledge, configured chat and reasoning, default MCP configuration, normal shutdown, and stdin EOF passed. |
| Existing 0.3 browser report | Resizing and persistence, concurrent chats and selected-chat cancellation, reasoning persistence, HTML5 uploads, 390px layout, and frozen-service AIHot refresh passed. |

Fresh logs are `logs/development/main-upload-*`. Earlier 0.3 reports are `.preview/03-source-smoke.json`, `03-desktop-smoke.json`, and `03-ui-report.json`. These files remain local. The model path was verified against a mock API without consuming real user model credentials.

Weather search loops and desktop `Checkpoint persistence failed` errors are being investigated on the independent `codex/fix-desktop-search` branch. **They are not completed mainline fixes in this upload.** Model APIs, Tavily Search, URL processing, and AIHot MCP are separate service paths. Successful URL imports do not prove that the search API is available.

Native desktop file drops and downloading WebView2 on a clean device have not received interactive acceptance testing. Cancellation is cooperative and offers no resume-from-checkpoint; blocking requests may wait for more streamed data or a timeout. Detailed earlier records remain in [PHASES.md](PHASES.md).

## Development approach

The original Runtime, LangGraph, Skills, MCP, Policy, and Hooks were retained, then exposed through a thin FastAPI layer and React workspace. The Python package, CLI, configuration, and development data directory use `xiliu`, `XILIU_*`, and `.xiliu`.

HTTP manages conversations, settings, and content. NDJSON streams chat status, reasoning, and final answers. Conversation UUIDs identify Runtime sessions. Web conversation context comes from SQLite, without automatically restoring earlier workspace history; the CLI / TUI retain their original defaults. Model APIs return whether a key is configured, without returning its plaintext.

Inbox, Knowledge, Feed, tasks, and automation were added to the same application. Automations reuse Scheduler / Store / Runner. Today aggregates existing services. Knowledge uses local hybrid retrieval by default, with optional embeddings.

## Current architecture

```text
xiliu/
├── pyproject.toml / uv.lock       # Python dependencies and lockfile
├── .env.example                  # Credential-free configuration template
├── start-xiliu.bat               # Windows Web launcher
├── src/xiliu/
│   ├── config.py / runtime.py     # Settings and session execution
│   ├── api/                      # Routes, services, SQLite store, lifecycle
│   ├── graph/modes/              # Fast / Standard / Deep
│   ├── graph/routing.py           # Mode and intent routing
│   ├── rag/                      # Shared retrieval, chunks, jobs, evidence
│   ├── agents/rag_agent.py        # Bounded local RAG delegation
│   ├── capabilities/agent_registry.py # Built-ins and manifests
│   ├── execution/evidence.py      # Normalized tool evidence
│   ├── execution/cancellation.py  # Cooperative cancellation
│   └── tools/app_tools.py         # Inbox import / list / classification adapters
├── web/
│   ├── src/app/                  # Routing and transition lifecycle
│   ├── src/features/             # Assistant, Inbox, Knowledge, Feed, Today, settings
│   ├── src/components/           # Shared UI and resizing controls
│   ├── src/desktop/bridge.ts      # Desktop preferences bridge
│   └── intro/ / scripts/         # Introduction page and export scripts
├── desktop/
│   ├── server.py / build_sidecar.py # Frozen service entry and packaging
│   ├── defaults/                 # Public MCP defaults, without credentials
│   └── src-tauri/                # Window, service ownership, NSIS configuration
├── scripts/                      # Build, verification, and log helpers
├── docs/                         # Bilingual docs, progress, architecture, evidence
├── logs/                         # Local development and preview logs
└── .xiliu/                       # Local data; excluded except versioned capabilities
```

## Execution and data flow

Chat requests validate the conversation and current references, handle slash commands, and enter Runtime with SQLite context and model settings. Automatic routing selects Fast, Standard, or Deep. Tools pass through the shared Gateway, Policy, and Hooks. Their normalized Evidence updates GraphState and supports Memory and verification. Tool loops and verification retries are bounded. Results and reasoning persist before the frontend displays them.

Inbox follows capture → background extraction → optional AI metadata → classification → indexing → retrieval. Originals and source metadata are retained. Revision checks prevent outdated background results from overwriting manual edits. RAG indexing uses persistent background jobs and shared SQLite; queries do not rebuild the index. Only changed chunks need new vectors.

Desktop packaging uses the same production frontend and FastAPI service. Tauri owns its service child, private readiness token, local logs, preferences, and shutdown. Desktop data is separated from development Web data. See the [Windows record](WINDOWS_RELEASE.md).

## Product modules

| Module | Implementation |
| --- | --- |
| Assistant | Multiple conversations, model overrides, reasoning, cancellation, Markdown, current-request references, Skills / MCP. `/clear` removes messages and summary; `/compress` reuses shared summarization. |
| Inbox | Text / URL / file capture, original retention, background import, extraction, optional AI metadata, edit, and Knowledge classification. |
| Knowledge | Tags, rule folders, manual corrections, hybrid retrieval, optional embeddings, and links to original evidence. |
| Feed | AI Hot and GitHub Top 5, cached results, source status, filters, Save, and Ask AI. |
| Today | News and tasks aggregated from existing services, with task management. |
| Settings / Automations | Model, profile, appearance, data, and recurring task configuration with recent run results. |
| Launch / Introduction | Galaxy launch animation and a separately built product introduction page. |
| Desktop | Tauri window, owned service lifecycle, preference persistence, and local logging. |

## Milestones

| Stage | Delivered scope |
| --- | --- |
| Phase 0 | Kernel baseline, design review, and xiliu naming. |
| Phase 1 | FastAPI foundation, model catalog, configuration, and error redaction. |
| Phase 2 | SQLite conversations, busy protection, Runtime connection, NDJSON streaming. |
| Phase 3 | Assistant UI, model settings, Web launcher, and API contracts. |
| Phase 4 | Slash commands and memory; fixes for context restoration, duplicate sends, Host handling, and cache races. |
| Phase 5 | Inbox / Knowledge, originals, Markdown, Chinese retrieval, and current-request references. |
| Phase 6 | Feed, tasks, Today, and automations on the existing execution chain. |
| Phase 7 | Regression and browser acceptance, provider / MCP checks, Save deduplication, scheduler shutdown races. |
| Later UI / desktop increments | Galaxy launch, grouped settings, preferences, background Knowledge imports, introduction page, desktop service. |
| 0.2 | Three modes, Evidence, Agent Registry, shared RAG, persistent incremental indexing, compatible API / CLI. Backend 111 passed / 1 skipped, frontend 30 passed at that stage. |
| 0.2 Windows | 36.55 MiB Chinese NSIS installer; actual install, native window / WebView2 launch, service retrieval, and shutdown checked. |
| 0.3 | Application writes, independent chats, cancellation, resizing, reasoning, model error / proxy handling, and AIHot defaults. Fresh backend 124 / frontend 33 passed. |
| This documentation and upload | Product image at the beginning of bilingual READMEs, bilingual progress records, and upload of the current mainline to GitHub `main`. New search / checkpoint repairs remain separate. |

Earlier test counts are historical results, not new assertions about this upload. See [0.2 kernel evidence](XILIU_02_KERNEL_RAG.md), [0.3 fixes](XILIU_03_FIXES.md), [phase history](PHASES.md), and [acceptance history](COMPLETION_REVIEW.md).

## File and data conventions

- Development logs go to `logs/development/`; preview logs go to `logs/preview/`. Desktop logs stay in its application data directory and rotate.
- Test sources, fixtures, setup, coverage, and browser reports stay local and are excluded from uploads. Source users need to obtain the test suite separately.
- Credentials, databases, user documents, dependencies, build outputs, `.preview/`, and logs are ignored. `.env.example`, dependency lockfiles, source, and required capability defaults remain versioned.
- Runtime Trace / Checkpoint files remain at their existing workspace paths for recovery and auditing.
- `scripts/collect-logs.ps1` collects development logs; active log files should be moved only after the owning service stops.
- Installation packages contain only the desktop shell, production frontend, core service, and necessary runtime resources, including legal notices. Model credentials are configured by the user.
