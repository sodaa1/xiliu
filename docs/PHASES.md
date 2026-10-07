# Phase 进度与证据

## Phase 0
- 上游 main：6d3689583f93b3fafd6381b2b65c31d9613464e5。
- .env 已存在；仅读取变量名称、model/data_dir 等非密钥字段；不修改原配置。
- 原始 uv run pytest -q：4 个 collection errors。上游 tests/agent_fakes.py 与 tests/__init__.py 没有包含在版本控制中；受影响：test_automation_runner、test_extension_verification、test_hook_lifecycle、test_scheduler。
- 后续以 python -m pytest 核对路径因素；不重写无关测试。
- 执行决策：在空的用户工作区拉取独立源码后，在 feature/xiliu-web-phase4 工作，不再创建第二份 worktree；用户已要求到 Phase 4 后检查，跳过中途审批。
- 测试文件在上游被 tests/ 忽略；新增本次测试用 git add -f 明确提交，避免扩大 .gitignore 对原仓库的影响。
- 计划与原设计冲突时以现有公共接口最小适配；最后保留工作目录供用户检查。

- python -m pytest 排除入口路径问题后仍有 2 个 collection errors：test_extension_verification、test_hook_lifecycle 均缺 tests.agent_fakes；后续全量验证分别报告原始失败与排除这两文件的结果。
- 本机 Git 无 author identity：本次本地提交显式使用 Codex 自动化身份，不更改全局 Git 配置。

## 用户补充范围
- 全面改名 xiliu：Python 包、CLI、XILIU_* 环境变量、.xiliu 数据目录、Skill 名称。原 .env 备份为忽略的 .env.pre-xiliu.backup，密钥值未变。
- 已授权清理原版测试与过时 specs/plans/PRD；保留当前测试、原始 UI 参考和所有 Runtime 模块。基线问题已记录，不再作为本次测试集的一部分。
- 原始 docs/reference 保持附件原文，仓库 origin 保持上游地址，以便追溯来源。

## Phase 1 完成
- src/xiliu/api：App factory、错误脱敏、模型 catalog、ModelSettingsService；新增 Settings.provider。
- 测试先因缺少 api 包失败，再实现通过：10 passed；Ruff passed；整个 src compileall passed。
- DeepSeek preset 使用本地已配置 deepseek-flash 为 canonical，保留 v4-flash 别名；来源 https://api-docs.deepseek.com/api/responses 。
- 本地配置已迁移 XILIU_*，未进行任何付费 API 调用。
