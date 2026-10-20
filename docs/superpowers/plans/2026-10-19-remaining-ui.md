# Remaining Xiliu pages implementation plan

> Execution: implement sequentially in the existing dirty checkout, preserving the current bytes as a local baseline. User explicitly requests direct implementation and one final acceptance; no intermediate approval gates or Git commits.

Goal: extend the approved pale-gray/white/lilac workspace to Inbox, Knowledge, every existing Settings panel, Onboarding, Automations, Companion controls and Launch, preserving APIs, routes and data.

Reference lock: the user's extracted `Xiliu_高清页面参考图` Inbox, Knowledge and Settings JPGs dominate. Existing approved homepage/Plans/Assistant/Feed supply tokens and chrome; remaining modules adapt those tokens to their existing behavior. Original icon rail and both homepage themes remain.

## Sequential deliverables

- [x] Capture a current-file baseline and before screenshots; inventory current routes and overlays.
- [x] Inbox: full-width rows, counted type filters, compact overflow actions, capture/editor/reading dialogs and deliberate empty state. Preserve selection, background processing and import semantics. Test existing content workflows and a shared overflow component.
- [x] Knowledge: folder navigation with full-width library structure, readable real counts, search-result rows and consistent folder/content dialogs. Test folder CRUD, search and document routes.
- [x] Settings: reference-inspired internal sidebar plus grouped content; retain all five categories and appearance subpanels, keyboard tab navigation and settings return URL. Test preferences, connection profiles and storage paths.
- [x] Automations: schedule rows, clear state switches, new-task form and history. Preserve every endpoint and timezone. Test existing drawer CRUD and focus behavior.
- [x] Onboarding, Companion and Launch: restrained matching surfaces, readable prompts, compact native controls, pale launch composition and reduced-motion handling. Preserve native window dimensions, approved pet artwork and desktop calls.
- [x] After each group: targeted tests, production browser capture, reference comparison and fix actionable layout/behavior findings.
- [x] Final: all frontend/Python tests, Lint, TypeScript/build, updated changed-file-only surface mappings, read-only review, screenshot gallery and explicit remaining limitations.

## Constraints and review focus

- No new dependency or unrelated backend edits. User-owned uncommitted work must survive.
- Avoid applying new page styles to legacy Today or Plans layouts; all new selectors scoped or shared intentionally.
- Keyboard, touch, narrow screens, dark/large-font and reduced-motion states must remain usable.
- Menus/dialogs must keep a stable return focus; full row CRUD must remain reachable.
- Source references must not introduce fake metadata, counters, model capabilities or unavailable backend functions.

## Final evidence

All planned groups implemented and verified. See `docs/audit/remaining-ui-2026-10-19/README.md` for reference adaptations, 243 frontend tests, 931 Python tests (1 skipped), production build, 30 responsive layouts and native/external-service limits. Read-only review findings were fixed. No commit or deployment.
