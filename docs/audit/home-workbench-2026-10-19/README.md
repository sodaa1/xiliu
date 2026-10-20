# 首页山水工作台主题验收 · 2026-10-19

本次按「撤销上一轮无效改动，先把首页按参考图做好，保留原有主题」实施。只交付首页及首页相关弹窗、主题入口；不将全站改造标记为完成。个人计划工作台、新建任务表单及用户已有未提交改动均保留。

## 使用

首页顶部可切换「原有主题 / 山水工作台」，设置 → 外观中也可切换。默认保留原有主题，选择按浏览器、登录用户及演示模式隔离持久化；不会修改原来的浅色/暗色、字体、背景设置。切换两种首页保留尚未提交的速记草稿。专注计时仅在当前浏览器记录，不声称是后端历史统计。

## 参考与对照

参考来自用户 ZIP 中 `主页/01-home-main.jpg`、`02-quick-capture.jpg`、`03-daily-brief.jpg`、`04-mobile-today.jpg`，并以个人计划及任务弹窗的浅色紫色体系约束色彩。

- [参考图 / 实际页面并排](reference-vs-implementation.png)
- [原有主题 / 新主题](before-after-desktop.png)
- [任务区域放大对照](task-detail-comparison.png)
- [快速记录弹窗对照](capture-comparison.png)
- [移动端内容对照](mobile-content-comparison.png)
- [完整桌面](after-desktop.png) · [完整移动端](after-mobile.png) · [原有移动端](before-mobile.png)
- [移动速记](capture-mobile-final.png) · [暗色和大字号](dark-large-desktop.png) · [平板](tablet.png)
- [设置覆盖层](settings-overlay.png) · [资讯详情](article-desktop.png) · [今日简报](daily-brief.png)

桌面参考原始 2290×1406，等比例归一为 1440×884，与 Edge 的 1440×884 CSS 像素、DPR 1 截图比较。移动参考含手机边框及状态栏，对照图去掉系统装饰；实际网页保留可操作的搜索和主题切换入口。截图用独立临时数据库，通过真实 HTTP API 写入 6 个任务、12 条笔记、8 条资讯，不读取或修改用户工作区数据。1.5 小时为测试浏览器专注计时 fixture，非生产硬编码。

山水横幅、手写装饰和三张资讯配图直接提取参考图，未用生成图替代。裁剪坐标见下表；文件压缩为 WebP，总计约 64 KB。

| 资源 | 参考图裁剪范围（原图像素） |
| --- | --- |
| workbench-panorama.webp | 主页主图 (1000,100)–(2250,350) |
| workbench-panorama-mobile.webp | 主页主图 (1000,100)–(2250,255) |
| home-lake.webp | 主页主图 (420,1104)–(710,1237) |
| home-seaside.webp | 主页主图 (732,1104)–(1021,1237) |
| home-desk.webp | 主页主图 (1043,1104)–(1332,1237) |

保留的适配差异：使用项目现有品牌图标与 Lucide 图标；问候语按实际时间变化；资讯数显示「可读资讯」，不虚构阅读历史与昨日增长；任务标签来自实际任务分类；速记附件入口连接已有文件/链接导入，没有放置不可用的 @、# 按钮；活动时间线来自实际内容、任务和对话。移动端保留任务筛选。以上不声称像素级复刻。

## 迭代记录

1. 读取主图后实现独立侧栏、山水问候、四个概览区、任务与速记双栏、资讯配图及活动时间线，原首页分支保留。
2. 浏览器发现横幅被背景层遮盖，修复层级；替换为参考图原始画面，调整任务行数、字号、卡片高度及留白。
3. 对照速记参考图调整四个类型页签、输入区、保存栏，复用既有导入、任务、对话接口。
4. 移动端并排检查发现横幅和概览区偏高，缩短高度、增大任务文字；固定底栏接入实际导航与速记。
5. 独立代码审查修复保存中关闭导致草稿竞争、暗色问候文字对比、跨日计时重置、模态中 Ctrl+K 聚焦背景等问题。
6. 浏览器发现禁用按钮失焦后 Escape 无效，修复共享 ContentDialog 顶层键盘监听，补回归测试。

