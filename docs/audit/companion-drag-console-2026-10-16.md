# Desktop companion startup and drag correction

Version 0.4.4, 2026-10-16. Local installer: `dist/Xiliu-0.4.4-x64-setup.exe`.

The previous worktree debug executable had Windows PE subsystem 3 (console), while release builds already used subsystem 2 (GUI). The Windows subsystem attribute now applies to debug builds too. Service creation already used CREATE_NO_WINDOW and remains unchanged. The rebuilt debug executable and extracted production executable both report subsystem 2.

The previous held pose moved only 2–4 logical pixels. It now lifts 6–9 pixels and swings ±6 degrees from an upper-body pivot, with no scale or blur filter. Release removes the transform and restores the icon dock. Reduced system motion keeps a static lift. Imported Live2D models receive drag/release state and can play Drag, Held, or TapBody motions; release stops that motion and resumes the current application phase. Default characters remain raster images, not rigged limb animation.

Validation: 118 frontend tests passed, ESLint passed, production web build passed, 8 Rust tests passed. A newly added renderer interaction test failed before the drag-state connection and passed after it. Final targeted companion tests: 15 passed. Browser checks exercised both forms at DPR 1, 1.25 and 2, with and without reduced motion (12 cases): changing body rotation, unchanged scale, hidden dock, release reset and no accidental composer opening. The final extracted installer passed matching resource hashes, GUI subsystem and 0.4.4 version checks; its frozen service reached readiness, served the companion and exited normally through its private shutdown endpoint. See [package evidence](releases/0.4.4/package.json) and [browser motion evidence](releases/0.4.4/motion.json).

Limits: no installer wizard was run against user data, and physical mouse dragging across native windows/monitors was not repeated. Browser checks verify the renderer and pointer path; PE inspection verifies executable subsystem. The screenshot's old console window was not present during this run.
