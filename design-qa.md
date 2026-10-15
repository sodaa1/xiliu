# Companion interaction visual QA

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
