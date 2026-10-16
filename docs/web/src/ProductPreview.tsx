import {
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  FileText,
  Folder,
  House,
  Inbox,
  Link,
  MessageSquare,
  MoreHorizontal,
  Newspaper,
  Paperclip,
  Plus,
  Search,
  Sparkles,
  Square,
} from "lucide-react";
import type { ReactNode } from "react";

const viewNames = ["收件箱", "知识库", "助手", "今日"];
const documents = ["AI 与个人知识管理", "设计的长期主义", "值得重读的文章"];

export function Mark({ children }: { children?: ReactNode }) {
  return (
    <span className="intro-mark">
      <Sparkles size={26} strokeWidth={1.5} />
      {children}
    </span>
  );
}

export function InboxPreview({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`inbox-preview ${compact ? "compact" : ""}`}>
      <div className="preview-card-head">
        <div>
          <strong>收件箱</strong>
          <span>先收集，再整理</span>
        </div>
        <Plus size={18} />
      </div>
      <div className="preview-list">
        {[
          { icon: FileText, title: "一段值得保留的文字", type: "文本" },
          { icon: Link, title: "一篇关于 AI 的文章", type: "链接" },
          { icon: Paperclip, title: "一个新的想法", type: "文件" },
        ].map(({ icon: Icon, title, type }) => (
          <div className="preview-row" key={title}>
            <Icon size={17} />
            <span>{title}</span>
            <small>{type}</small>
          </div>
        ))}
      </div>
      {!compact && (
        <div className="preview-note">
          <Inbox size={15} />
          灵感来了，先留住它。
        </div>
      )}
    </div>
  );
}

export function KnowledgePreview({ compact = false }: { compact?: boolean }) {
  return (
    <div className="knowledge-preview">
      <div className="preview-card-head">
        <div>
          <strong>知识库</strong>
          <span>我的知识库</span>
        </div>
        <Search size={17} />
      </div>
      <div className="preview-list">
        {documents.map((title, i) => (
          <div className="preview-row" key={title}>
            <FileText size={17} />
            <span>{title}</span>
            <small>{["AI · 阅读", "思考 · 设计", "阅读 · 收藏"][i]}</small>
          </div>
        ))}
      </div>
      {!compact && (
        <div className="preview-tags">
          <span>
            <Folder size={14} />
            阅读笔记
          </span>
          <span>
            <Folder size={14} />
            灵感与想法
          </span>
        </div>
      )}
    </div>
  );
}

export function TodayPreview({ compact = false }: { compact?: boolean }) {
  return (
    <div className="today-preview">
      <div className="preview-card-head">
        <div>
          <strong>今日</strong>
          <span>今日待办</span>
        </div>
        <MoreHorizontal size={18} />
      </div>
      <div className="preview-row">
        <Check size={17} />
        <span className="task-done">整理本周阅读笔记</span>
      </div>
      <div className="preview-row">
        <Square size={16} />
        <span>回顾今天的灵感</span>
      </div>
      {!compact && (
        <div className="preview-row">
          <Square size={16} />
          <span>把想法写成一个小计划</span>
        </div>
      )}
    </div>
  );
}

export function AssistantPreview({ compact = false }: { compact?: boolean }) {
  return (
    <div className="assistant-preview">
      <div className="preview-card-head">
        <strong>助手</strong>
        <MoreHorizontal size={18} />
      </div>
      <div className="reference-chip">
        <FileText size={14} />
        参考：我的阅读笔记
      </div>
      <p className="preview-reply">这些灵感，可以从三个方向展开。</p>
      {!compact && (
        <div className="answer-lines">
          <p>
            先梳理共同主题，再连接已有知识，
            <br />
            最后把值得尝试的想法变成行动。
          </p>
          <span>参考内容仅用于本轮对话</span>
        </div>
      )}
      <div className="preview-composer">
        <Paperclip size={17} />
        <span>问问息流…</span>
        <span className="send-circle">
          <ArrowUp size={18} />
        </span>
      </div>
    </div>
  );
}

