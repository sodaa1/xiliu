# Package size and startup: measured before/after

Both actual NSIS installers were extracted with 7-Zip. Deployment excludes installer-temporary $PLUGINSDIR, registry and generated uninstall registration. Registered Windows installation and WebView2 GUI: not_run.

Old 0.3.2 is the existing release artifact, not an independently reconstructed dependency cache; total differences cannot be attributed entirely to one dependency trim.

| Metric | Before | Final 0.4.0 | Delta |
|---|---:|---:|---:|
| Installer bytes | 38,746,721 | 38,514,440 | -232,281 |
| Deployment bytes | 81,369,464 | 80,876,074 | -493,390 |
| Deployment files | 864 | 858 | -6 |
| Sidecar bytes | 70,968,696 | 70,475,306 | -493,390 |
| Sidecar files | 863 | 857 | -6 |

Final installer SHA256: `a861242b0340d53bd155a3fbb9454834a52caf3931f44b5a32c7ef5acbdfe5d1`.
Frozen executable SHA256: `c1fdf8e44dc41a703451b815fc7c5d33669f4a7c60c643eaec748c6e4b14c4a0`.
Old installer SHA256: `fe4a45f399ea4a2f5e2160194d1059ed9049acb14429015ca399b9f4823bbeb2`.

## Startup / memory

Three fresh disposable-data launches per artifact; 10 persisted Task create/complete/delete cycles each; provider keys stripped. No disk cache flush, so these are process samples, not guaranteed cold disk timings. All exited 0.

| Run | Before ready ms | After ready ms | Before working set bytes | After working set bytes |
|---|---:|---:|---:|---:|
| 1 | 2921.1327 | 2537.3801 | 124,579,840 | 124,993,536 |
| 2 | 2550.5079 | 2310.9670 | 123,969,536 | 125,087,744 |
| 3 | 2632.5138 | 2364.0369 | 124,039,168 | 125,370,368 |

Median ready ms: 2632.5138 → 2364.0369.

Raw HTTP timing samples and memory after work remain in startup-baseline.json / startup-after.json. Historical pre-final and pre-AI measurements are explicitly separate.

## Final deployment Top 30

| File | Bytes |
|---|---:|
| xiliu-service.exe | 18,970,157 |
| xiliu-desktop.exe | 10,400,768 |
| _internal/cryptography/hazmat/bindings/_rust.pyd | 9,897,472 |
| _internal/python312.dll | 7,003,928 |
| _internal/web/dist/fonts/xiliu-handwriting.woff2 | 5,432,280 |
| _internal/libcrypto-3.dll | 5,162,776 |
| _internal/pydantic_core/_pydantic_core.cp312-win_amd64.pyd | 5,157,888 |
| _internal/tiktoken/_tiktoken.cp312-win_amd64.pyd | 2,450,944 |
| _internal/sqlite3.dll | 1,500,440 |
| _internal/ucrtbase.dll | 1,362,264 |
| _internal/base_library.zip | 1,332,005 |
| _internal/unicodedata.pyd | 1,137,944 |
| _internal/libssl-3.dll | 790,296 |
| _internal/regex/_regex.cp312-win_amd64.pyd | 726,016 |
| _internal/zstandard/_cffi.cp312-win_amd64.pyd | 667,136 |
| _internal/rpds/rpds.cp312-win_amd64.pyd | 559,104 |
| _internal/zstandard/backend_c.cp312-win_amd64.pyd | 525,312 |
| _internal/jiter/jiter.cp312-win_amd64.pyd | 465,920 |
| _internal/uuid_utils/_uuid_utils.cp312-win_amd64.pyd | 352,256 |
| _internal/web/dist/assets/app-DCf2Tx5d.js | 344,765 |
| _internal/web/dist/assets/index-D25fIHUo.js | 297,939 |
| _internal/yaml/_yaml.cp312-win_amd64.pyd | 253,952 |
| _internal/_decimal.pyd | 253,208 |
| _internal/certifi/cacert.pem | 240,216 |
| _internal/orjson/orjson.cp312-win_amd64.pyd | 224,768 |
| _internal/ormsgpack/ormsgpack.cp312-win_amd64.pyd | 209,408 |
| _internal/pyexpat.pyd | 199,448 |
| _internal/charset_normalizer/md.cp312-win_amd64.pyd | 193,536 |
| _internal/_cffi_backend.cp312-win_amd64.pyd | 181,248 |
| _internal/_ssl.pyd | 177,432 |

Duplicate hash excess: 150,630 bytes; groups and hashes remain in package-after.json.

## Trim and preserved behavior

MCP collection was reduced from the entire package to mcp.client, keeping reachable dynamic imports. Actual frozen stdio initialize/tools/list/tools/call succeeded. Textual remains available to source CLI/TUI and is excluded from the desktop sidecar. TLS/crypto, Python runtime, RAG/tokenizer resources and Chinese fonts were retained; largest necessary files are shown above. No user SQLite, Markdown, credentials or caches were cleaned.

The final extracted executable passed keyless Fast (0 model calls, 3 verified receipts), ordinary SDK with a local provider, real local stdio MCP, Feed→Inbox→Knowledge→Todo→Automation persistence/restart, empty PATH and EOF/private shutdown. See desktop-frozen-app-actions.json. External accounts and registered GUI installation are not claimed.
