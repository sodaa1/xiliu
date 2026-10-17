# Xiliu · 息流

![Xiliu home with the built-in background](docs/assets/xiliu-home-background.png)

[English](README.en.md) · [简体中文](README.zh-CN.md)

[Try the online demo](https://sodaa1.github.io/xiliu/#/today) · No installation or API key required. Uses sample data and simulated replies.

*Application home with the built-in background enabled. The home background can be changed in Settings.*

**Give information a home and ideas room to flow.** Xiliu is a local-first personal knowledge workspace and AI assistant connecting Feed, Inbox, Knowledge, Assistant, and Today.

Current version: **0.4.4**. React and FastAPI share the Runtime / LangGraph kernel; the Windows desktop uses Tauri 2. Documents and conversations stay on your device. Enabled model and network tools send their requests to the services you configure.

## Full Web deployment package

The self-hosted Web app supports accounts, isolated workspaces, user-owned model API keys, and an optional lifetime allowance of five operator-funded AI replies per account. Guests can try sample data and simulated replies without signing in.

Follow the [Docker deployment guide](docs/CLOUD_WEB_DEPLOYMENT.md); account data lives in the server's persistent volume. See [operations](docs/cloud-operations.md) for backups and account recovery. This is a deployable source package; a public full-service instance is not yet hosted. GitHub Pages remains the guest demo. Desktop sign-in and bidirectional synchronization are planned for a later phase.

Cloud mode disables local files, processes, Skills / MCP and shared search credentials; AI Hot and Web search are unavailable. The Windows 0.4.4 installer remains the local desktop edition.

## What's new in 0.4.4

- A shared first-visit feature tour for Web and desktop, with skip and replay controls.
- Chinese interface and six navigation shortcuts; companion drag feedback and standing hair/skirt inertia.
- [Online demo](https://sodaa1.github.io/xiliu/#/today) with sample data and simulated replies. This static site has no accounts or cloud synchronization.

## What's new in 0.4.3

- The home opens with the built-in background; saved blank and custom backgrounds remain unchanged.
- The Windows package includes an independent desktop companion with Q and standing forms, per-form scaling, compact chat and Inbox capture.
- Idle blink/smile, clear drag feedback, and native window command permissions are included. Rigged Live2D models and Cubism Core remain optional external assets.

## What's new in 0.4

- App business operations use one `app` tool and one ActionRegistry, backed by the existing UI services.
- Explicit local operations use Fast without Supervisor or model calls; optional AI metadata jobs persist and recover after restart.
- Feed supports manual add/edit/remove/restore and external hide/unhide. Non-sensitive preferences synchronize with revision checks.
- Human confirmations, per-action policy, cancellation and stored result verification are shared across execution paths.
- See the [v0.4 delivery report](docs/XILIU_04_UNIFIED_ACTIONS.md), [page capability matrix](docs/audit/all-pages-capabilities.md), [performance](docs/audit/fast-performance.md) and [package comparison](docs/audit/package-size-before-after.md).

## What's new in 0.3

- **Agent access to application data:** `inbox_import`, `inbox_list`, `knowledge_folders`, `knowledge_folder_create`, and `inbox_classify` reuse the UI's services. URLs are imported separately. When explicitly requested, unmatched cards can be saved to Knowledge without a folder.
- **Independent chats and cancellation:** each conversation owns its running state and request controller. Use other chats while one is running, stop only the selected chat, and retain received reasoning and completed operations.
- **Adjustable layout:** the main sidebar can shrink to 144px, the conversation sidebar to 160px, and the composer height ranges from 48–98px. Pointer and keyboard resizing persist across reloads.
- **Desktop and model connections:** uploads use HTML5 drag and drop; SDK reasoning and chat history are retained. Literal local model addresses bypass system proxies; external endpoints keep their proxy settings. Connection and authentication errors return directly instead of becoming repeated routing retries.
- **AIHot defaults:** first launch adds the public MCP configuration when missing and preserves existing user configuration. News retrieval does not require a model API key.

See the [0.3 change record](docs/XILIU_03_FIXES.md) and [0.3.1 repair record](docs/XILIU_031_FIXES.md). The patch adds current-weather retrieval, one workflow retry budget for search, and reliable Windows Git subprocess startup. [0.3.2](docs/XILIU_032_FIXES.md) adds folder creation and preserves Inbox tags when moving links to a requested folder.

## Features and workflow

**Discover → Capture → Organize → Ask → Act**

| Module | Features |
| --- | --- |
| Feed | AI Hot, GitHub Top 5, source status, Save, and Ask AI. |
| Inbox | Capture text, URLs, and files; preserve sources and originals, extract text in the background, optionally organize with AI, edit, and classify. |
| Knowledge | Tags, rule-based folders, Chinese hybrid retrieval, source references, and optional embeddings. |
| Assistant | Multiple chats, Markdown, model selection, reasoning, references for the current request, Stop response, Skills, and MCP. |
| Today | News and tasks in one view, with task creation, editing, and completion. |
| Settings | Models, profile, appearance, data, and automations; light / dark / system themes and reduced motion. |

## Windows installation

Download `Xiliu-0.4.4-x64-setup.exe` and its SHA256 file from [GitHub Release v0.4.4](https://github.com/sodaa1/xiliu/releases/tag/v0.4.4). Installers are published as release assets rather than committed to Git source.

1. Run the installer and follow its Chinese-language wizard. Python, Node.js, and Rust are not required to use the packaged application.
2. On first launch, configure your provider, API endpoint, model, and API key in Settings. The package includes no developer credentials, personal model configuration, databases, tests, or project documentation.
3. Capture documents in Inbox, organize them into Knowledge, and reference them in Assistant.

Windows x64 and WebView2 are required. The installer needs network access to download WebView2 when it is missing. The installer is currently unsigned. Desktop data lives in `%APPDATA%\io.xiliu.desktop`; development Web data defaults to `.xiliu/` in the repository. Exit the app and back up the complete data directory before upgrading. You do not need to delete your data to upgrade.

See the [Windows delivery record](docs/WINDOWS_RELEASE.md) and [desktop guide](desktop/README.md) for build and verification boundaries.

## Run from source

Install Python 3.12+, uv, and Node.js / npm. From the repository root:

```powershell
uv sync --dev
cd web
npm ci
npm run build
cd ..
uv run xiliu web --open
```

On Windows, you can also run `start-xiliu.bat`. The default URL is `http://127.0.0.1:8765`. For frontend development, run `npm run dev` and start `uv run xiliu web` from the repository root in another terminal. See `uv run xiliu --help` for CLI commands.

Building the Windows desktop also requires Rust MSVC and Microsoft C++ Build Tools / Windows SDK:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

The script builds the frontend, freezes the service, builds Tauri / NSIS, and exports the versioned installer and SHA256 file to `dist/`.

## Models and network services

Configure models in Settings, or copy `.env.example` to your local `.env`. Never commit real credentials.

| Variable | Purpose |
| --- | --- |
| `XILIU_PROVIDER` | Model provider. |
| `XILIU_BASE_URL` | Compatible model API endpoint. |
| `XILIU_MODEL` | Chat model name. |
| `XILIU_API_KEY` | Model credential; the API does not return its plaintext. |
| `XILIU_DATA_DIR` | Data directory. |
| `XILIU_EMBEDDING_MODEL` | Optional dedicated embedding model; leave empty for local retrieval. |
| `TAVILY_API_KEY` | Search service credential, separate from the chat model API. |

Chat models, URL metadata processing, AIHot MCP, and Search are separate call paths. Network access in one does not establish that the others are configured. External MCP services may also need their own runtimes and configuration. See [.env.example](.env.example) for all variables.

## Kernel and RAG

**Fast** handles lightweight chat and simple local queries. **Standard** uses planning, tool execution, and bounded verification. **Deep** can organize Todos and delegate to subagents. The optional API `mode` selects a path; omitting it enables automatic routing. NDJSON streaming and the Gateway permission chain remain shared.

Tool outputs become Evidence consumed by GraphState, Memory, and Verifier. RAG shares Knowledge's SQLite database. Document changes enter a persistent background queue; queries do not rebuild the entire index, and only changed chunks need new vectors. Default full-text and metadata retrieval needs no embedding service. The first RAG migration preserves an `app.pre-rag.sqlite3` backup.

The data directory's `agents/` contains `rag`, `research`, and `code` templates. Delegated permissions are narrowed to the parent's scope. See the [0.2 kernel record](docs/XILIU_02_KERNEL_RAG.md).

## Verification and limits

Fresh mainline regression on October 9, 2026: backend **124 passed / 1 skipped**, frontend **33 passed**. The skip is an existing static-resource test requiring unavailable Windows symlink privileges. See [project progress](docs/DEVELOPMENT_PROCESS.en.md).

```powershell
uv run python -m pytest
uv run ruff check src/xiliu
uv run pyright src/xiliu
uv run python scripts/verify_kernel_rag.py
cd web
npm test -- --run
npm run lint
npm run build
```

Tests are maintained with the source. Development logs, temporary data and test tooling are excluded from the installer. The offline proof script uses a fake model and needs no real provider credentials.

- Text extraction supports PDF / DOCX; scanned documents have no OCR. Saving a URL does not automatically fetch its full article.
- Stop response does not undo completed writes or provide resume-from-checkpoint. Blocking external calls may release only after more streamed data or a timeout.
- A crash inside a tool batch has no per-tool exactly-once recovery guarantee. Knowledge is single-user, and tool permissions are not OS network isolation.
- The desktop package has no development interpreter, pytest, or Ruff. Use the source environment for Code Agent Python scripts and tests.
- The 0.3 SDK / Graph / HTTP path was tested with a local mock API, without user credentials. Native desktop window file drops and WebView2 downloads on a clean device have not received interactive acceptance testing.

## Documentation and origin

[English docs](docs/README.en.md) · [中文文档](docs/README.zh-CN.md) · [Project progress](docs/DEVELOPMENT_PROCESS.en.md) · [中文进展](docs/DEVELOPMENT_PROCESS.md) · [Architecture](docs/ARCHITECTURE.md) · [Phase history](docs/PHASES.md)

The kernel originated from [sodaa1/xiliumini](https://github.com/sodaa1/xiliumini), baseline `6d3689583f93b3fafd6381b2b65c31d9613464e5`. This project uses `xiliu` for its brand, Python package, CLI, and configuration.

The introduction website source, scripts, and design records are in [`docs/web/`](docs/web/README.md); the application build still provides `/intro/`. Public introduction: [Xiliu](https://933693.xyz/projects/xiliu/).

## Product introduction concept

![Xiliu product introduction](docs/web/assets/xiliu-intro-concept-a.png)

*The image is a visual concept for the product introduction page; its cards contain illustrative content.*
