# Desktop Companion Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task in this session. User approved starting implementation on 2026-10-15.

**Goal:** Preserve both character forms, integrate the standing portrait in Today, and provide a small Windows companion with conversation and Inbox shortcuts.

**Architecture:** Main WebView owns ChatProvider and live conversations. A Rust coordinator manages companion/capture windows, tray, preferences, request acknowledgements and compact status snapshots. Auxiliary React routes share existing Inbox import behavior.

**Tech Stack:** Tauri 2 / Rust, React 19 / TypeScript, TanStack Query, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-15-desktop-companion-design.md`

## Global Constraints

- User's latest size constraint overrides the draft: default character height 96 CSS px, adjustable 72–128 CSS px.
- Keep existing Python service, model configuration and import semantics; no additional AI requests.
- Work in attached worktree `codex/desktop-companion`; original dirty checkout stays intact.
- All commits use `sodaa1 <soda933693@163.com>`, without AI attribution.
- PNG assets are usable source art; no completed Cubism model exists. Do not claim Live2D completion or substitute a different character model.

## Review Focus

- A failed or late quick-chat acknowledgement must preserve the draft and never submit twice.
- Minimized/hidden main window keeps ownership of active streams; explicit quit still shuts down its service.
- Desktop transparency is restricted to the companion route; normal main-window backgrounds remain intact.
- A small companion or restored position must remain reachable across monitor/DPI changes.
- Capture errors and cancel/close retain draft until explicitly discarded; main queries refresh after save.

## Task 1: Character surfaces and capture reuse

**Files:** `web/public/companion/*`, `web/src/features/companion/*`, `web/src/features/today/TodayPage.tsx`, `web/src/features/content/CaptureDialog.tsx`.

**Interfaces:** `CaptureForm({onClose,onSaved})` shared by the existing dialog and an auxiliary page; `TodayCompanion` renders the standing portrait and shortcuts.

- [x] Add tests that prove capture failures preserve text, duplicate submission is blocked, and successful capture can be repeated.
- [x] Run the new tests and observe the expected missing-feature failure.
- [x] Extract the existing form without changing business semantics; add retained auxiliary capture page.
- [x] Copy selected PNGs, add a scoped responsive welcome section, and verify build/visual layout.

## Task 2: Windows coordinator and frontend bridge

**Files:** `desktop/src-tauri/src/companion.rs`, `desktop/src-tauri/src/main.rs`, `desktop/src-tauri/Cargo.toml`, capabilities; `web/src/desktop/companion.ts`, `CompanionController.tsx`, `CompanionPage.tsx`, `App.tsx`.

**Interfaces:** Rust commands prefixed `companion_`; JSON `CompanionSnapshot` with monotonic revision, phase, cid, message and count; request IDs with pending/accepted/failed states. Only main can publish snapshots and acknowledge requests.

- [x] Add tests for selected-run prioritization, no reasoning leakage, stale revisions, small default size and bounded settings.
- [x] Observe failing tests before implementing the corresponding behavior.
- [x] Add native tray/window lifecycle and trusted-window checks; keep sidecar shutdown ownership unchanged.
- [x] Relay quick chat to main, acknowledge after creation, retain pending draft, publish true execution states and refresh content queries after capture.
- [x] Add companion controls to main, plus browser preview routes; verify TypeScript and Rust compilation/tests.

## Task 3: Verification and delivery

- [x] Run complete frontend suite, targeted lint, production build and Rust tests/check.
- [x] Inspect main and companion routes visually at intended sizes using a local app service without model calls.
- [x] Obtain an independent review of the feature diff, resolve material findings, and update the execution ledger.
- [x] Commit only feature changes in the isolated branch and report actual validation plus the missing Live2D model.

## Remaining stage

- [ ] Prepare layered art, build the approved Q-version Cubism model, integrate its SDK renderer and verify real animation transitions. The current implementation renders the approved PNG and does not claim Live2D completion.
- [ ] Validate the packaged Windows app on real multi-monitor/DPI changes, tray exit and long-running minimized chats. Native compilation/unit tests and browser UI verification do not replace these checks.

## Execution ledger

- Baseline: frontend suite passed, 16 files / 68 tests.
- Ruling: execute inline after the user's explicit instruction to start; no further design permission question.
- Ruling: independent worktree starts from committed HEAD; original checkout's uncommitted UI changes are preserved there, not copied or committed here.
- Pre-flight: Task 1's shared CaptureForm is consumed by Task 2's capture route; Task 2's snapshot type is shared by Rust coordinator and React controller and will use matching camelCase fields.
- Task 1: complete — shared form, native capture page, selected character assets and Today surface. Duplicate-submit test failed with two imports before the fix, then passed.
- Task 2: complete — frontend bridge, Rust coordinator and bounded small window settings. Tray intent and stable-subscription regressions were observed failing before their fixes.
- Review: three material findings fixed with regressions: saving cannot discard newly edited input, background quick chat does not change main conversation selection, and stopped tasks are not reported as successful.
- Verification: frontend 20 test files / 78 tests passed; targeted ESLint passed; production build passed; Rust 4 tests passed.
- Browser: actual character button 96×96; capture scroller 600px high with 654px content and overflow:auto; local save, archived-item lookup and draft reload passed; no page errors. No live model API calls were used.
- Ruling: preserve the isolated branch without merging into the original dirty checkout or publishing. Live2D and packaged-native UI acceptance remain explicit outstanding work.
