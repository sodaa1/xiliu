import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronDown,
  CircleHelp,
  Copy,
  Database,
  FileText,
  Folder,
  Github,
  House,
  Layers,
  LockKeyhole,
  Menu,
  MessageSquare,
  Newspaper,
  Plus,
  Search,
  Server,
  Settings2,
  ShieldCheck,
  Sparkles,
  Workflow,
  X,
} from "lucide-react";
import {
  AssistantPreview,
  FeedPreview,
  InboxPreview,
  KnowledgePreview,
  Mark,
  ProductWindow,
  TodayPreview,
} from "./ProductPreview";
import { useLandingMotion } from "./useLandingMotion";

const stages = [
  {
    name: "收集",
    en: "COLLECT",
    title: (
      <>
        灵感来了，
        <br />
        先留住它。
      </>
    ),
    body: "不必一开始就想好分类。网页、文字、文件，先放进收件箱。保留原文与来源，给稍后的思考留一个入口。",
    tags: ["文字 / 链接 / 文件", "原件保留", "后台整理"],
  },
  {
    name: "整理",
    en: "ORGANIZE",
    title: (
      <>
        让收藏，
        <br />
        慢慢成为知识。
      </>
    ),
    body: "把值得留下的内容放入知识库。用标签和规则文件夹组织，以全文、元数据和可选向量检索找回。资料变化在后台进入 RAG 索引，重新发现被你收藏的好想法。",
    tags: ["规则文件夹", "中文混合检索", "可选 embedding"],
  },
  {
    name: "对话",
    en: "UNDERSTAND",
    title: (
      <>
        从已有的知识，
        <br />
        问出新的问题。
      </>
    ),
    body: "把资料带入这一轮对话，让 AI 围绕你的参考展开。多个会话独立保存运行状态，查看思考过程，也可以只停止当前会话的回复。",
    tags: ["多会话", "停止回复", "本轮参考"],
  },
  {
    name: "行动",
    en: "ACT",
    title: (
      <>
        从一个想法，
        <br />
        到今天的一小步。
      </>
    ),
    body: "在今日看简报、回顾收集、处理待办。把重复的事情交给每日自动任务，为值得投入的思考多留一点时间。",
    tags: ["今日简报", "待办事项", "每日自动任务"],
  },
];

const repositoryUrl = "https://github.com/sodaa1/xiliu";
const installCommands =
  "git clone https://github.com/sodaa1/xiliu.git\ncd xiliu\nuv sync --dev\ncd web\nnpm ci\nnpm run build\ncd ..\nuv run xiliu web --open";
const questions = [
  [
    "息流适合用来做什么？",
    "它适合个人的日常信息工作：收集文章与资料、整理阅读笔记、围绕自己的参考与 AI 对话，再用简报、待办与自动任务组织一天。",
  ],
  [
    "“本地优先”意味着 AI 可以离线运行吗？",
    "资料、会话与配置保存在本机。AI 连接你配置的本地或远程模型服务；资讯与 Search 等联网工具仍需网络，是否能离线取决于所用模型和工具。",
  ],
  [
    "可以使用自己的模型吗？",
    "可以。在设置中配置服务商、模型与兼容接口地址。息流支持 OpenAI 兼容接口，并提供 DeepSeek 等预设；模型与服务费用由对应服务商收取。",
  ],
  [
    "自动任务会一直在后台运行吗？",
    "自动任务需要息流应用或调度进程保持运行。你可以在设置中创建每日任务，暂停、恢复并查看最近运行记录。",
  ],
  [
    "现在如何开始使用？",
    "从 GitHub 获取 xiliu 源码，安装 Python 3.12+、uv 和 Node.js / npm，按下方命令运行网页工作台。Windows 已完成 0.3.0 安装包构建；安装包不存入 Git 源码，当前 GitHub Releases 尚无公开下载资产。",
  ],
  [
    "Windows 桌面版如何安装？",
    "已有 Xiliu-0.3.0-x64-setup.exe 时，双击并按中文向导安装，无需另装 Python、Node.js 或 Rust。需要 WebView2，缺少时安装引导程序会联网下载。首次启动在设置中填写自己的模型连接与 API 密钥；安装包未签名。源码构建步骤见 GitHub 的 desktop/README.md。",
  ],
  [
    "模型能联网，为什么搜索还需要配置？",
    "对话模型、AIHot MCP 和 Search 是不同的调用链。AIHot 默认公开 MCP 配置不依赖模型 API 密钥；Search 使用独立的 TAVILY_API_KEY，其他 MCP 服务按各自要求配置。停止回复也不会撤销已经完成的写入。",
  ],
];

