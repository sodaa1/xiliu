# Plans calendar workbench implementation plan

> Execution: implement inline in the current workspace. The user's attached topmost calendar workbench is the selected visual target.

**Goal:** Rebuild only `/plans` as the selected calendar workbench while retaining the existing task API and query invalidation.

**Architecture:** One `['plans']` query and page-owned mutations supply every panel. Pure local-date helpers derive calendar cells and statistics. Local calendar, task row/form, statistics and progress components render that shared data. App Shell and other feature styles are unchanged.

**Tech stack:** Existing React, TanStack Query, Lucide, CSS and GSAP; no added dependencies.

**Spec:** User's 2026-10-18 UI reconstruction brief and attached topmost “方案一 · 现代日历工作台”.

## Constraints and decisions

- Keep navigation in Shell; use existing theme tokens and font.
- Stats: today's scheduled daily tasks, current Monday–Sunday scheduled daily tasks, active long-term goals. No completion-history field: streak displays 暂无记录.
- Progress counts direct linked children. No children: 暂无关联任务, zero-width bar.
- Undated tasks remain in the central scope list and are excluded from calendar/date totals. Search filters both lists; statistics remain whole-data totals.
- Month navigation clamps month-end days. Local calendar construction and comparisons never use UTC date keys.
- Current-week focus includes weekly plans dated this week or with linked daily tasks dated this week. No invented schedule.
- ≥1024px three columns; 768–1023px two columns with goals below; ≤767px one column. Narrow cards remain readable.
- Reuse existing Modal and motion preference. Native controls retain keyboard access and visible focus.

## Tasks

- [x] Add failing date/aggregation tests covering year boundaries, February, local midnight, undated tasks, direct parent progress.
- [x] Implement `plan-utils.ts` and run the focused tests.
- [x] Add failing page tests covering search, date views, CRUD payloads, parent relationships, synchronized panels/cache, server errors.
- [x] Implement calendar, statistics, task rows/form, progress cards and page orchestration. Scope CSS to plans and its dialog.
- [x] Run frontend suite, typecheck, lint and production build; fix regressions within scope.
- [x] Run local preview and browser interactions; capture desktop, tablet, mobile and dark/reduced-motion states. Compare reference topmost content against actual desktop screenshot. Record evidence and limitations in a dedicated plans QA report.

## Review focus

- Local midnight / DST and year-crossing weeks must retain dates.
- Empty and undated datasets must not yield fake percentages or schedules.
- Scope/parent changes must not produce invalid relationships.
- Failed mutations retain drafts and announce errors; successful writes refresh both query keys.
- Shared task appears in calendar and list; toggles and deletes update both.

## Validation ledger

- Initial workspace: no tracked changes; existing untracked `ort` left untouched.
- Task fields lack completion history, descriptions, priorities, categories and duration. No schema extension planned.
- Existing dependencies include GSAP and Lucide. React Bits references reviewed: Animated List, Spotlight Card and Count Up. Animated Tabs URL unavailable; implement small local sliding indicator using existing CSS capability.

- Final verification: 44 frontend test files / 186 tests passed; complete ESLint and production build passed. Build retains its pre-existing >500kB chunk warning.
- Browser: 25 assertions across eight widths, dark/light, normal/reduced motion, CRUD, keyboard, empty/error states; no page runtime errors. Evidence in docs/audit/plans-calendar-workbench-2026-10-18.md.
- Review found null-parent fallback and mixed-child filter issues; both reproduced by failing tests and corrected. No schema, package, Shell or API changes.