export function ProductWindow({
  view = 3,
  large = false,
}: {
  view?: number;
  large?: boolean;
}) {
  const viewName = viewNames[view];
  return (
    <div className={`product-window ${large ? "window-large" : ""}`}>
      <div className="window-bar">
        <span className="window-dots">
          <i />
          <i />
          <i />
        </span>
        <span>息流 · 属于你的信息空间</span>
        <span className="window-caption">界面示意</span>
      </div>
      <div className="window-body">
        <aside className="window-sidebar" aria-label="演示导航">
          <div className="window-brand">
            <Mark />
            xiliu
          </div>
          {[
            { label: "今日", icon: House },
            { label: "助手", icon: MessageSquare },
            { label: "资讯", icon: Newspaper },
            { label: "收件箱", icon: Inbox },
            { label: "知识库", icon: BookOpen },
          ].map(({ label, icon: Icon }) => (
            <div
              className={`window-nav ${label === viewName ? "is-active" : ""}`}
              key={label}
            >
              <Icon size={16} />
              <span>{label}</span>
            </div>
          ))}
          <div className="window-local">
            <span />
            本地优先
          </div>
        </aside>
        <div className="window-content">
          <div className="window-content-top">
            <span>{viewName}</span>
            <Search size={16} />
          </div>
          {view === 3 ? (
            <>
              <span className="preview-eyebrow">
                每一天，思路都更清晰。
              </span>
              <h3>早上好，让今天更清晰。</h3>
              <p className="window-subtitle">把注意力，留给真正重要的事。</p>
              <div className="today-grid">
                <div className="window-panel">
                  <div className="panel-title">
                    <Newspaper size={17} />
                    今日简报
                    <ChevronRight size={16} />
                  </div>
                  <p>AI 的新进展，与你有关的部分。</p>
                  <div className="brief-item">
                    <span>人工智能热点</span>
                    <strong>从新的工具，到新的工作方式</strong>
                  </div>
                  <div className="brief-item">
                    <span>GitHub</span>
                    <strong>发现值得关注的开源项目</strong>
                  </div>
                  <div className="brief-item">
                    <span>收件箱</span>
                    <strong>留一点时间，整理新收集的灵感</strong>
                  </div>
                </div>
                <div className="window-panel">
                  <TodayPreview />
                </div>
              </div>
              <div className="overview-prompt">
                <Sparkles size={18} />
                <span>今天，想从什么开始？</span>
                <span className="send-circle">
                  <ArrowUp size={16} />
                </span>
              </div>
            </>
          ) : view === 0 ? (
            <>
              <span className="preview-eyebrow">让每个想法都有归处。</span>
              <h3>先留住，再慢慢想。</h3>
              <p className="window-subtitle">一段文字，一个链接，一份资料。</p>
              <div className="window-panel">
                <InboxPreview />
              </div>
              <div className="capture-hint">
                <Plus size={16} />
                收集文字、链接或文件<span>保留原件</span>
              </div>
            </>
          ) : view === 1 ? (
            <>
              <span className="preview-eyebrow">
                让你的知识相互连接。
              </span>
              <h3>把收藏，变成自己的知识。</h3>
              <p className="window-subtitle">
                用文件夹与标签，让内容各得其所。
              </p>
              <div className="window-panel">
                <KnowledgePreview />
              </div>
              <div className="capture-hint">
                <Search size={16} />
                搜索正文、摘要与标签<span>中文检索</span>
              </div>
            </>
          ) : (
            <>
              <span className="preview-eyebrow">带着积累，继续思考。</span>
              <h3>带着知识，继续对话。</h3>
              <p className="window-subtitle">把参考交给 AI，把判断留给自己。</p>
              <div className="window-panel">
                <AssistantPreview />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export function FeedPreview() {
  return (
    <div className="feed-preview">
      <div className="preview-card-head">
        <div>
          <strong>资讯</strong>
          <span>与世界保持连接</span>
        </div>
        <Newspaper size={19} />
      </div>
      <div className="feed-filter">
        <span className="selected">全部</span>
        <span>人工智能热点</span>
        <span>GitHub</span>
      </div>
      {[
        [
          "AI HOT",
          "让 AI 成为工作流的一部分",
          "关注工具背后的思路，发现可实践的方向。",
        ],
        [
          "GITHUB",
          "下一个值得探索的开源项目",
          "从 Trending 出发，把发现带回你的知识库。",
        ],
      ].map(([source, title, detail]) => (
        <div className="feed-item" key={source}>
          <span>{source}</span>
          <h4>{title}</h4>
          <p>{detail}</p>
          <div>
            <span>阅读原文</span>
            <span>收藏</span>
            <span>
              引用提问 <ArrowUpRight size={12} />
            </span>
          </div>
        </div>
      ))}
      <small className="demo-caption">
        示例内容 · 实际资讯由应用按来源获取
      </small>
    </div>
  );
}
