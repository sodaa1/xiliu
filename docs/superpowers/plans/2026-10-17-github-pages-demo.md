# GitHub Pages demo deployment implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish the existing static visitor demo on GitHub Pages with working navigation, images and first-visit guidance.

**Architecture:** Build the same demo with the repository base path and opt-in hash navigation. Keep local preview and desktop routing unchanged. Use GitHub Actions to publish only the compiled demo assets; preserve any existing Pages configuration until inspected.

**Tech Stack:** Vite, React Router, GitHub Actions and GitHub Pages.

**Spec:** User request to publish the existing demo through GitHub; existing behavior in docs/WEB_DEMO_DEPLOYMENT.md.

## Global constraints

- Work on codex/github-pages-demo; preserve the unrelated untracked ort file.
- Git author and committer: sodaa1 <soda933693@163.com>.
- No accounts or cloud synchronization in this change; those are future work.
- Never publish local data, credentials, the desktop service, or the repository itself as static assets.

## Review focus

- Repository subpaths must cover runtime image paths as well as Vite-generated assets.
- Refreshing a copied route must work on GitHub Pages without server rewrites.
- The demo must remain isolated from real backend requests and normal-mode data.
- Existing remote commits and Pages deployments must be inspected before changing publication settings.
- Declare success only after the deployed URL and primary tour flows have been checked.

## Task 1: Build a portable Pages demo

- [ ] Add regression coverage for prefixed runtime assets and route selection.
- [ ] Add opt-in hash navigation and base-aware bundled resource paths.
- [ ] Add an Actions workflow using the actual Pages base path and upload only web/dist-demo.
- [ ] Run frontend tests, lint, a Pages build, and browser checks under /xiliu/.

## Task 2: Publish and verify

- [ ] Inspect remote main and existing Pages settings; commit and integrate without overwriting remote work.
- [ ] Enable Actions-based Pages publication if no existing site would be replaced, and push the reviewed change.
- [ ] Wait for deployment and verify the public demo, assets, tour and copied route refresh.
- [ ] Record the real public URL and any remaining external blockers.
