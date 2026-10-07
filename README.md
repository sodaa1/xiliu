# 息流 · xiliu

本地优先的个人信息与 AI 助手。React + FastAPI 薄层直接调用原 Runtime。

当前实现：Phase 0–4（模型设置、多会话 Assistant、四个斜杠命令）。后续内容模块尚未开放。

## 运行

```powershell
uv sync --dev
cd web
npm ci
npm run build
cd ..
uv run xiliu web --open
```

Windows 可双击 `start-xiliu.bat`。默认 http://127.0.0.1:8765 。开发前端：`cd web; npm run dev`，API：`uv run xiliu web`。

本地 `.env` 使用 `XILIU_API_KEY`、`XILIU_MODEL`、`XILIU_BASE_URL`、`XILIU_PROVIDER`、`XILIU_DATA_DIR`，参考 `.env.example`。原配置已备份，绝不提交。

[架构树](docs/ARCHITECTURE.md) · [阶段记录](docs/PHASES.md) · [原设计](docs/reference/息流_UI_v0.1_技术方案.md)

```powershell
uv run python -m pytest
uv run ruff check src tests
cd web
npm test -- --run
npm run lint
npm run build
```

源内核来自 [sodaa1/xiliumini](https://github.com/sodaa1/xiliumini)，基线 `6d3689583f93b3fafd6381b2b65c31d9613464e5`；Web 适配与品牌按用户要求使用 xiliu。
