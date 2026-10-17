# 网页试用部署评估

评估日期：2026-10-16。工作分支：`codex/web-demo-deployment`。

已实现静态游客演示，以及网页和桌面共用的首次功能导览。按最新需求，应用不再提供独立 Wiki 页面。2026-10-17 已通过 GitHub Pages 发布：[在线体验](https://sodaa1.github.io/xiliu/#/today)。真实 AI、账号登录及网页/桌面数据同步仍属于后续改造。

## 已实现：构建与预览演示版

在项目根目录执行：

```powershell
npm --prefix web ci
npm --prefix web run build:demo
npm --prefix web run preview:demo
```

打开 `http://127.0.0.1:5184/today`。演示版不需要 Python、登录或 API Key；使用 IndexedDB 保存此浏览器中的演示资料，存储不可用时提示仅当前页面保留。页面顶部可以确认后重置。

- 首次进入工作台自动显示功能导览，以遮罩高亮实际入口；支持上一步、下一步、跳过和完成，结束后回到原页面，刷新不再自动重复。
- 可以收藏资讯、编辑标签、归档与检索、操作计划、创建会话并体验带引用的本地模板回复。
- 助手明确标为“演示回复”；实时资讯、真实模型、文件上传/解析、自动任务、外部工具和原生桌宠只提供说明。
- 左下角问号可以重新播放导览。步骤与简介位于 `web/src/features/onboarding/steps.ts`，网页和桌面共享；已经安装的桌面包需要更新到包含本次构建的版本。

## 静态发布步骤

### GitHub Pages 自动发布

仓库提供 `.github/workflows/demo-pages.yml`：向 `main` 推送相关网页改动，或手动运行该工作流时，构建并发布 `web/dist-demo/`。首次需要在仓库 Settings → Pages 中将来源设为 GitHub Actions。

当前仓库已启用 GitHub Actions 来源。首个发布提交为 `1e23279`，[部署工作流](https://github.com/sodaa1/xiliu/actions/runs/39010562627) 构建和发布成功；公网完成 22 项浏览器检查，见 [验收记录](audit/github-pages-demo-2026-10-17.json)。

工作流读取 Pages 的实际部署路径，并设置 `VITE_DEMO_ROUTER=hash`，使仓库子路径（例如 `/xiliu/`）下的字体、背景和角色图片正常加载；分享链接形如 `/xiliu/#/today`，刷新无需服务器重写。默认本地演示与桌面版继续使用原有路由。

本地复验 Pages 构建：

```powershell
$env:VITE_DEMO_ROUTER='hash'
npm --prefix web run build:demo -- --base=/xiliu/
Remove-Item Env:VITE_DEMO_ROUTER
```

将产物放在静态服务器的 `/xiliu/` 目录，再执行 `node scripts/qa/web-demo-pages.cjs`。默认验收地址为 `http://127.0.0.1:5185/xiliu/`；可通过 `DEMO_URL` 和 `DEMO_REPORT` 指定公网地址与结果文件。检查包括直接打开和刷新主要页面、首次引导、手机尺寸、资源加载及演示不请求真实 API。

### 其他静态托管

1. 执行上面的 `build:demo`，发布目录为 **`web/dist-demo/`**。不要把项目根目录、`.env`、数据库或正常构建目录当作发布内容。
2. 将该目录中的文件上传到支持 SPA 的静态托管，或放到现有 Nginx 静态目录。首次采用独立子域名的根路径，例如 `demo.<你的域名>`；资源路径按根路径构建。
3. 配置未命中文件的路径回退到 `/index.html`。产物自带 `_redirects`，支持该格式的平台可识别 `/* /index.html 200`；其他平台需在控制台或服务器配置等效规则。
4. 如果使用 Nginx，静态站点的 location 使用下列规则，并为该域名配置 HTTPS：

   ```nginx
   location / {
       try_files $uri $uri/ /index.html;
   }
   ```

5. 验证 `/today`、`/assistant` 直接打开和刷新均正常，新浏览器首次进入时显示导览，跳过或完成后不再弹出，且浏览器网络面板没有 `/api` 请求，再把介绍站的“在线体验”入口链接到新地址。

演示不需要反向代理到现有本机 FastAPI，也不需要开放其端口。静态上线无需修改后端的本机访问保护。当前已发布到 GitHub Pages 默认域名，尚未绑定自定义域名。

本机已经有 Playwright 和 Edge 时，可在预览运行期间执行 `node scripts/qa/web-demo-guide.cjs` 复验主要流程。`PLAYWRIGHT_MODULE` 可指定 Playwright 包路径，`DEMO_URL` 可覆盖预览地址，`BROWSER_CHANNEL` 可选择已安装的浏览器；脚本不会安装依赖或下载浏览器。

## 结论

息流可以提供网页版试用。现有 `web/` 已是 React + Vite 应用，FastAPI 可以同时提供 `/api` 与构建后的网页，无需重写整套界面。Tauri 是 Windows 桌面外壳，网页服务不需要它。

正常应用仍面向本机单用户，不能直接当作公开多人服务上线。此次用独立静态演示满足“首次体验后决定是否安装”的目标，真实 AI 体验按下文另行改造。

## 源码依据与部署障碍

| 项目 | 现状 | 对公网部署的影响 |
| --- | --- | --- |
| 网页与 API | `web/` 调用同源 `/api`；`src/xiliu/api/app.py` 提供静态网页 | 可以采用一个域名提供前后端 |
| 启动地址 | `src/xiliu/cli/__init__.py` 中 `xiliu web` 固定监听 `127.0.0.1` | 当前命令仅供本地使用 |
| Host / Origin | `create_app()` 的 `local_origin` 中间件只接受 loopback 主机和写请求来源 | 只改变监听地址仍无法正常通过公网域名使用 |
| 资料与聊天 | `AppStore` 使用一个数据目录的 `app.sqlite3`，列表和查询未按访客身份隔离 | 多人共用实例会共用资料与会话；聊天 ID 不等于用户身份 |
| 模型设置 | 全实例共享 `ModelSettingsService`，设置接口可写入服务端配置文件 | 公开试用应由管理员管理模型，阻止访客修改配置 |
| Agent 能力 | 内核包含文件、进程执行、Code Agent、Skill / MCP 与自动任务 | 公开体验需要服务端能力白名单和运行隔离；仅隐藏按钮不足以限制调用 |
| 流式聊天 | 浏览器读取 NDJSON 响应 | 反向代理应避免缓存整个聊天响应，并设置合适的超时 |
| 桌面能力 | `web/src/desktop/bridge.ts` 检测 Tauri 环境 | 普通网页可复用主界面，原生窗口、独立桌宠等能力需隐藏或说明 |
| 介绍站 | `docs/web/` 已支持独立静态构建 | 现在就能部署介绍页，但它不是完整应用试用版 |

## 选择哪种试用方式

| 方式 | 访客体验 | 需要的部署 | 适用阶段 |
| --- | --- | --- | --- |
| 现有介绍页 | 看产品介绍与示例界面 | 静态托管 | 立即对外介绍 |
| 游客演示版（本分支已实现） | 浏览预置 Feed、收集示例资料、归类、检索、体验预设问答流程 | 纯静态托管 | 首次体验，免安装、免配 Key |
| 真实 AI 试用 | 输入自己的问题，获得真实模型回复 | 隔离后的后端、模型额度与运行维护 | 需要验证 AI 效果时 |
| 完整云端版 | 长期保存个人资料、跨设备使用 | 账号、授权、用户数据隔离、备份与完整运维 | 已决定提供云端产品时 |

正常前端 `web/dist/` 继续依赖真实 API；只有独立构建的 `web/dist-demo/` 使用演示数据层。修改正常页面功能时，需要同时检查演示请求处理器是否覆盖新增能力。

## 后续上线安排

1. GitHub Pages 演示已发布；按需绑定自己的域名，或按上文迁移到其他静态托管。
2. 确认体验地址和实际可用的安装包地址，再更新介绍站的体验/下载入口。
3. 有必要时再接入限额真实 AI：访客会话隔离、服务端配额、超时与成本上限先落地，再开放模型请求。

静态演示无需持续运行 Python 服务，也没有按模型调用产生的费用；托管费用取决于所选平台和流量。

## 现有代码现在如何运行

在项目根目录执行以下命令，只会启动本机网页，不会部署到公网：

```powershell
uv sync --locked --no-dev
npm --prefix web ci
npm --prefix web run build
uv run xiliu web --open
```

默认入口是 `http://127.0.0.1:8765`。这是验证网页功能和准备演示内容的方式。

如果只发布现有介绍页：

```powershell
npm --prefix web ci
npm --prefix docs/web run build
```

发布 `docs/web/dist/` 中的静态文件。现有文档说明它可以复制到个人网站的 `public/projects/xiliu/`；实际上传方式取决于个人网站当前使用的托管服务。

## 真实 AI 试用版如何部署

如果选择真实 AI，建议采用：浏览器 → HTTPS 反向代理 → Python 应用容器。模型 API 由服务端调用。起步可以使用单台 Linux 云服务器和 Docker Compose，不需要先引入 Kubernetes。

上线前需要完成以下应用改造：

- 将本地模式与公开试用模式明确区分。公开模式使用配置的精确 Host 和完整 Origin 白名单（协议、域名、端口），并保留来源校验；不要直接删除现有中间件或通过改写请求头绕开它。
- 生成服务端可校验的访客身份，在所有资料、附件、聊天、任务、后台作业和流式请求中检查归属。可以采用有访问控制的每访客独立实例与数据目录，或完整的多租户数据层；只给聊天增加访客字段不够。
- 锁定模型配置与 API 地址，禁止公开访客修改服务端 Key、任意 API 地址和管理员配置。Key 不进入前端构建产物。
- 为游客启用最小能力白名单；默认关闭命令执行、Code Agent、任意 MCP / Skill 扩展和长期自动任务。限制上传、导入与对外请求的范围。
- 设定单访客请求额度、并发和 token 上限、全站成本上限、过期清理规则；限额由服务端执行。

完成上述改造后，再按下面顺序部署：

1. 构建前端：Node 构建阶段包含 `web/` 和 `docs/web/`，因为应用构建会调用介绍站脚本。
2. 构建 Python 3.12+ 运行镜像，安装锁定的运行依赖，包含 `src/` 和 `web/dist/`；前端资源放在 `create_app()` 能找到的位置，或通过应用工厂明确指定 `static_dir`。
3. 使用干净的服务端配置和数据目录。构建上下文排除 `.env*`、个人 `.xiliu/` 数据、备份、日志、虚拟环境、桌面产物和开发资料；需要的能力模板单独选择打包。
4. 对需要保留的数据挂载持久卷；临时游客数据使用独立目录并按期限清理。容器以非 root 用户运行，不挂载宿主机敏感目录或 Docker socket。
5. 容器内可以使用下列应用工厂入口。此命令本身不会解除当前源码的本机访问限制，必须先完成公开模式改造：

   ```sh
   uv run --no-sync uvicorn xiliu.api.app:create_app --factory --host 0.0.0.0 --port 8765 --workers 1
   ```

6. 反向代理提供域名与 HTTPS，后端端口只向代理开放。前端和 API 保持同源；Nginx 对聊天流设置 `proxy_buffering off`，并根据模型耗时设置读取超时。
7. 先采用单应用进程，验证后台调度、流状态和取消请求，再考虑扩容。当前不能假定任意多进程部署都能共享运行状态。
8. 用两个独立浏览器验证资料与会话隔离、越权拒绝、额度生效、流式回复和停止、过期清理、容器重启后的预期状态，再对外发布体验入口。

上述容器与代理配置仍需实现和实测，本文不表示已有可直接执行的公网部署包。服务器资源应根据少量并发试用测量决定；使用远程模型时不需要为模型推理购买 GPU。

## 官方部署参考

- [FastAPI：Docker 容器部署](https://fastapi.tiangolo.com/deployment/docker/)
- [Uvicorn：应用工厂、监听地址与端口](https://uvicorn.dev/settings/)
- [Nginx：反向代理与响应缓冲](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
