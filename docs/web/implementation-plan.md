> 本文件保留 2026-10-08 首版实现记录。当前源码、构建方式和 0.3.0 内容维护说明见同目录 README.md。

# 息流 A 版长页 Implementation Plan

**Goal:** 保存用户选定的 A 版到 README，并实现独立 `/intro/` 长页。
**Architecture:** 复用现有 Vite/React/GSAP/Lucide，新增多页入口，不改工作台导航或后端。工作区存在大量用户已有变更，原位添加隔离目录，不暂存或提交其他改动。
**Tech Stack:** React 19, TypeScript, Vite 7, GSAP ScrollTrigger, Lucide.
**Spec / approved visual:** 用户在本对话选择 A 版并授权按其风格实现长页；源图保存为 `docs/assets/xiliu-intro-concept-a.png`。

## Reference lock / decision ledger

| Decision | Source | Role / rule |
| --- | --- | --- |
| 白底、墨黑、轻宋体标题、黑色胶囊 CTA | A 版 + Refero Steep | 大标题 regular；正文 sans；圆角卡片 24px |
| 单处蜜桃色 #fbe1d1 + 棕字 #5d2a1a | Refero Steep | 仅本地优先 editorial callout；不扩散到 CTA |
| 置顶首屏由零散卡片过渡为完整工作台 | Steep 实站 1440×1000 滚动采集 | sticky 容器 + scrub 淡出/放大；不劫持滚轮 |
| 分区渐入，工作流视觉随滚动切换 | 原站产品叙事 + 息流信息流程 | GSAP context 清理；原生滚动 |
| Windows SimSun / Songti / Noto Serif SC 回退 | 中文标题 + 本机字体 | 不依赖远程字体；sans UI 与轻 serif display 分工 |
| 图标及品牌 | 现有 Lucide / Brand | 复用原品牌，单色呈现；不生成图片代替可交互 UI |
| 功能文案与安装 | README / COMPLETION_REVIEW | 不承诺离线 AI、云同步或已提供桌面安装包 |

## Files

- `docs/assets/xiliu-intro-concept-a.png`: 原 A 版图。
- `README.md`: 追加展示图、页面入口与参考来源。
- `web/intro/index.html`: 独立 HTML 元数据与入口。
- `web/src/features/intro/{main.tsx,LandingPage.tsx,landing.css,useLandingMotion.ts}`: 页面、组件与滚动动效。
- `web/src/features/intro/LandingPage.test.tsx`: 产品演示键盘切换、安装复制成功/失败。
- `web/vite.config.ts`: 加入 intro 多页构建 input。
- `src/xiliu/api/app.py`: 仅补充静态目录 index 解析和 HTML no-cache，保留原 SPA/API 行为；对应新增后端目标测试。
- `.preview/intro-smoke.cjs`: 本地浏览器验证脚本；截图/结果保留在忽略目录。
- `design-qa.md`: 来源、参考锁、桌面/移动/减少动态与交互验证。

## Constraints and review focus

- 入口 `/intro/`；主要 CTA 到安装 section，本地工作台链接 `/today`。
- 动画仅在桌面且无 reduced-motion 下启用，移动保持完整静态内容与可切换演示。
- 支持键盘、focus-visible、原生 FAQ details、剪贴板失败反馈。
- 展示内容均明确为交互演示，不产生真实 AI/API/用户数据写入。
- 覆盖 1536×1024、1440×900、1024×768、390×844，无横向溢出。
- GSAP 对 effect 卸载清理；滚动回退不会卡住页面；直达锚点可见。

## Tasks

- [x] 保存 A 图并追加 README；保留原有文档内容。
- [x] 写交互测试并确认缺实现的失败。
- [x] 实现首屏卡片、工作台过渡、四步叙事、功能分区、本地优先、FAQ、安装与页脚。
- [x] 复用 GSAP 实现滚动联动与 reveal，窄屏/减少动态降级。
- [x] 运行前端测试与生产构建；验证现有应用不受影响。
- [x] 真实浏览器截图并测试 sticky/滚动回退、键盘、FAQ、复制与锚点。
- [x] 比较 A 图及原站采集，完成 design-qa；打开介绍页交付。

## Verification ledger

- 用户授权在已有项目内实现；大量其他任务的修改保留，不创建提交、不改其页面行为。
- 前端 red→green：缺少 LandingPage 导入失败 → 新增交互实现后 3 项通过；全量 29 项通过。
- 后端 red→green：`/intro/` 原返回 SPA HTML → 目录 index 补充后目标 5 项通过，1 项 Windows 符号链接权限跳过。
- 生产构建和实际构建产物托管检查通过。
- 浏览器 13 项 + Escape/focus/console 补充检查通过，页面异常 0。
- 已人工并排检查 A 原图与最终首屏，以及工作流/Feed/AI/本地优先和手机视口。
- 滚动脚本只使用原生滚动，不使用平滑滚动代理，不修改用户浏览器全局设置。
- 独立复核发现说明灰字对比度偏低后，将正文灰色调至 #686d77、蜜桃区辅助棕字调至 #7d4b37。浏览器 30 处测量全部达到 4.5:1（最低 4.64:1）；已刷新并检查分区截图。
- 最终前端 29/29、生产构建、ESLint 0 警告、Prettier 均通过。
