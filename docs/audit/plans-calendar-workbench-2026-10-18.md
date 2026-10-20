# Plans calendar workbench QA — 2026-10-18

final result: passed

## Visual target and evidence

- Source: user attachment `C:/Users/Sodaa/AppData/Local/Temp/codex-clipboard-09b67649-e358-48ee-ab00-0ed749a242c5.png`, 1536×1024. Only the topmost “方案一 · 现代日历工作台” is the target.
- Source comparison crop: (425, 11)–(1473, 617), 1048×606, excluding reference sidebar and presentation captions.
- Render: local `/plans`, 1440×1000 CSS pixels, DPR 1, Asia/Shanghai, light theme, small existing app font; mock clock 2026-10-18. Desktop and mobile browser fixtures are isolated simulated task data and never write to a real backend.
- Implementation page content capture: 1366×942, excluding existing Shell, normalized to 1048px width with aspect ratio preserved. Different screen height leaves extra bottom whitespace; no stretching or pixel similarity percentage was used.
- Full comparison: `browser-e2e/plans-calendar-2026-10-18/comparison.png`.
- Desktop: `browser-e2e/plans-calendar-2026-10-18/desktop.png`; dark theme: `dark.png`; mobile task area: `mobile-tasks.png`.
- Focused comparison images: `.preview/plans-calendar/detail-stats.png`, `detail-calendar.png`, `detail-tasks.png`. Opened together with full comparison and the final desktop, mobile and form captures.
- Browser checks and viewport geometry: `browser-e2e/plans-calendar-2026-10-18/report.json`. Reproducer: `verify.cjs` (uses the installed desktop Playwright runtime and running Vite at port 5173).

## Five fidelity surfaces

- Typography: project font and preference retained; task titles at 1rem, metadata at .85rem. Headings, dates and compact filters remain distinct. Long titles wrap/truncate without widening columns.
- Layout: four statistics; 36/36/28 content columns with 18px gaps; calendar and selected-date agenda share one card; task editor below the scope tabs; two right progress groups. Desktop primary cards have bounded equal heights and independent list scrolling; adding a task stays accessible. Tablet uses two columns and moves goals below; mobile uses a single column.
- Colors: existing white/light gray and #7773E9 accent roles, low contrast outlines, restrained lavender shadows. The fire icon has an orange tint. Dark theme uses existing tokens.
- Assets/icons: existing Lucide icons and Shell brand reused. Reference mountain illustration is in the Shell/presentation area outside this page's authorized scope, so it is not recreated. Charts are actual-data UI graphics, not decorative raster images.
- Copy/data: requested title/subtitle and primary action retained. No invented category, priority, description or duration fields. The reference’s 2024 month, fake streak and illustrative percentages are replaced by local dates, real task aggregates and “暂无记录”. Central list retains all records in its chosen scope, including undated ones; the date agenda only includes daily tasks with that actual local due date. This makes its count differ from the scoped list by design.

## Comparison and repair history

1. Initial browser render: long lists expanded desktop cards and displaced the add area. Global input styles added a second search border and changed its direction. P2: bounded the cards, enabled internal scrolling and strengthened only local search/input selectors.
2. Full-view and focused comparisons: card density and weekly-focus rows differed from the reference. P2: reduced card heights, tightened row spacing and placed each focus name/progress/count on one line. Added the restrained moving tab background alongside the reference underline.
3. Responsive and dark captures: 320px stats overflowed; global dark rules outlined every calendar date and filled inline inputs. P2: adjusted narrow stats and added local dark overrides. Fresh captures and geometry checks at all eight viewports have zero horizontal overflow.
4. Final full/focused comparison and desktop/mobile/form inspection found no further actionable P0/P1/P2 visual issue. Remaining differences are data and existing-Shell adaptations described above. The 90% similarity request is a design goal, not a measured or claimed score.

## Functional verification

- Search filters the task list and date agenda; no-date tasks remain visible in the list and do not acquire dates.
- Day/week/month are distinct views. Local Monday-start dates handle month-end, leap February and year-crossing weeks. Arrow keys/Home/End/PageUp/PageDown are supported; browser ArrowRight focus/selection passed.
- Create, edit, toggle/recover and delete all use existing workspace API and shared query invalidation for plans/today. Browser checks confirmed cross-panel synchronization.
- Creation uses the chosen scope and optional eligible parent/time. Editing an independent calendar task does not inherit a list parent filter. Goal filters survive switching between eligible child scopes.
- Modal Escape restores trigger focus. Mobile edit/delete controls are visible and the dialog stays within the viewport.
- Empty/error states retain useful actions; unavailable data is not presented as zero statistics.
- Reduced motion honors both app and OS preferences; normal list animations settle with clean transforms. No browser page errors.
- Eight widths: 1440, 1200, 1024, 900, 768, 767, 390 and 320px. All showed zero page/body horizontal overflow.
- Existing demo adapter verified through a separate local preview at port 5184; creation works without a real server/database.

## Limits

Browser writes used isolated fixtures and the existing demo adapter. This pass does not claim live-backend end-to-end coverage. No completion-history field exists; streak intentionally remains unavailable. Build retains its existing >500kB bundle warning. No new package or database field was added.
