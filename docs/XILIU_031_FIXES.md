# 息流 0.3.1 修复记录

日期：2026-10-09。修复分支：`codex/fix-desktop-search`。基于当前 0.3 工作内容建立独立工作区，原工作区、原分支与原暂存区保留给用户上传；本次不合并或上传。

## 检查结果

- Inbox 导入 URL 时保存链接并用已有分类服务识别元数据，不会先抓取网页正文。因此标签识别不能单独证明搜索代理的连接正常。
- Web 的现有 Tavily 配置已受控验证成功；完整 WebSearchTool 也返回有效来源。桌面使用独立用户配置，未配置 Tavily 密钥，但安装的 SDK 支持 keyless，本机的无密钥请求也成功。此次故障不能只归因于缺少 API Key。
- 北京天气等实时查询没有被识别为外部检索，默认进入 Standard。模型可以反复发现不存在的天气 MCP，而不使用已有的 web_search。
- 子代理的永久失败没有传到父代理；临时搜索错误又在子循环、父循环和任务轮次重复尝试。最终只留下 loop limit 或 model request failed，掩盖了最先发生的搜索错误。
- 旧冻结程序的任务路径在首次检查点保存阶段阻塞，尚未请求模型；仅测试轻聊天不能覆盖该问题。Windows Git 启动及检查点清理已加固，冻结程序和空 PATH 场景均已实际复测。

## 局部修复

| 范围 | 最终行为 |
| --- | --- |
| 天气路由 | 北京天气、上海气温、今天/明天的实时天气进入 Fast 并绑定 web_search。解释、翻译、偏好、本地知识及禁止联网问题不触发新的天气识别规则。 |
| 搜索循环 | 每轮首次搜索失败就退出本轮。Fast 返回失败原因；Standard 仅由外层最多三轮控制重试。限额、认证、禁止访问等永久错误立即结束，新旧委派工具均传递 retryable 与安全错误原因。 |
| 空 MCP 发现 | 外部检索发现空 MCP 后通过相同 Gateway 执行一次 web_search 后备；明确禁止联网或本地知识任务不会自动后备。只记录实际返回的来源。 |
| 取消 | 模型、搜索、后备及委派入口保留取消异常，不把取消当作可重试的网络失败。 |
| 桌面检查点 | Git 优先从 PATH 定位，Windows 可从标准安装目录后备定位。所有 Git 读写使用同一启动层，关闭输入并隐藏子进程窗口。CheckpointError 后不重复执行失败保存，保留正常任务与其他异常的终止保存和 trace 收尾。日志只记录步骤、异常类型及退出码。 |

检查点格式、恢复验证、Git 快照及工具授权机制保持原语义。安装包仍使用本机 Git，不打包用户密钥或数据。

## 验证

- 最终 Python 回归：179 passed，1 skipped；跳过项是既有 Windows 符号链接权限用例。前端：33 passed。
- Ruff、Python 类型检查、前端生产构建及 Windows 原生打包通过。
- 新增本地回归 55 项：搜索 43 项、检查点 12 项。遵照现有上传要求，测试源码保持 Git 忽略，不强制加入上传内容。
- 冻结程序以临时用户数据和本地假模型测试工作流、检查点、思考保存、配置默认值及两种关闭方式，关闭后端口释放。
- 空 PATH 的冻结程序通过标准 Git 安装目录完成快照；无专用天气 MCP、无 Tavily 密钥时，实际搜索北京天气并返回来源，两次模型调用完成一次检索和一次回答。该测试的模型是本地假服务，搜索为实际 Tavily 请求。
- 另一次隔离源码会话复用现有 Web 模型与搜索配置，实际“北京天气如何”返回带来源的回答并保存检查点；没有修改原会话或配置。

本地复验：

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe scripts/verify_desktop_service.py .preview/desktop-sidecar/xiliu-service/xiliu-service.exe --workflow --empty-path --report .preview/frozen-check.json
```

默认冻结检查不使用真实密钥或外部搜索。显式增加 `--live-search` 可执行一次真实 keyless 搜索，模型仍为本地假服务；该检查受网络和 Tavily 服务限额影响。

安装包：`dist/Xiliu-0.3.1-x64-setup.exe`，附带 `.sha256`。本次未替换正在运行的旧安装程序；使用新安装包后，桌面才会运行补丁代码。