## 实际验证

| 检查 | 结果 | 原始记录 |
| --- | --- | --- |
| 全量前端测试 | 49 文件、231 项通过 | [frontend-tests.txt](frontend-tests.txt) |
| 全量 Python 测试 | 931 通过、1 跳过 | [python-tests.txt](python-tests.txt) |
| 应用界面分类保护 | 20 通过 | [surface-final.txt](surface-final.txt) |
| ESLint | 退出码 0 | [lint.txt](lint.txt) |
| TypeScript `tsc -b` | 退出码 0 | [typescript.txt](typescript.txt) |
| 生产构建，含 Intro | 成功 | [build.txt](build.txt) |
| 真实 Edge 浏览器 | 20 项场景通过，0 个页面脚本错误 | [基础场景](browser-checks.json)、[扩展场景](browser-extra-checks.json) |

浏览器覆盖主题切换/刷新持久化、任务完成/撤销、速记草稿保留、Ctrl+Enter 保存、搜索、计时、资讯预览、创建任务、手动资讯收录、收藏、简报、设置覆盖层、Tab 焦点约束、模态内 Ctrl+K、防止失败请求丢草稿、390px/768px 布局、暗色/大字号/减少动态效果。AI 跳转复用现有流程；未调用真实模型或检查新模型输出。生产构建保留 Vite 主包超过 500 KB 的体积提示，本轮未新增依赖。

## 本次修改文件

新增：

- `web/src/features/today/WorkbenchHome.tsx`：参考图首页、真实数据、速记/简报/资讯预览。
- `web/src/features/today/WorkbenchShell.tsx`：独立侧栏、搜索、主题切换及设置入口。
- `web/src/features/today/home-workbench.css`：本主题变量、组件样式、响应式、暗色及减少动画适配。
- `web/src/features/today/HomeThemeSwitch.tsx`、`home-theme.ts`：主题切换和存储。
- `web/src/features/today/useHomeDraft.ts`：切换主题时保留草稿。
- `web/src/features/today/FocusCard.tsx`：浏览器本地当天计时。
- `web/src/features/today/WorkbenchHome.test.tsx`、`home-theme.test.tsx`、`FocusCard.test.tsx`。
- `web/src/features/content/ContentDialog.test.tsx`：按钮禁用失焦后的键盘回归。
- `web/public/themes/` 中上表 5 个 WebP 资源。

修改：

- `web/src/app/App.tsx`：仅 Today 的新主题 Shell 分支、保留原设置覆盖层。
- `web/src/features/today/TodayPage.tsx`：保留原首页，按所选主题渲染。
- `web/src/features/settings/AppearanceSettings.tsx`：添加首页主题选择，不改其余设置布局。
- `web/src/features/content/ContentDialog.tsx`：顶层弹窗键盘事件与失焦恢复。
- `docs/audit/coverage-manifest.json`：仅补充新首页界面分类、复用现有 Action 绑定，保留原记录。
- `design-qa.md`：追加本次验收入口，保留已有内容。
- 当前验收目录：报告、截图、对照图、浏览器脚本及检查记录。

撤销的是上一轮新增的 soft-workspace 样式、VisualStyleSettings 和相关测试/挂载点；未使用 reset/clean 覆盖用户的计划页、任务 API、Modal、演示数据等未提交工作。

## 未完成

Assistant、Feed、Inbox、Knowledge、Settings 其它子页、Onboarding、Automations、Companion、Launch 尚未按本主题逐页改造和交付逐页截图。本次不将这些模块算作完成；个人计划和任务弹窗按用户要求保持现状。尚未做跨设备计时同步、真实 AI 调用或人工屏幕阅读器验收。
