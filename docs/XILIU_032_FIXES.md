# 0.3.2：指定知识库文件夹的 Agent 操作

0.3.1 已合并至 `main`。本次修复以下任务被误判为只读检索、仅暴露 `knowledge_search` 与 `knowledge_get` 的问题：

> 在知识库创建一个叫面试的文件夹，把指定 GitHub 链接先放入 Inbox 生成标签，再放入知识库；只保存链接，不克隆。

## 原因与改动

- 任务路由未覆盖「创建文件夹」「放入」等表达。现在进入具备应用写入工具的 Standard 流程；URL 中的 `python` 等词不作为编写代码的指令。
- 原有工具只能列出文件夹、自动归类。新增 `knowledge_folder_create`，复用页面的知识库服务；同名文件夹直接复用，并注册 `knowledge.write` 权限。
- `inbox_classify` 接受实际目标 `folder_id`，等待现有 Inbox 后台任务完成，保留其生成的标签后归档。等待有超时与取消检查，人工编辑仍通过修订号保护。
- Planner 使用这些现有应用服务执行操作；验证器核对数据库中的文件夹、原始来源、归档位置和标签，避免仅凭回复判定成功。

原 URL 保存在卡片的 `source` 和 `content` 中，卡片类型为 `link`，没有附件文件或克隆仓库。未指定目标文件夹时，沿用原有自动归类流程。

## 验证与交付

- Python：194 项通过，1 项跳过；前端：34 项通过；Ruff、Pyright、前端 lint 和发布构建通过。
- 使用现有 DeepSeek 配置，在临时数据目录执行用户原句：8 次模型请求后任务通过，实际生成「面试」文件夹和一张已带标签、保留原始链接的卡片，归档位置正确。
- 源码桌面服务和 PyInstaller 冻结服务均通过隔离验收：每轮 6 次本地模拟模型请求、一次工作流尝试；完整检查真实数据库写入、思考流、检查点，以及私有关闭接口和 stdin EOF 两种退出方式。空 PATH 情况下也通过。
- 网页服务已从 0.3.0 重启至 0.3.2，原会话 ID 与模型配置保留。此前运行中的旧服务不会自动加载主干代码修改。

安装包：`dist/Xiliu-0.3.2-x64-setup.exe`，附 `.sha256`。

SHA256：`fe4a45f399ea4a2f5e2160194d1059ed9049acb14429015ca399b9f4823bbeb2`。

复验冻结服务：

```powershell
.venv/Scripts/python.exe scripts/verify_desktop_service.py `
  .preview/desktop-sidecar/xiliu-service/xiliu-service.exe `
  --app-folder --empty-path --report .preview/frozen-032-folder-check.json
```
