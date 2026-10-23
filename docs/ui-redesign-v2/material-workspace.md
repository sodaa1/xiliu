# Inbox 与资讯：紧凑网格 → 分栏阅读

视觉目标直接采用用户提供的阅读截图，以及已确认的知识库紧凑网格。

| 决策 | 依据 | 实现 |
| --- | --- | --- |
| 默认横排卡片，打开后左侧连续列表 | 用户截图及交互要求 | 两页均根据阅读状态切换布局，关闭回到浏览视图 |
| 顶部工具区约 25% | 用户空间比例要求 | 1440×960 实测 Inbox 内容区域从 y=202 开始，资讯从 y=234.5 开始；包含演示状态条 |
| 紧凑卡片 | 用户要求约缩小一半 | Inbox 约 254×230，资讯约 254×250；响应式自动增加列数 |
| 固定阅读区，贴齐右侧与底部 | 用户尺寸一致要求 | 左列固定 320px；右列填充剩余空间，正文独立滚动；切换两篇资讯右区均为 x=384、width=1056、bottom=960 |
| 窄屏单独阅读 | 保留可用阅读宽度 | 隐藏左列，提供返回按钮，无页面水平溢出 |

共同样式集中于 `web/src/styles/material-workspace.css`，移除旧版 grid 打开后隐藏队列的分支。知识库继续使用现有资料库布局和紧凑弹窗。

验证：完整前端回归 258/258 通过；补充返回网格和删除当前阅读内容的断言后，Inbox 相关 5/5 再次通过；ESLint、格式检查、TypeScript 与演示构建通过。构建仍有既有的包体积提示。动作静态审计 1099 个界面项、0 错误，不代表 Agent 端到端测试已运行。浏览器验证了桌面分栏、切换文章尺寸、两页窄屏及返回。

截图：`screenshots/feed-compact-grid.jpg`、`screenshots/feed-split-reader.jpg`、`screenshots/inbox-compact-grid.jpg`、`screenshots/inbox-split-reader.jpg`。

代码位于 `codex/agent-ui-optimization`，主干集成及提交验证见 [integration.md](integration.md)。
