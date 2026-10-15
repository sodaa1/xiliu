# Independent companion interaction verification

## Behavior

- Chibi base height 96 CSS px, standing base height 168 CSS px; independent 100/125/150/175/200% preferences persisted by native settings. Older chibi pixel heights migrate to the nearest supported scale.
- Icon-only new chat / Inbox / more controls underneath the character. More exposes form switch, home and appearance settings. A single horizontal composer preserves draft and existing request-ID/acceptance behavior; Escape collapses without discarding text.
- Native OS window dragging waits for the Windows button release off the UI thread; browser preview uses pointer capture and bounded positioning. Controls hide during the held pose, then recover. Reduced motion removes continuous sway.
- Native window size includes composer, notice and optional controls. Offscreen anchors select the closest monitor work area before clamping.
- Settings follow pet/tray updates and merge each edit into current settings so an unrelated scale edit does not restore an old form or visibility.

## Verified

| Check | Result |
|---|---|
| Frontend suite | 111 passed / 26 files |
| Backend unit suite | 321 passed |
| Rust tests | 7 passed, including legacy preferences, limits, dock geometry and secondary-monitor edges |
| ESLint / TypeScript / production build | Passed; existing >500kB main bundle warning remains |
| Surface contract guard | 799 occurrences classified; 0 errors; runtime Agent equivalence not claimed |
| Browser interactions | Passed; see browser-e2e/companion-interactions.json |
| Native-sized DOM | 8 configurations: both forms, 100/200%, collapsed/expanded with notice and more; no clipping |
| Independent review | Two P2 regressions fixed; follow-up found no remaining Important/Critical issues |
| Visual QA | design-qa.md: passed for the approved composition with explicit physical-size adaptations |

## Limits

The native OS release loop and movement across monitors with differing DPI compile and have geometry/renderer boundary coverage, but were not exercised through a real packaged Windows application in this turn. This change builds no installer. Approved PNGs remain the default; genuine Cubism deformation needs rigged model exports and licensed Core. Whole-character drag sway is not artist-authored hair/cape deformation.

Browser preview preferences are local to the browser origin; native persistent preferences remain in companion.json. Browser preview does not claim desktop pinning or background-process behavior.
