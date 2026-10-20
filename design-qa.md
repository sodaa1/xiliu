# Companion interaction visual QA

## Latest plans form follow-up — 2026-10-18

final result: passed

Source truth: user attachment `C:/Users/Sodaa/AppData/Local/Temp/codex-clipboard-954ca8c8-f7be-48c0-a4d0-20e5c4f79704.png`, 1536×1024; cropped modal 975×803. Final implementation: `docs/audit/browser-e2e/plans-form-followup-2026-10-18/form-empty-desktop.png`, viewport 1536×1024 CSS px, DPR 1, modal 980×876. Both are light-theme empty new daily forms with normal priority. Current local date and requested additional status/category controls intentionally differ.

Opened and inspected the normalized combined `reference-comparison.png` and the focused `reference-comparison-form-detail.png` in the same evidence directory. Reference scales proportionally to modal width; no stretching or unmeasured fidelity score. Initial P2 control-orientation drift from shared labels was fixed; a further comparison prompted readable 24/16/14px form typography and buttons; dark capture prompted local illustration-caption and date-icon contrast fixes. Fresh final desktop, mobile and dark screenshots were captured after repairs. No actionable P0/P1/P2 visual findings remain.

Five fidelity surfaces: existing font family with reference-sized hierarchy; 980px two-column layout, restrained radii and shared footer; white/lavender/gray tokens and distinct status colors; actual generated WebP calendar illustration plus existing icons; functional form copy and local-date data without mock counts. The extra right-side controls make the final modal taller than reference. Generated mountain details/calendar angle and native date formatting are documented P3 differences, not a claimed pixel-exact match.

32 isolated browser checks passed with no page errors, including real demo persistence, selected date, category/status, week/list/chart synchronization, reminders, keyboard and 320–1440px layouts. Frontend: 222 tests, lint and production build passed. Backend: 931 passed, 1 skipped. Negative-offset timezone form/date tests also passed. Reminder scope is explicitly page-open; browser writes do not touch the user's stored profile. Full evidence and limits: `docs/audit/plans-form-followup-2026-10-18.md`. Older sections below are historical and retain their original scopes.

final result: passed

## Source and rendered evidence

Compared the three approved generated-image states against the running /desktop/companion UI and appearance settings in a single combined comparison image:
C:/Users/Sodaa/.codex/visualizations/2026/10/15/01a13e47-ce90-75c0-b335-b7cba3799c15/companion-design-comparison.png

Sources: generated images exec-2b09d80b-aed8-4659-bedf-e6e9f74cce3a.png, exec-ff97997c-80a6-4f24-a0b6-661b4d8750db.png and exec-5869fb9e-286a-4e82-9c07-292b49fb1cce.png in the same thread's generated_images directory. Sources are enlarged directions, not physical pixel specs. Captured implementation at 1440x900 CSS px / deviceScaleFactor 2, then used element screenshots at original density in the comparison. Focused captures in docs/audit/browser-e2e show controls/composer/scales.

## Fidelity review

- Typography/copy: existing app font, 14px composer placeholder, no visible button labels or panel title; tooltips and accessible names retained. Percentage labels remain legible in settings. No text overflow.
- Spacing/layout: controls below character, single horizontal composer expands left, two separate percentage rails. Standing toolbar centered beneath the larger character. Input's inherited rectangular focus shadow removed; composer has a subtle focus border.
- Colors/tokens: white floating pills, neutral icons, soft lavender send/selection accents; no page layout changes. App settings retain existing card styling.
- Images: reused approved transparent character assets, full character visible after image decode. Drag animation acts on the whole character. No unapproved character regeneration.
- Content/interactions: new chat, Inbox and more are functional, not decorative; composer draft survives Escape; both scale rows save independently. Actual pointer drag hides/restores controls. Native-sized DOM checks cover 8 configurations.

## Deliberate adaptations

The user-approved physical defaults are 96px / 168px, so 32px desktop hit targets occupy a larger proportion than in the enlarged generated mock. Artwork poses remain the already-approved project PNGs. Browser captures show transparency over white; desktop wallpaper/window chrome from the concept is owned by Windows and is not embedded in the pet. Settings use existing product card styles rather than recreating mock OS chrome. Native-only pin/enable controls appear only in the desktop application.

No actionable P0/P1/P2 visual issues remain. Native packaged OS drag/mixed-DPI smoke testing and genuine Live2D model deformation are outside this visual pass and are explicitly recorded in the verification report.

Checklist: source resolved, live implementation captured, combined comparison inspected, five fidelity surfaces checked, browser interactions tested, meaningful deviations documented.


## Expression follow-up (2026-10-15)

final result: passed

Source: six aligned blink/happy/surprised frames under web/public/companion/expressions. Rendered: both forms in the running companion, 100% defaults, deviceScaleFactor 3. Combined source/render comparison captured and inspected: docs/audit/browser-e2e/pet-expressions-comparison.png. No actionable P0/P1/P2 visual issues.

Original body artwork remains the base layer. Eye/mouth masks align in both aspect ratios; blink fully closes the eyes, happy changes eyes and mouth, surprise opens the mouth and eyes. Body pixels outside a broad manually selected facial box remain unchanged above <=8/255 compositing noise (six actual screenshot comparisons). Drag transform was disabled only for that isolated comparison.

Typography/copy, icon sizing, colors and controls are unchanged. Feathered masks avoid seams; permanent raster compositing prevents expression toggles from changing body edge antialiasing materially. Existing 96/168 defaults, independent scale saves, drag/compose/capture flows and eight native-sized viewports passed browser regression checks. Reduced motion stops automatic blinks while retaining direct interaction expressions.


