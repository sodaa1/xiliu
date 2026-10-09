# 息流 Windows 桌面

Tauri 2 管理窗口和自己启动的 Python 服务，业务复用 FastAPI / Runtime，生产前端由该本机服务提供。窗口初始 1440×900，最小 1100×720。

## 安装与首次配置

当前本地安装包为 `dist/Xiliu-0.3.0-x64-setup.exe`，附带 SHA256 校验文件。0.3 更新及验证边界见 [修复记录](../docs/XILIU_03_FIXES.md)，历史安装证据与当前产物见 [Windows 交付记录](../docs/WINDOWS_RELEASE.md)。双击后使用中文向导安装。

用户不需要 Python、Node.js 或 Rust。需要 WebView2，缺少时安装向导下载运行时。首次启动在设置中自行填写模型 API 地址、模型和 API Key。包内不包含开发者 `.env`、密钥、个人模型配置或用户资料。

## 从源码构建

需要 Python 3.12+、uv、Node.js / npm、Rust 的 `x86_64-pc-windows-msvc` 工具链，以及 Microsoft C++ Build Tools 的 C++ 工具和 Windows SDK。

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

已有依赖时可添加 `-SkipDependencyInstall`。脚本发现 `.preview/toolchain/cargo` 时，仅为当前进程启用项目内 Rust；常规安装的 Rust 也可直接使用。

构建分为前端、Python 服务、Tauri / NSIS 三步。原始安装包生成在 `desktop/src-tauri/target/release/bundle/nsis/`，脚本复制到 `dist/` 并生成 SHA256。Rust 依赖通过 `Cargo.lock` 锁定，生成后保留在源码中。

也可分步执行：

```powershell
uv sync --dev --group desktop
cd web
npm ci
npm run build
cd ..
uv run --group desktop python desktop/build_sidecar.py
cd desktop
npm ci
npm run build
```

开发桌面使用 `npm run dev`，仍须先生成 sidecar。

## 包含的资源

- 桌面壳与启动提示页。
- 编译后的前端 HTML、JS、CSS、字体和图像。
- 冻结的 API、Agent 内核、RAG 和必要运行依赖。
- 依赖需要的元数据、schema、证书、时区与许可证。

不包含项目 README / docs、测试源码、测试框架、开发工具、source map、CLI / TUI、构建日志或配置密钥。PyInstaller 使用 onedir，避免每次启动解压大型 onefile；`binaries/` 由脚本生成，不进入 Git。

冻结服务提供应用业务运行环境，不作为独立 Python 命令行解释器。Code Agent 的 Python 脚本与测试执行请使用源码开发环境；外部 MCP 服务的运行工具也需另行准备。

## 数据与生命周期

桌面数据位于 `%APPDATA%\io.xiliu.desktop`，不会覆盖开发 `.xiliu/`。模型设置保存到该目录的 `.env`，用户自行配置；外观、个人信息和侧栏偏好由 bridge 持久化，避免随机端口改变造成偏好丢失。备份时退出应用并复制完整数据目录。

服务绑定 `127.0.0.1` 的随机空闲端口，启动完成输出 ready，桌面壳用私有令牌验证后进入工作台。日志不打印令牌。运行日志为数据目录下的 `logs/service.log`，超过 2 MB 轮换到 `service.previous.log`。

关闭窗口先请求后端退出并关闭自身 stdin，最多等待 30 秒后只回收自己启动的子进程。壳意外退出导致管道 EOF，服务也会退出。初始提示页之后保留原银河开场与业务界面。

## 验证与排错

真实冻结服务烟雾验证使用临时资料和空模型配置：

```powershell
.venv/Scripts/python.exe scripts/verify_desktop_service.py .preview/desktop-sidecar/xiliu-service/xiliu-service.exe --report logs/development/desktop-service-02-proof.json
```

覆盖 ready / 令牌、前端、介绍页、知识写入检索、无 API Key、关闭与端口释放。遇到启动错误，查看数据目录 `logs/service.log`；构建错误查看 `logs/development/`。冻结服务通过不等于桌面安装验收通过，最终状态见交付记录。

官方参考：[构建前提](https://v2.tauri.app/start/prerequisites/)、[Windows NSIS](https://v2.tauri.app/distribute/windows-installer/)、[sidecar](https://v2.tauri.app/develop/sidecar/)。