function Action({
  secondary = false,
  href = "#start",
  children = "开始使用",
}: {
  secondary?: boolean;
  href?: string;
  children?: ReactNode;
}) {
  return (
    <a className={`intro-button ${secondary ? "outline" : ""}`} href={href}>
      {children}
      {secondary ? <ArrowRight size={16} /> : <ArrowUpRight size={17} />}
    </a>
  );
}

export function LandingPage({
  publicShowcase = false,
}: {
  publicShowcase?: boolean;
}) {
  const root = useRef<HTMLDivElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const [active, setActive] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const [question, setQuestion] = useState(0);
  useLandingMotion(root, setActive);

  useEffect(() => {
    if (!menuOpen) return;
    const closeWithEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setMenuOpen(false);
      menuButton.current?.focus();
    };
    window.addEventListener("keydown", closeWithEscape);
    return () => window.removeEventListener("keydown", closeWithEscape);
  }, [menuOpen]);

  function onTabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % stages.length;
    else if (event.key === "ArrowLeft")
      next = (index + stages.length - 1) % stages.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = stages.length - 1;
    else return;
    event.preventDefault();
    setActive(next);
    document.getElementById(`flow-tab-${next}`)?.focus();
  }

  async function copyInstall() {
    try {
      await navigator.clipboard.writeText(installCommands);
      setCopyStatus("安装命令已复制");
    } catch {
      setCopyStatus("请选中下方命令手动复制");
    }
  }

  return (
    <div className="intro-site" ref={root}>
      <a className="skip-link" href="#features">
        跳到功能介绍
      </a>
      <header className="intro-header">
        <a className="intro-brand" href="#top" aria-label="息流 xiliu 首页">
          <Mark />
          <span>
            息流 <em>xiliu</em>
          </span>
        </a>
        <nav
          className={menuOpen ? "is-open" : ""}
          id="intro-navigation"
          aria-label="介绍页导航"
          onClick={() => setMenuOpen(false)}
        >
          <a href="#features">
            <Layers size={16} strokeWidth={1.7} aria-hidden="true" />
            <span>功能</span>
          </a>
          <a href="#workflow">
            <Workflow size={16} strokeWidth={1.7} aria-hidden="true" />
            <span>工作流</span>
          </a>
          <a href="#local">
            <Database size={16} strokeWidth={1.7} aria-hidden="true" />
            <span>本地优先</span>
          </a>
          <a href="#questions">
            <CircleHelp size={16} strokeWidth={1.7} aria-hidden="true" />
            <span>常见问题</span>
          </a>
        </nav>
        <div className="header-actions">
          <Action />
          <button
            className="mobile-menu"
            ref={menuButton}
            aria-label={menuOpen ? "关闭导航" : "打开导航"}
            aria-controls="intro-navigation"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X size={21} /> : <Menu size={21} />}
          </button>
        </div>
      </header>

      <main>
        <section
          className="hero-scroll"
          id="top"
          aria-labelledby="intro-heading"
        >
          <div className="hero-stage">
            <div className="hero-copy">
              <div className="hero-center">
                <p className="eyebrow">个人信息与 AI 助手 · 0.3.0</p>
                <h1 id="intro-heading">
                  信息有归处，
                  <br />
                  思考自成流。
                </h1>
                <p className="hero-description">
                  收集灵感，整理知识，与 AI 一起思考。
                  <br className="mobile-break" />
                  把注意力，留给真正重要的事。
                </p>
                <div className="button-pair">
                  <Action />
                  <Action secondary href="#workflow">
                    了解息流
                  </Action>
                </div>
              </div>
            </div>
            <div className="float-card float-inbox">
              <InboxPreview compact />
            </div>
            <div className="float-card float-knowledge">
              <KnowledgePreview compact />
            </div>
            <div className="float-card float-today">
              <TodayPreview compact />
            </div>
            <div className="float-card float-assistant">
              <AssistantPreview compact />
            </div>
            <div className="hero-overview">
              <ProductWindow large />
            </div>
            <a className="hero-scroll-cue" href="#features">
              <span>向下，看看信息如何流动</span>
              <ArrowDown size={16} />
            </a>
          </div>
        </section>

        <section className="intro-manifesto intro-container" id="features">
          <div data-reveal>
            <p className="eyebrow">少些散乱，多些清晰。</p>
            <h2>
              从随手收集，
              <br />
              到真正理解。
            </h2>
          </div>
          <div className="manifesto-body" data-reveal>
            <p>
              好想法，常常散落在不同地方。
              <br />
              一篇文章、一段对话、一闪而过的灵感。
            </p>
            <p>
              息流让它们在同一个空间相遇。
              <br />
              不急着处理所有信息，先留下值得思考的。
            </p>
            <a className="text-link" href="#workflow">
              走一遍你的信息流 <ArrowRight size={17} />
            </a>
          </div>
        </section>

        <section
          className="workflow-section"
          id="workflow"
          aria-labelledby="workflow-heading"
        >
          <div className="intro-container">
            <div className="section-heading" data-reveal>
              <p className="eyebrow">让信息与行动连起来</p>
              <h2 id="workflow-heading">
                不是更多收藏。
                <br />
                是更有用的连接。
              </h2>
              <p>从发现到行动，让每一步自然衔接。</p>
            </div>
            <div className="workflow-layout">
              <div className="workflow-story">
                {stages.map((stage, i) => (
                  <article
                    className={`workflow-step ${active === i ? "current" : ""}`}
                    data-stage={i}
                    key={stage.name}
                    id={`step-${i}`}
                  >
                    <span className="step-number">
                      0{i + 1} / {stage.en}
                    </span>
                    <h3>{stage.title}</h3>
                    <p>{stage.body}</p>
                    <div className="step-tags">
                      {stage.tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
              <div className="workflow-sticky">
                <div
                  className="flow-tabs"
                  role="tablist"
                  aria-label="信息流演示"
                >
                  {stages.map((stage, i) => (
                    <button
                      key={stage.name}
                      role="tab"
                      id={`flow-tab-${i}`}
                      aria-controls="flow-panel"
                      aria-selected={active === i}
                      tabIndex={active === i ? 0 : -1}
                      onClick={() => setActive(i)}
                      onKeyDown={(event) => onTabKey(event, i)}
                    >
                      {stage.name}
                    </button>
                  ))}
                </div>
                <div
                  className="flow-panel"
                  role="tabpanel"
                  id="flow-panel"
                  aria-labelledby={`flow-tab-${active}`}
                  tabIndex={0}
                >
                  <ProductWindow view={active} />
                </div>
                <p className="demo-caption">
                  <span className="demo-dot" />
                  交互演示 · 向下滚动或切换上方步骤
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="feed-section intro-container feature-split">
          <div className="feature-copy" data-reveal>
            <p className="eyebrow">01 / 发现下一份灵感</p>
            <h2>
              与世界连接。
              <br />
              为自己留下。
            </h2>
            <p>
              在资讯发现 AI 新进展与 GitHub
              热门项目。读到值得保留的，收进来；遇到值得追问的，交给 AI
              一起梳理。
            </p>
            <a
              className="text-link"
              href={publicShowcase ? "#workflow" : "/feed"}
            >
              {publicShowcase ? "了解收集流程" : "打开资讯"}{" "}
              <ArrowUpRight size={17} />
            </a>
            <div className="inline-benefits">
              <span>
                <NewspaperIcon />
                发现资讯
              </span>
              <span>
                <Plus size={15} />
                保存到资料
              </span>
              <span>
                <MessageSquare size={15} />
                引用提问
              </span>
            </div>
          </div>
          <div className="feature-visual" data-reveal>
            <div className="floating-sheet">
              <FeedPreview />
            </div>
          </div>
        </section>

        <section className="knowledge-section intro-container feature-split reverse">
          <div className="feature-visual knowledge-scene" data-reveal>
            <div className="knowledge-search">
              <Search size={18} />
              <span>搜索自己的知识</span>
              <kbd>中文</kbd>
            </div>
            <div className="knowledge-folders">
              <div>
                <Folder size={22} />
                <span>阅读笔记</span>
                <small>值得回来的地方</small>
              </div>
              <div>
                <Folder size={22} />
                <span>研究资料</span>
                <small>慢慢积累的线索</small>
              </div>
              <div>
                <Folder size={22} />
                <span>灵感与想法</span>
                <small>还没长成的可能</small>
              </div>
            </div>
            <div className="floating-sheet knowledge-sheet">
              <KnowledgePreview compact />
            </div>
            <span className="scene-caption">
              让“我记得收藏过”，变成“就在这里”。
            </span>
          </div>
          <div className="feature-copy" data-reveal>
            <p className="eyebrow">02 / 让知识留在身边</p>
            <h2>
              让每次积累，
              <br />
              都找得回来。
            </h2>
            <p>
              标签与规则文件夹，给内容一个位置。正文、摘要与元数据一起检索，帮你从自己的资料中找回答案的线索。
            </p>
            <a
              className="text-link"
              href={publicShowcase ? "#workflow" : "/knowledge"}
            >
              {publicShowcase ? "了解知识整理" : "打开知识库"}{" "}
              <ArrowUpRight size={17} />
            </a>
            <div className="inline-benefits">
              <span>
                <Folder size={15} />
                规则文件夹
              </span>
              <span>
                <Search size={15} />
                中文检索
              </span>
            </div>
          </div>
        </section>

        <section
          className="ai-section intro-container"
          aria-labelledby="ai-heading"
        >
          <div className="section-heading" data-reveal>
            <p className="eyebrow">03 / 为思考添一点助力</p>
            <h2 id="ai-heading">
              你的知识，
              <br />
              也是对话的起点。
            </h2>
            <p>带上一份参考，让思考再往前走一步。</p>
          </div>
          <div className="ai-demo" data-reveal>
            <div className="ai-demo-sidebar">
              <Mark />
              <span>我的阅读笔记</span>
              <h3>我的阅读笔记</h3>
              <p>关于 AI、设计，以及如何更好地思考。</p>
              <div>
                <FileText size={17} />
                AI 与个人知识管理
              </div>
              <div>
                <FileText size={17} />
                设计的长期主义
              </div>
              <div>
                <FileText size={17} />
                值得重读的文章
              </div>
              <small>示例资料，不读取你的本地内容</small>
            </div>
            <div className="ai-demo-chat">
              <div className="chat-demo-label">
                <Sparkles size={17} />
                <span>助手</span>
                <small>交互演示 · 不调用模型</small>
              </div>
              <div className="sample-question">
                {
                  [
                    "这些笔记有什么共同主题？",
                    "帮我整理成一个行动计划。",
                    "下一步值得探索什么？",
                  ][question]
                }
              </div>
              <div className="sample-answer" key={question}>
                <Mark />
                <div>
                  <span className="reference-chip">
                    <BookOpen size={14} />
                    参考：我的阅读笔记
                  </span>
                  <p>
                    {
                      [
                        "这些笔记都在回答一个问题：如何让信息真正参与思考。",
                        "可以从一个小而完整的循环开始，不必一次整理所有内容。",
                        "可以从“知道了什么”，继续问到“这些知识能改变什么”。",
                      ][question]
                    }
                  </p>
                  <ol>
                    {[
                      [
                        "从收藏转向理解：留下观点，也留下自己的问题。",
                        "从单篇转向连接：用标签把相近的想法放在一起。",
                        "从理解转向行动：为有价值的想法留一个下一步。",
                      ],
                      [
                        "挑一篇值得重读的文章，收进收件箱。",
                        "写下三个关键词，整理到自己的知识库。",
                        "带着参考问一个问题，把答案变成今天的待办。",
                      ],
                      [
                        "比较不同笔记里相似的观点，它们是否矛盾？",
                        "找一个工作中的真实问题，用现有资料试着回答。",
                        "把还不确定的地方留下，成为下一次阅读的方向。",
                      ],
                    ][question].map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ol>
                </div>
              </div>
              <div className="question-options" aria-label="选择示例问题">
                {["发现共同主题", "整理行动计划", "继续探索"].map(
                  (label, i) => (
                    <button
                      key={label}
                      aria-pressed={question === i}
                      onClick={() => setQuestion(i)}
                    >
                      {label}
                      <ArrowUpRight size={13} />
                    </button>
                  ),
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="everyday-section intro-container">
          <div className="everyday-top" data-reveal>
            <div>
              <p className="eyebrow">04 / 给每一天留出空间</p>
              <h2>
                重要的事，
                <br />
                回到今天。
              </h2>
            </div>
            <p>
              少一点来回切换。
              <br />在今日，知道从哪里开始。
            </p>
          </div>
          <div className="everyday-grid">
            <div className="everyday-card" data-reveal>
              <div className="everyday-card-title">
                <span>今日</span>
                <HouseIcon />
              </div>
              <h3>
                先看清今天，
                <br />
                再开始行动。
              </h3>
              <p>
                今日简报与待办放在一起，
                <br />
                给一天一个清晰的起点。
              </p>
              <div className="floating-sheet">
                <TodayPreview />
              </div>
            </div>
            <div className="everyday-card" data-reveal>
              <div className="everyday-card-title">
                <span>自动任务</span>
                <Settings2 size={19} />
              </div>
              <h3>
                重复的事情，
                <br />
                让它按时发生。
              </h3>
              <p>
                设置每日任务，保留运行记录。
                <br />
                把精力留给需要你判断的事。
              </p>
              <div className="automation-example">
                <div>
                  <span className="automation-symbol">
                    <Layers size={21} />
                  </span>
                  <div>
                    <strong>我的每日简报</strong>
                    <span>每天 09:00</span>
                  </div>
                  <span className="example-status">
                    <Check size={13} />
                    已启用
                  </span>
                </div>
                <div className="automation-record">
                  <span>最近运行</span>
                  <span>
                    已完成 <Check size={14} />
                  </span>
                </div>
                <small>示例状态 · 调度需要应用保持运行</small>
              </div>
            </div>
          </div>
        </section>

        <section className="local-section intro-container" id="local">
          <div className="local-callout" data-reveal>
            <div>
              <p className="eyebrow">本地优先，由你选择。</p>
              <h2>
                属于你的信息，
                <br />
                留在你的工作台。
              </h2>
              <p>
                数据保存在本机，模型由你选择。
                <br />
                让工具适应你的习惯，让思考保留自己的节奏。
              </p>
              <a className="text-link" href="#start">
                建立自己的信息空间 <ArrowRight size={17} />
              </a>
            </div>
            <div className="local-principles">
              <div>
                <Database size={23} />
                <h3>本地保存</h3>
                <p>
                  资料与工作数据保留在本机，
                  <br />
                  原件与整理后的内容都有出处。
                </p>
              </div>
              <div>
                <Server size={23} />
                <h3>模型自选</h3>
                <p>
                  连接你选择的模型服务，
                  <br />
                  按自己的需要配置兼容接口。
                </p>
              </div>
              <div>
                <ShieldCheck size={23} />
                <h3>能力可扩展</h3>
                <p>
                  通过 Skill 与 MCP 扩展能力，
                  <br />
                  继续使用息流已有的执行机制。
                </p>
              </div>
            </div>
            <div className="local-footnote">
              <LockKeyhole size={15} />
              本地优先指数据存储。AI 与资讯获取按配置连接外部服务。
            </div>
          </div>
        </section>

        <section className="faq-section intro-container" id="questions">
          <div data-reveal>
            <p className="eyebrow">你可能想了解的事</p>
            <h2>
              开始之前，
              <br />
              你可能想问。
            </h2>
          </div>
          <div className="faq-list" data-reveal>
            {questions.map(([title, answer]) => (
              <details key={title}>
                <summary>
                  {title}
                  <ChevronDown size={18} />
                </summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="start-section intro-container" id="start">
          <div data-reveal>
            <p className="eyebrow">从小处开始，让思路清晰。</p>
            <h2>
              给下一个好想法，
              <br />
              留一个位置。
            </h2>
            <p>从今天收集的第一条灵感开始。</p>
            <div className="button-pair">
              <Action href={publicShowcase ? repositoryUrl : "/today"}>
                {publicShowcase ? "查看 GitHub 项目" : "打开本地工作台"}
              </Action>
              <Action secondary href="#install">
                查看安装步骤
              </Action>
            </div>
            <small>
              {publicShowcase
                ? "在自己的电脑上安装，让信息留在自己的工作台。"
                : "已有息流服务？可以直接进入工作台。"}
            </small>
          </div>
          <div className="install-panel" id="install" data-reveal>
            <div className="install-head">
              <span>从源码运行 · 网页 / Windows</span>
              <button
                onClick={() => void copyInstall()}
                aria-label="复制安装命令"
              >
                <Copy size={15} />
                <span>复制命令</span>
              </button>
            </div>
            <p className="install-requirements">
              需要 Python 3.12+、uv、Node.js / npm。
            </p>
            <pre>
              <code>{installCommands}</code>
            </pre>
            <p>
              Windows 也可以双击 <code>start-xiliu.bat</code>。<br />
              在设置中配置模型连接后，即可开始 AI 对话。
            </p>
            <a
              className="text-link"
              href={`${repositoryUrl}/blob/main/desktop/README.md`}
              target="_blank"
              rel="noreferrer"
            >
              Windows 桌面安装与构建 <ArrowUpRight size={14} />
            </a>
            {copyStatus && (
              <div role="status" className="copy-status">
                {copyStatus}
              </div>
            )}
          </div>
        </section>
      </main>
      <footer className="intro-footer intro-container">
        <div className="footer-top">
          <a className="intro-brand" href="#top">
            <Mark />
            <span>
              息流 <em>xiliu</em>
            </span>
          </a>
          <p>信息有归处。思考自成流。</p>
          <a className="text-link" href="#top">
            回到开头 <ArrowUpRight size={16} />
          </a>
        </div>
        <div className="footer-bottom">
          <span>本地优先的个人信息与 AI 助手</span>
          <div className="footer-links">
            <a href="https://933693.xyz/">
              返回作品集 <ArrowUpRight size={13} />
            </a>
            <a href={repositoryUrl} target="_blank" rel="noreferrer">
              <Github size={14} />
              GitHub · xiliu
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function NewspaperIcon() {
  return <Newspaper size={15} />;
}
function HouseIcon() {
  return <House size={19} />;
}
