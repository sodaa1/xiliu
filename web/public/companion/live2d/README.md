# Live2D runtime and model assets

The app lazily loads Cubism 3/4 models via pixi-live2d-display. Existing images remain usable without a model or WebGL.

Before distributing a Live2D-enabled build, obtain Cubism Core for Web from https://www.live2d.com/en/sdk/download/web/ under its applicable license, and place `live2dcubismcore.min.js` in this directory. The proprietary runtime is not silently downloaded or represented as bundled.

Export the approved chibi and standing artwork from Cubism Editor as separate `.model3.json` + `.moc3` + texture/motion bundles. Import each complete folder through Settings → Appearance → Live2D. The approved PNG artwork is not a rigged Cubism model and cannot provide eye or mesh parameters by itself.

The renderer has transparent output, 30fps cap, pointer focus, optional Idle/Thinking/Success motions, resize handling, reduced-motion support, visibility pause, cleanup and static fallback. The 96px desktop window footprint is preserved for both forms.

References: https://docs.live2d.com/en/cubism-sdk-manual/model-web/ and https://github.com/guansss/pixi-live2d-display .
