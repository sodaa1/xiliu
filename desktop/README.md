# 息流 Windows 桌面

Tauri 2 管理窗口和自己启动的 Python 服务，业务复用 FastAPI / Runtime，生产前端由该本机服务提供。窗口初始 1440×900，最小 1100×720。

## 安装与首次配置

当前本地安装包为 `dist/Xiliu-0.4.4-x64-setup.exe`，附带 SHA256 校验文件。本次内核与模型设置更新见 [0.4 发布验证](../docs/architecture/graph-v2/release-0.4.md)，历史安装证据见 [Windows 交付记录](../docs/WINDOWS_RELEASE.md)。双击后使用中文向导安装。

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

### 桌面伴侣

Today 首页默认展示内置背景和正常比例角色，保留已有用户的背景选择。独立桌宠的 Q 版默认 96 个逻辑像素高，常规形象默认 168 像素高；“设置 → 外观 → 桌面伴侣”分别保存两种形态的 100%、125%、150%、175%、200% 比例，也可切换置顶或停用。旧像素设置迁移到最近的可用比例。

拖动角色可移动桌宠，拖动期间隐藏下方按钮。Q 版悬提左右摆动；常规形象轻微倾斜，发梢、裙摆按实际移动产生惯性，手部、前臂与面部不参与局部拉伸，松手后平滑复位。减少动态效果时保持静止悬提。图形渲染不可用时保留原始图片。角色下方为新对话、Inbox、更多三个图标；更多中可切换形态、返回工作台或打开外观设置。点击新对话展开横向输入框，Esc 收起并保留草稿。进展气泡来自实际对话状态，点击进入对应会话。后台快捷对话不会切换主窗口当前正在编辑的会话。

启用桌宠时，关闭主窗口会隐藏到托盘，对话与本地服务继续运行；托盘提供显示/隐藏桌宠、收录和“退出息流”。停用桌宠后恢复关闭主窗口即退出的行为。桌宠位置、大小与启用偏好保存到应用数据目录的 `companion.json`。

独立收录窗关闭后保留当前会话内草稿；文字草稿另存当前窗口的 sessionStorage，可在页面重载后恢复。退出整个应用不保证保留未提交的文件或窗口会话。保存期间禁止编辑，失败保留内容，成功后可继续收录；“查看内容”直接定位已保存条目，即使后台规则已将其归类到 Knowledge。

当前默认形象使用已确认的透明 PNG，拖动反馈为整体悬提摆动。两种形态均有局部表情：待机偶尔眨眼和微笑，悬停短暂微笑后恢复待机，展开对话时保持微笑，拖动时小惊讶；只替换脸部区域，避免身体切图跳动。减少动态效果或页面不可见时暂停自动表情。Live2D 本地模型导入与延迟渲染已接入；拆层、Cubism 建模、动作文件和许可允许的 Cubism Core 仍需提供，未导入时保留 PNG，不声称已提供角色变形动画。

桌面数据位于 `%APPDATA%\io.xiliu.desktop`，不会覆盖开发 `.xiliu/`。模型设置保存到该目录的 `.env`，用户自行配置；外观、个人信息和侧栏偏好由 bridge 持久化，避免随机端口改变造成偏好丢失。备份时退出应用并复制完整数据目录。

服务绑定 `127.0.0.1` 的随机空闲端口，启动完成输出 ready，桌面壳用私有令牌验证后进入工作台。验证就绪后，仅向本次服务端口授予按主窗口、桌宠、收录窗口划分的命令权限；桌宠与收录窗口限制为各自页面路径。日志不打印令牌。运行日志为数据目录下的 `logs/service.log`，超过 2 MB 轮换到 `service.previous.log`。

退出应用时先请求后端退出并关闭自身 stdin，最多等待 30 秒后只回收自己启动的子进程。壳意外退出导致管道 EOF，服务也会退出。初始提示页之后保留原银河开场与业务界面。

## 验证与排错

真实冻结服务烟雾验证使用临时资料和空模型配置：

```powershell
.venv/Scripts/python.exe scripts/verify_desktop_service.py .preview/desktop-sidecar/xiliu-service/xiliu-service.exe --report logs/development/desktop-service-02-proof.json
```

覆盖 ready / 令牌、前端、介绍页、知识写入检索、无 API Key、关闭与端口释放。遇到启动错误，查看数据目录 `logs/service.log`；构建错误查看 `logs/development/`。冻结服务通过不等于桌面安装验收通过，最终状态见交付记录。

官方参考：[构建前提](https://v2.tauri.app/start/prerequisites/)、[Windows NSIS](https://v2.tauri.app/distribute/windows-installer/)、[sidecar](https://v2.tauri.app/develop/sidecar/)。
