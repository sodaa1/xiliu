# Companion clarity, idle expressions and native verification

## Delivered behavior

The small raster pet no longer rotates or scales during dragging. A stepped vertical lift snaps to whole physical pixels at the current devicePixelRatio. The first idle expression appears after 1.5–2.7 seconds, followed by 3.5–5.3 second neutral intervals. Blinks last 220ms and smiles 1400ms. Hover smiles expire after 1200ms so a resting pointer cannot suppress automatic blinking. Drag surprise and active-composer expression priority remain intact; hidden/reduced-motion pages pause automatic expressions.

Native Windows testing found that Tauri 2.12.2 rejects remote custom IPC without an app permission manifest. Explicit command groups now cover main, companion and capture separately. Only after the owned child service proves readiness with the launch token are runtime capabilities installed for that exact localhost port and matching window. The previous static all-port remote grants were removed. Companion/capture navigation is additionally restricted to its own page path. WebView2 reports IPC origin without page path, so capability URL matching uses the owned origin while navigation guards enforce page paths.

## Verification

- Frontend: 117 tests in 26 files passed. ESLint passed. All five changed frontend files passed Prettier. The repository-wide format check still reports 72 unchanged files from the existing UI; no unrelated formatting changes were made.
- Backend: full pytest suite, 831 passed and 1 skipped.
- Rust: all 8 tests passed, including the exact-port/window-role capability policy. Native debug build passed with an isolated preview identifier, io.xiliu.desktop.pet-preview.
- Production frontend build passed. Existing >500kB main bundle warning remains. The frozen service frontend index and app JavaScript SHA256 match the final web build (app-DNJ3NmOC.js, 228056D1809E2AB8179FA053DAF21736D7A1B3CB38C325FE51A0009791E1FB78).
- Surface guard: 803 classified occurrences, zero errors. Runtime Agent equivalence is not claimed.
- Browser: both forms at DPR 1, 1.25, 1.5 and 2 passed automatic blink/smile, hover expiry, unchanged drag footprint, unscaled/unrotated drag matrix, physical-pixel lift, surprise and dock recovery. See browser-e2e/clear-drag-idle-browser.json. The unchanged-footprint check failed before the drag fix; two idle tests failed before the timer fix.
- Actual native Windows app with current frozen backend: main/pet IPC, Windows-confirmed main minimization with pet visible, restore via settings, independent 125/150% setting synchronization and window resizing, native idle blink/smile, independent Inbox capture without AI credentials, saved-item navigation, close/reopen draft preservation and background conversation creation/acknowledgement passed. Wrong-window privileged commands and non-pet navigation were rejected. See browser-e2e/native-pet-verification.json.
- Native lifecycle: normal app close with pet disabled exited and released the owned port. Restart chose a different port, retained both scales/form/enabled state, then restored default 96px Q form. All four raster images decoded at actual DPR 1.5. See browser-e2e/native-pet-lifecycle.json and native-pet-restored.png.
- Frozen full default smoke verifier passed twice, each covering private-route and stdin-EOF shutdown, exit code 0, released ports and same-data restart. The earlier single timeout was not reproduced; no unsupported timeout or lifecycle change was introduced. See browser-e2e/pet-frozen-service-proof*.json.
- Independent review found no Important/Critical issues in expression fixes or native ACL integration.

## Runtime and limits

A runnable native preview exists at desktop/src-tauri/target/debug/xiliu-desktop.exe with adjacent frozen-service resources. This is a developer preview, not a newly built installer. Its isolated application identifier does not use the normal installation data directory. Verification used no real model credentials; quick chat was verified through background creation/acceptance and the expected unconfigured-model error, not a real provider answer.

Actual cursor-driven OS dragging and cross-monitor DPI transitions cannot be simulated through this CDP harness; native geometry/release logic and browser expression/drag states have automated coverage. The native transparent window was visually inspected after restart. Browser captures remain the detailed expression/compositing evidence.

The default remains approved PNG artwork with local facial overlays. Import/storage and runtime code for rigged Cubism models is implemented, but real mesh deformation requires the character's rigged model export and licensed Cubism Core; these assets are not bundled or claimed complete.
