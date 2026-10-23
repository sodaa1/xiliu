# 2026-10-23 UI 主干集成验证

## 提交范围

- 首页、侧栏与跨页控件统一；知识库紧凑分类；Inbox / 资讯网格与分栏阅读。
- UI 控件覆盖映射和最近界面截图。
- README.md、README.zh-CN.md、README.en.md 同步更新，旧的小版本更新列表改为 Releases 链接，仅保留最近一次更新。
- 本次没有修改 API 客户端的请求路径、方法、DTO 或后端实现；原目录已有的后端 / Runtime / RAG 修改与研究资料不纳入此次提交。

## 主干与接口核对

远端 `main` 的基线为 `3de61d2b10ee3b486294a276e404f589f8f50c9b`（v0.4.5），与 UI 分支原基线相同。本地 `main` 原本落后 14 个提交，将通过快进保留已有云端和桌面历史，无须覆盖主干代码。

在独立检出中验证主干后端加本次 UI：

| 检查 | 结果 |
| --- | --- |
| 完整 Python 回归 | 931 passed / 1 skipped，约 254 秒 |
| 完整前端回归 | 258 passed / 0 failed |
| ESLint | 通过 |
| 正式应用与介绍页构建 | 通过；保留既有大包提示 |
| UI / App Action 静态审计 | 1092 surfaces / 0 errors |
| 本地未提交后端的相关 API 回归 | 38 passed，覆盖 Feed、Knowledge/Inbox、会话、任务及 Web 修复 |

结果文件为 `merge-backend-results.xml`、`merge-frontend-results.json` 和 `merge-surface-results.json`。静态映射不代表每个 Agent 路径已端到端运行；未调用真实外部模型，未重新打包或发布 Windows 安装包。

## Git 与署名

提交作者与提交者均使用用户确认的 `sodaa1 <soda933693@163.com>`，不添加 AI 共同作者。仅暂存经过审查的 UI、README 和验证文档。原工作区中其他改动保留，不使用全目录 add 或破坏性 reset。

正常完成流程为：提交 UI 分支 → 在独立检出快进合并到 main → 核对提交树及远端 main → 普通推送 main（不强推）。Git HTTPS 在此机器需使用命令级 `http.sslBackend=schannel` 才可连接；没有关闭 TLS 验证或改写全局网络设置。
