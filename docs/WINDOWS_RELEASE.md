# 息流 Windows 交付记录

日期：2026-10-09。目标为 Windows x64 的中文 NSIS `.exe` 安装包。

## 当前版本：0.3.0

产物：`dist/Xiliu-0.3.0-x64-setup.exe`，38,696,736 字节（约 36.90 MiB），同目录保留 `.sha256`。

```text
37757bbfdb48f1b269eba1f08956efd087e7f3783c156903d0354a1babd8a759
```

0.3 新增应用写入工具、多会话与取消、布局调整、思考流与模型连接处理、公开 AIHot MCP 默认配置。历史来源与冻结服务报告验证 owner 令牌、生产资源、未配置 API Key、Knowledge、配置后聊天 / 思考、MCP 默认配置、正常关闭及 EOF 退出；浏览器报告验证布局、多聊天、按会话停止、HTML5 文件导入和资讯刷新。详见 [0.3 修复记录](XILIU_03_FIXES.md)。

本次文档更新重新核对了现有安装包字节数与 SHA256，并对主干源码重新执行 124 后端 / 33 前端回归、静态检查和前端构建；未重新生成安装包，也未使用真实模型密钥。原生桌面窗口拖入及缺少 WebView2 时的下载流程尚未交互式验证。

当前 main 只包含已交付的 0.3 基线；天气搜索循环和桌面检查点的新修复在 `codex/fix-desktop-search` 独立分支处理。下文为 0.2 历史安装证据，不作为全部 0.3 新行为的验收。

## 历史版本：0.2.0

## 构建链

React / Vite → PyInstaller onedir 服务 → Tauri 2 桌面壳 → NSIS 安装包。

用户无需开发工具。服务监听随机本机回环端口，桌面壳持有私有令牌与子进程，关闭窗口时回收自身服务。

本次补齐 Rust MSVC 和 Microsoft C++ 构建工具。Rust 位于项目 `.preview/toolchain/`，不修改持久 PATH；Microsoft 安装程序会注册构建组件与 Windows SDK。

## 产物与验证

已通过完整发布脚本构建、实际静默安装、安装后服务验证及桌面启动 / 关闭验证。测试安装清理后，交付文件保留在 `dist/`。

交付路径：`dist/Xiliu-0.2.0-x64-setup.exe` 与同名 `.sha256`。

安装包大小：38,323,101 字节（36.55 MiB）。SHA256：

```text
c4bf2e93933f3302e8736a4850e1174a44c6157c8d7cc83184ecf68d73c2ff5e
```

本次实际证据（日志与报告仅本地保留，不进安装包）：

| 检查 | 结果与证据 |
| --- | --- |
| 完整构建 | `scripts/build-windows.ps1 -SkipDependencyInstall` 退出 0；前端、PyInstaller、Rust release、中文 NSIS 均成功。见 `logs/development/windows-release-build.log`。 |
| 资源精简 | 冻结模块不含测试框架、开发工具、终端界面；资源不含项目文档、配置、数据库、日志或 source map。保留必要许可证；见 `desktop-package-audit.json`。 |
| 实际安装 | 在项目临时目录安装，退出 0；服务哈希一致，桌面壳除 Tauri 正常写入的 NSIS 类型标记外与构建文件逐字节一致。见 `desktop-install-integrity.json`。 |
| 安装后服务 | 私有 ready 令牌、前端与介绍页、本地资料写入检索、API Key 未配置、正常退出、stdin EOF 退出及端口释放均通过。见 `desktop-installed-service-proof.json`。 |
| 桌面壳启动 | 实际窗口与 WebView2 子进程出现，本机业务服务启动并提供生产前端；关闭窗口退出 0，自有服务退出。见 `desktop-shell-proof.json`。 |

安装验收使用本机已有 WebView2，没有验证缺少 WebView2 时的下载流程，也没有请求真实模型 API。安装资源仅约 49.11 MiB 的运行依赖与前端，另外包含桌面壳、冻结服务和卸载程序。

## 复现

准备 Python 3.12+、uv、Node.js / npm、Rust MSVC 和 Microsoft C++ Build Tools，运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

已有依赖时可添加 `-SkipDependencyInstall`。脚本自动发现本机项目内 Rust 工具链。构建日志放在 `logs/development/`；运行日志位于 `%APPDATA%\io.xiliu.desktop\logs\service.log`。

## 分发内容与边界

安装包只分发桌面壳、前端构建资源、Python 核心业务代码与运行依赖。显式排除测试框架、开发工具和桌面不用的 CLI / TUI。项目 README、docs、测试、日志、源码仓库、开发者 `.env`、密钥和用户资料均不包含在包内。运行依赖需要的元数据、时区、证书及 schema 资源保留。

用户首次启动自行配置模型 API。安装目录与数据目录分离，开发 Web 资料仍留在 `.xiliu/`。

缺少 WebView2 时安装引导程序需要联网。当前没有代码签名证书；生成安装包不代表已完成签名或公开发布。其他 Windows 设备兼容性仍需验证。

官方参考：[Windows 构建前提](https://v2.tauri.app/start/prerequisites/)、[NSIS 安装包](https://v2.tauri.app/distribute/windows-installer/)。
