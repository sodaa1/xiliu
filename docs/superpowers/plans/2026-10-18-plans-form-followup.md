# Task form and planning semantics follow-up — 2026-10-18

User selected clipboard-954ca8c8-f7be-48c0-a4d0-20e5c4f79704.png as the exact form visual; last two attachments define status pills. Build directly from these sources, retaining unrelated Shell.

- One query supplies calendar, scope lists, statistics and focus panels. Daily date-selected list and its scheduled total share a predicate. Legacy undated records are a separately labelled backlog, never assigned a date. The daily statistic follows selected date and is labelled accordingly.
- Weekly list, weekly statistic and focus use interval-overlapping weekly plans, overdue weekly plans actually completed in the selected week, and unscheduled plans. Chart counts completed weekly plans by actual completed_at in each local weekday; old completion without timestamp remains unknown.
- Add compatible persisted task metadata: starts_at/due_at interval, completed_at, status, category, description, priority, tags, reminder_minutes. Preserve completed bool, parent_id and old API callers. No invented completion history. Backend and demo validation enforce the same rules.
- New task defaults from selected calendar date. Daily date/time controls; week/goal range controls. Parent association and category are separate. Native type/status/priority/category radio groups; tags support Enter/remove; description 500 chars. Reminder is an explicit page-open reminder, not an unsupported OS/background notification.
- Reuse Modal with optional headerContent only; preserve existing consumers. Modal body has 60/40 columns, header icon/title/subtitle, stable footer, and supplied/generated decorative calendar art. Dark, small-screen and reduced-motion support retained.
- Tests: date/aggregate helpers, payloads and validation, migrations and API compatibility, demo persistence, no fake completion history. Then full frontend checks and relevant backend suites; isolated browser CRUD plus screenshot comparison at 1536×1024 and mobile.
