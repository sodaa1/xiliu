# 息流介绍网站

网站：<https://933693.xyz/projects/xiliu/>。项目：<https://github.com/sodaa1/xiliu>。

本目录集中维护介绍网站的页面源码、样式、滚动动效、交互检查、图标、概念图和构建脚本。产品应用仍由项目根目录的 `web/` 提供；介绍站复用其锁定的 React、GSAP、Lucide、TypeScript 和 Vite 依赖，无需维护另一套依赖或锁文件。

## 文件

- `index.html`：公开站的入口、描述与 canonical 地址。
- `src/`：React 页面、产品演示、CSS、GSAP 与交互检查。
- `public/`：站点 favicon。
- `assets/`：README 使用的 A 版概念图及原始生成预览。
- `scripts/`：独立开发、构建及检查入口；`scripts/qa/` 为本地浏览器复核脚本。
- `design-qa.md`、`implementation-plan.md`：设计来源和首版验证记录。
- `dist/`：公开发布产物，生成目录，不提交源码仓库。

## 开发与构建

在项目根目录先安装应用前端依赖：

```powershell
npm --prefix web ci
npm --prefix docs/web run dev
```

独立预览地址为 `http://127.0.0.1:5183/`，使用公开展示模式。

```powershell
npm --prefix docs/web run build
npm --prefix docs/web test
```

独立构建输出 `docs/web/dist/`，保持资源相对路径，可复制到个人网站的 `public/projects/xiliu/`。只发布 HTML、favicon 与 assets；不携带应用服务、运行数据或密钥。

应用中的 `/intro/` 也使用本目录的同一份源码：`npm --prefix web run dev` 提供本地介绍入口，`npm --prefix web run build` 生成 `web/dist/intro/`，保留本地工作台链接。公开版本的相关入口改为流程介绍、项目或安装说明。

浏览器复核脚本位于 `scripts/qa/`，需自行提供 Playwright。`PLAYWRIGHT_MODULE` 可指定已有安装路径；`INTRO_URL` 默认是独立预览地址，`BROWSER_CHANNEL` 默认使用 Edge。运行 `node docs/web/scripts/qa/intro-smoke.cjs` 检查滚动、交互及多屏幕布局，截图和报告写入本目录的 `.preview/`。应用构建后可运行 `uv run python docs/web/scripts/qa/intro-production-smoke.py` 检查 `/intro/` 及其静态资源。

## 内容依据

当前文案以项目 [`README.md`](../../README.md)、[`desktop/README.md`](../../desktop/README.md)、[`WINDOWS_RELEASE.md`](../WINDOWS_RELEASE.md) 和 [`XILIU_03_FIXES.md`](../XILIU_03_FIXES.md) 为依据。

- 当前版本 0.3.0；介绍多会话、停止回复、思考过程、中文混合检索与后台 RAG。
- 从源码运行需要 Python 3.12+、uv 和 Node.js / npm；安装命令从克隆 `sodaa1/xiliu` 开始。
- 已有 Windows x64 安装包时可使用中文向导；无需开发工具，需 WebView2。首次启动自行配置模型连接和 API Key。
- 2026-10-09 核对 GitHub Releases 未发现公开安装资产，因此网页不放虚构的 `.exe` 下载地址。发布新 Release 后，需同步核对资产和版本再改下载入口。
- 数据保存在本机；本地模型、远程模型和联网工具的运行条件分别说明。停止回复不撤销已经完成的操作。

## 设计

延续用户选定的 A 版及 Refero / Steep 的白底编辑式排版、黑色胶囊和单处蜜桃重点区。手机和减少动态模式保持静态可读内容；示例 UI 不调用模型或写入用户资料。
