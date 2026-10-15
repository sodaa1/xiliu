# Companion expression verification

## Change

The prior fallback rendered a single neutral PNG, so movement could not change its eyes or mouth. Both forms now retain that base image and overlay only aligned generated facial regions. Six files supply blink/happy/surprised states. The expression timer prioritizes drag over interaction/success over idle blink, pauses when hidden/reduced, and cleans up timers/listeners. Decode failure leaves the base face visible.

Imported Live2D models receive their own named expressions; no raster overlays cover the canvas. Genuine Cubism mesh deformation still depends on model/Core assets and is not claimed by this raster fix.

## Evidence

- PetAvatar tests: seven passed; three new expression cases failed against the preceding code before implementation.
- Full frontend suite: 115 passed in 26 files. ESLint, formatting and TypeScript/Vite production build passed. Existing >500kB main chunk warning remains.
- Backend unit suite: 321 passed. Static action/surface guard: 803 classified occurrences, zero errors; runtime Agent equivalence not claimed.
- Browser: both forms decoded all three frames; idle blink, brief close/return, hover smile, drag surprise/release and reduced motion passed with no page errors. See browser-e2e/pet-expressions-browser.json.
- Image comparison: six DOM captures show visible facial changes and zero changes outside a broad face rectangle above 8/255 compositing noise. See browser-e2e/pet-expressions-pixels.json. Motion disabled during this isolated pixel comparison only.
- Existing browser regressions: movement, toolbar recovery, no false chat click, draft retention, settings navigation, independent125/150 scales + reload, cross-tab updates and narrow composer passed. Eight native-sized DOM configurations still fit.
- Independent reviewer: seven expression tests rerun; no Important/Critical findings. Real native OS drag/mixed-DPI manual acceptance remains unchanged from the prior report.
- Visual QA: combined source/render comparison inspected; design-qa.md follow-up passed.
