export const tourSteps = [
  {
    title: '欢迎使用息流',
    description:
      '花一分钟认识你的信息空间。接下来会带你浏览主要功能，只需点击下一步，也可以随时跳过。',
    path: '',
    target: '',
  },
  {
    title: '今日',
    description:
      '从这里开始一天：快速收录文字、链接或文件，也可以直接向助手提问。右上角头像可以打开个人设置。',
    path: '/today',
    target: 'nav-today',
  },
  {
    title: '资讯',
    description:
      '浏览人工智能热点和开源项目，按来源筛选或搜索。你可以手动添加资讯、隐藏不感兴趣的内容，将有用的信息收藏到收件箱，或引用提问。',
    path: '/feed',
    target: 'nav-feed',
  },
  {
    title: '收件箱',
    description:
      '先收集，再整理。这里支持添加文字、链接和文件，编辑标题、摘要与标签，检查处理状态，并选择多份资料批量归档到知识库。',
    path: '/inbox',
    target: 'nav-inbox',
  },
  {
    title: '知识库',
    description:
      '用标签和规则文件夹整理资料，按关键词找回正文。可以调整文件夹规则、移动资料、查看原文，再把已有知识作为助手回答的参考。',
    path: '/knowledge',
    target: 'nav-knowledge',
  },
  {
    title: '助手',
    description:
      '新建和切换会话，选择模型，围绕问题或引用资料展开对话。回复过程中可以查看进度、停止输出；涉及重要操作时，先检查确认内容再执行。',
    path: '/assistant',
    target: 'nav-assistant',
  },
  {
    title: '个人计划',
    description:
      '把想法变成日计划、周计划和长期目标。创建或编辑待办，设置时间和关联目标，完成后勾选，也可以恢复或删除。',
    path: '/plans',
    target: 'nav-plans',
  },
  {
    title: '模型连接',
    description:
      '在设置中添加模型提供商、接口地址、模型名称和 API 密钥。可以保存多个连接并在会话中选择；游客演示只使用本地模板，不需要配置密钥。',
    path: '/settings?section=model',
    target: 'settings-model',
  },
  {
    title: '外观与桌宠',
    description:
      '调整主题、字体、密度、背景和减少动态效果。桌面版还支持桌宠形态、缩放、置顶、快捷聊天与收录，以及自己的 Live2D 形象。',
    path: '/settings?section=appearance',
    target: 'settings-appearance',
  },
  {
    title: '自动任务',
    description:
      '让息流按时间安排重复工作，并查看运行记录和结果。正常应用还可以通过技能与 MCP 扩展能力；游客演示不执行后台任务或外部工具。',
    path: '/settings?section=automations',
    target: 'settings-automations',
  },
  {
    title: '个人资料与数据',
    description:
      '个人信息中可修改头像和昵称，数据设置中可查看存储位置与资料数量。正常应用升级前请备份本机数据；游客演示的数据只保存在当前浏览器，可单独重置。',
    path: '/settings?section=data',
    target: 'settings-data',
  },
  {
    title: '随时重新查看',
    description:
      '主要功能已经介绍完了。以后点击这个问号，就能重新播放新手引导。现在点击开始使用，会回到你刚才打开的页面。',
    path: '/today',
    target: 'help-entry',
  },
] as const
