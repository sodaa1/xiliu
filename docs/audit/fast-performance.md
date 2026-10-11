# Final Gateway performance and earlier core baseline

Latest measurements include ExecutionGateway policy/hooks/audit. Source SHA256 fingerprints are in JSON.

## Latest Gateway measurements

Generated: 2026-10-10T14:49:28.868201+00:00

Python 3.12.1; Windows-11-10.0.26100-SP0; 10 samples per scenario/layer.

| Scenario | Items | Layer | p50 ms | p95 ms | First ms | Model / Supervisor |
|---|---:|---|---:|---:|---:|---:|
| inbox.archive_all | 100 | fast | 2334.968 | 3328.813 | 2663.29 | 0 / 0 |
| inbox.archive_all | 100 | chat | 2126.732 | 2420.88 | 2127.027 | 0 / 0 |
| link.folder.workflow | 1 | fast | 182.84 | 269.216 | 178.32 | 0 / 0 |
| link.folder.workflow | 1 | chat | 195.622 | 288.254 | 191.432 | 0 / 0 |

All model calls, Supervisor runtime calls and network attempts: **0**.

Each measured write is new, verified durable state; receipt replay is not timed. Latest Gateway samples cover 100-item Inbox archival and link→folder workflow. The earlier 1000-item full matrix is separately labeled below.

- percentile: nearest rank p95; median p50
- data: fresh disposable SQLite+Markdown copies per operation, outside timing
- cold: app_initialization measures fresh Service/App; first_ms is first observation
- warm: modules imported once; operations use warm interpreter and fresh App/data
- cache: OS cache not flushed; true cold process/import/device latency not measured
- excluded: seeding/copy, assertions, shutdown, HTTP/SSE/browser rendering
- workers: workers not started; synchronous local Service/Dispatcher/Fast/Chat path
- comparisons: independent layers; subtracting medians only estimates overhead
- credentials: empty env file; credential/provider env removed; model/network blocked

Raw samples and separate fresh App initialization timings are in fast-performance.json.
Chat timing includes real conversation reads, user/assistant persistence and in-process event construction. It excludes HTTP/SSE transfer and frontend rendering.

Reproduce this phase: `PYTHONPATH=src python scripts/benchmark_app_fast.py --samples 10 --bulk-sizes 100 --profile gateway`


## Earlier measurements — before Gateway integration

Earlier process loaded Fast before ExecutionGateway integration. Its Fast/Chat data does not prove final Gateway overhead; 1000-item Service is a core-write baseline.

### Earlier full matrix

Generated: 2026-10-10T09:33:56.255342+00:00

Python 3.12.1; Windows-11-10.0.26100-SP0; 10 samples per scenario/layer.

| Scenario | Items | Layer | p50 ms | p95 ms | First ms | Model / Supervisor |
|---|---:|---|---:|---:|---:|---:|
| inbox.archive_all | 100 | service | 1615.542 | 2236.198 | 2236.198 | 0 / 0 |
| inbox.archive_all | 100 | dispatch | 1856.225 | 1956.204 | 1813.421 | 0 / 0 |
| inbox.archive_all | 100 | fast | 1875.935 | 1941.373 | 1941.373 | 0 / 0 |
| inbox.archive_all | 100 | chat | 1885.171 | 1912.426 | 1912.426 | 0 / 0 |
| inbox.archive_all | 1000 | service | 20872.445 | 24364.646 | 23973.286 | 0 / 0 |
| inbox.archive_all | 1000 | dispatch | 23763.906 | 80150.635 | 26860.805 | 0 / 0 |
| inbox.archive_all | 1000 | fast | 22052.355 | 23654.409 | 21773.389 | 0 / 0 |
| inbox.archive_all | 1000 | chat | 22444.757 | 24604.291 | 22268.216 | 0 / 0 |
| link.folder.workflow | 1 | service | 72.543 | 80.979 | 75.267 | 0 / 0 |
| link.folder.workflow | 1 | dispatch | 105.992 | 126.766 | 111.981 | 0 / 0 |
| link.folder.workflow | 1 | fast | 120.9 | 129.733 | 119.491 | 0 / 0 |
| link.folder.workflow | 1 | chat | 142.524 | 160.579 | 137.438 | 0 / 0 |
| feed.create | 1 | service | 6.358 | 8.061 | 6.406 | 0 / 0 |
| feed.create | 1 | dispatch | 20.012 | 24.663 | 21.009 | 0 / 0 |
| feed.create | 1 | fast | 36.179 | 44.739 | 36.303 | 0 / 0 |
| feed.create | 1 | chat | 58.254 | 70.843 | 59.813 | 0 / 0 |
| today.task.create | 1 | service | 6.535 | 17.28 | 6.789 | 0 / 0 |
| today.task.create | 1 | dispatch | 23.434 | 33.01 | 24.309 | 0 / 0 |
| today.task.create | 1 | fast | 36.464 | 48.899 | 35.712 | 0 / 0 |
| today.task.create | 1 | chat | 65.775 | 72.16 | 61.505 | 0 / 0 |
| preferences.update | 1 | service | 8.306 | 20.318 | 7.743 | 0 / 0 |
| preferences.update | 1 | dispatch | 31.702 | 45.175 | 45.175 | 0 / 0 |
| preferences.update | 1 | fast | 61.325 | 70.977 | 70.689 | 0 / 0 |
| preferences.update | 1 | chat | 77.667 | 97.838 | 70.91 | 0 / 0 |
| preferences.read | 1 | service | 2.606 | 3.234 | 2.135 | 0 / 0 |
| preferences.read | 1 | dispatch | 12.467 | 16.536 | 13.574 | 0 / 0 |
| preferences.read | 1 | fast | 26.974 | 29.379 | 27.505 | 0 / 0 |
| preferences.read | 1 | chat | 52.906 | 59.073 | 44.525 | 0 / 0 |
| unknown.clarify | 0 | fast | 8.378 | 11.299 | 10.588 | 0 / 0 |
| unknown.clarify | 0 | chat | 31.242 | 123.065 | 24.17 | 0 / 0 |

All model calls, Supervisor runtime calls and network attempts: **0**.

Each measured write is new, verified durable state; receipt replay is not timed. The 100/1000-item Inbox cases run real local classification and Markdown/SQLite writes. Today uses the shared TaskService, without an inferred date. Unknown commands clarify through Fast/Chat and have no comparable Service action.

- percentile: nearest rank p95; median p50
- data: fresh disposable SQLite+Markdown copies per operation, outside timing
- cold: app_initialization measures fresh Service/App; first_ms is first observation
- warm: modules imported once; operations use warm interpreter and fresh App/data
- cache: OS cache not flushed; true cold process/import/device latency not measured
- excluded: seeding/copy, assertions, shutdown, HTTP/SSE/browser rendering
- workers: workers not started; synchronous local Service/Dispatcher/Fast/Chat path
- comparisons: independent layers; subtracting medians only estimates overhead
- credentials: empty env file; credential/provider env removed; model/network blocked

Raw samples and separate fresh App initialization timings are in fast-performance.json.
Chat timing includes real conversation reads, user/assistant persistence and in-process event construction. It excludes HTTP/SSE transfer and frontend rendering.

Reproduce this phase: `PYTHONPATH=src python scripts/benchmark_app_fast.py --samples 10 --bulk-sizes 100 1000`
