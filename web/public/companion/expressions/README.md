# Facial expression frames

Both chibi and standing forms have blink, happy and surprised PNG variants derived from their existing character artwork. All variants keep the original canvas size and face placement.

The renderer retains the original neutral character image. It reveals only eyes and mouth from these frames through feathered masks, so regenerated hair, clothes and body never replace the approved artwork. Keep frames aligned with chibi.png (1254x1254) / standing.png (1024x1536) when updating them.

- Idle: first blink after 1.5–2.7 seconds, then a 3.5–5.3 second neutral interval. Blinks last 220ms; every third cycle includes a 1400ms smile.
- Hover: a 1200ms smile, then idle resumes even while the pointer stays. Active composer or success phase: happy.
- Dragging: surprised, taking priority over happy/blink.
- Hidden page and reduced motion: pause automatic expressions. Direct interaction expressions remain available.
- Failed or undecoded expression images leave the original face visible.

These raster expression overlays do not require Cubism Core. Imported rigged models use their own named expressions and are never covered by PNG facial overlays.
