# Companion interaction update

Approved target: the three previews accepted on 2026-10-15. Reuse existing independent Tauri companion and approved character images.

- [x] Add regression tests for independent form scale, compact composer and drag lifecycle.
- [x] Implement 96px chibi / 168px standing bases, independent 100/125/150/175/200% scales, legacy settings migration and bounded native geometry.
- [x] Place icon-only chat / Inbox / more controls under the character. Expand chat into one horizontal pill; preserve draft, request IDs and acceptance checks.
- [x] Add pointer dragging to web preview and native drag-end feedback; hide controls during drag, respect reduced motion.
- [x] Verify frontend, native geometry, browser interactions, audit classifications and visual fidelity; independent review before completion.

Constraints: no main-page layout changes; preserve capture and chat capabilities; use sodaa1 <soda933693@163.com> for any commit. Real rigged Live2D animation still requires approved model exports and Cubism Core.

## Execution evidence

- Reused codex/desktop-companion; no primary-checkout edits.
- Watched the missing compact controls / per-form preferences tests fail before implementation; native settings migration/limits tests likewise failed against the prior code.
- Independent review caught stale cross-window preferences and offscreen secondary-monitor fallback; both reproduced in failing regression tests before fixes.
- Final: 111 frontend tests, 321 backend unit tests, 7 Rust tests, frontend lint/build, 799 classified surfaces with zero guard errors.
- Browser checks passed: actual pointer movement and release, toolbar hide/restore, no accidental chat click, draft retention, settings navigation, independent scale persistence across reload, cross-tab updates, narrow viewport, reduced motion. Eight native viewport configurations rendered without clipping using IPC boundary doubles.
- Real Windows OS drag-release/mixed-DPI smoke testing and rigged Cubism animation remain manual/asset-dependent; no installer built in this change.