## Clear drag and native follow-up (2026-10-16)

final result: passed for the implemented raster companion

Native startup capture inspected at actual DPR 1.5: docs/audit/browser-e2e/native-pet-restored.png. The 96px Q character and icon-only dock fit the transparent independent 136x172 CSS-pixel window. Both forms preserve the approved body art. Drag feedback uses stepped vertical lift without rotation/scaling; browser checks at four DPR values confirm the raster footprint stays fixed and lift aligns to physical pixels. Idle now includes visible 220ms blinks and 1400ms smiles; hover expires rather than holding closed eyes indefinitely.

Typography, pill spacing, colors and toolbar/composer layout remain the approved composition. The native settings, minimized-main behavior and independent capture window were exercised against the real frozen service. No new actionable visual issues found. Cursor-driven OS dragging/mixed-DPI movement and genuine Cubism deformation retain the explicit limits in companion-native-2026-10-16.md.

## Plans calendar workbench (2026-10-18)

final result: passed

Rebuilt only the plans work area against the user's topmost calendar-workbench attachment. Existing Shell and previous companion QA above are preserved. Source and browser screenshots were compared together, including focused calendar, task and statistics regions; desktop card density, input style collisions, dark-date outlines and 320px overflow were fixed and recaptured.

Evidence and limitations: `docs/audit/plans-calendar-workbench-2026-10-18.md`. Final comparison and browser report: `docs/audit/browser-e2e/plans-calendar-2026-10-18/`. Isolated mock data was used; no numeric 90% similarity score or live-backend coverage is claimed.

## Homepage reference theme (2026-10-19)

final result: passed for the scoped homepage implementation, with documented product adaptations; full-site redesign remains unfinished.

The user's original main-home, quick-capture and mobile reference images were inspected alongside actual Edge screenshots in combined comparison boards. Fixed background stacking, reference artwork, desktop typography/card density, mobile hero/stat heights, dark contrast and keyboard/modal races, then recaptured. Source normalization, remaining intentional differences, changed files, 20 actual browser checks and test logs: [homepage audit](docs/audit/home-workbench-2026-10-19/README.md). Prior project QA and pre-existing uncommitted plan/backend changes are preserved.

## Shared original navigation and Assistant reference redesign (2026-10-19)

final result: passed for the requested navigation/home/task-status corrections and Assistant page; remaining page-body redesigns are unfinished.

Restored one shared original icon rail, integrated existing capsule navigation into each page header/background with icon-only home theme choices, and replaced the old panorama with a newly generated native 2039x771 image. Added explicit three-state task selection through the existing API. Assistant is redesigned directly from the user's main/model/execution-trace references with existing functional capabilities. Fixed Feed grid placement, mobile conversation layout, settings return-query retention, duplicate knowledge-detail chrome and status-control hover overlap. Combined source/before/after boards, actual Edge screenshots, API checks, changed-file list, generated-asset provenance and test records: [navigation and Assistant audit](docs/audit/navigation-assistant-2026-10-19/README.md).

## Task menu, Feed reference redesign and shared typography (2026-10-19)

final result: passed for this scoped group; remaining page-body redesigns are unfinished.

Read the user's task menu attachments and Feed main/reading/source/saved references before implementation and compared them with actual Edge screenshots. Added a hover/focus/touch three-dot task menu with three color states, preserved CRUD and fixed editor return focus. Feed now uses the reference hero, compact picks and full manageable reading list, with source/read/editor dialogs and responsive layout. Shared Chinese sans-serif typography respects existing font, size, theme and reduced-motion preferences. Fixed legacy CSS cascade, card height, mobile filters and management availability found through screenshot/code review. No backend changes in this pass.

Evidence: [task menu and Feed audit](docs/audit/task-menu-feed-2026-10-19/README.md), including per-page before/after boards, reference comparison, actual API browser checks, 239 frontend tests, 931 backend tests (1 skipped), Lint, TypeScript, production build and surface guard results. Reference image crops are decorative fallbacks, not original news photos; native desktop-shell and non-Windows font appearance remain unverified. Previous QA and unrelated dirty changes are preserved.


## Remaining page reference implementation (2026-10-19)

Final result: implemented and browser-verified for Inbox, Knowledge, all five Settings categories, Automations, Onboarding, Companion controls/capture and Launch, with documented native/external-service limits.

Read the user's Inbox, Knowledge and Settings JPGs before each group and opened the combined normalized reference/actual Edge boards at completion. Corrected inherited layout collisions, menu handler ordering, settings focus, mobile file input overflow, model-name wrapping, narrow content titles and navigation labels. Full 12-step browser tours exposed and verified the App shell remount return-route fix. Kept original icon rail, both homepage themes and Plans layout. Typography, spacing, colors, artwork provenance and genuine product copy/capabilities were checked; no numeric similarity claim.

Final evidence: [remaining pages audit](docs/audit/remaining-ui-2026-10-19/README.md) and [gallery](docs/audit/remaining-ui-2026-10-19/index.html): 15 actual before/after boards, 5 user-reference comparisons, mobile/dark/empty/error states, 243 frontend tests, 931 Python tests (1 skipped), Lint, TypeScript, production build and 1073-surface guard. Actual API browser workflows use an isolated temporary database. No new dependencies, unrelated backend edits, deployment or Git commit. Native OS window/mixed-DPI and real external model/scheduler execution remain untested in this visual pass.
