import importlib
import importlib.util

import pytest


def resolve(text):
    module = "xiliu.app.intent"
    assert importlib.util.find_spec(module) is not None, "typed App intent resolver missing"
    return importlib.import_module(module).resolve_intent(text)


@pytest.mark.parametrize(
    "text, action",
    [
        ("列出待办", "tasks.list"),
        ("创建待办‘读书’", "tasks.create"),
        ("完成待办‘读书’", "tasks.complete"),
        ("重新打开待办‘读书’", "tasks.complete"),
        ("将待办‘读书’改名为‘阅读’", "tasks.update"),
        ("删除待办‘读书’", "tasks.delete"),
        ("浏览Feed", "feed.list"),
        ("刷新Feed", "feed.refresh"),
        ("给Feed加入https://example.com/story作为资讯", "feed.add_manual"),
        ("隐藏Feed资讯‘新闻’", "feed.hide_external"),
        ("恢复Feed隐藏的资讯‘新闻’", "feed.unhide_external"),
        ("删除Feed我添加的资讯‘新闻’", "feed.remove_manual"),
        ("Inbox有什么？", "inbox.list"),
        ("把‘灵感’放入Inbox", "inbox.import_text"),
        ("导入https://example.com/story到Inbox", "inbox.import_url"),
        ("将Inbox里面内容分类归入知识库", "inbox.classify_all"),
        ("把我收件箱里还没整理的内容都搬到知识库", "inbox.classify_all"),
        ("一键整理收件箱", "inbox.classify_all"),
        ("重试Inbox‘资料’", "inbox.retry"),
        ("查看知识库文件夹", "knowledge.folders.list"),
        ("在知识库创建名为‘面试’的文件夹", "knowledge.folders.create"),
        ("知识库文件夹‘面试’改名为‘求职’", "knowledge.folders.update"),
        ("删除知识库文件夹‘面试’", "knowledge.folders.delete"),
        ("知识库里有面试相关资料吗？", "knowledge.search"),
        ("查看个人设置", "preferences.get"),
        ("把昵称改为‘溪流’", "preferences.update"),
        ("切换深色主题", "preferences.update"),
        ("将字号调大", "preferences.update"),
        ("开启减少动画", "preferences.update"),
        ("恢复默认外观", "preferences.reset"),
        ("查看自动化任务", "automations.list"),
        ("暂停自动任务‘新闻’", "automations.toggle"),
        ("启用自动化‘新闻’", "automations.toggle"),
        ("删除自动化‘新闻’", "automations.delete"),
        ("查看自动化‘新闻’的运行记录", "automations.runs"),
        ("创建每日09:30自动化‘新闻’提示词‘总结资讯’", "automations.create"),
        ("列出会话", "conversations.list"),
        ("创建新会话", "conversations.create"),
        ("查看会话‘项目’", "conversations.get"),
        ("会话‘项目’改名为‘研究’", "conversations.update"),
        ("查看会话‘项目’消息历史", "conversations.messages"),
    ],
)
def test_domain_verbs_and_semantic_rephrases_share_registered_actions(text, action):
    intent = resolve(text)
    assert intent.action_id == action
    assert intent.kind in {"read", "write"}


@pytest.mark.parametrize(
    "text",
    [
        "怎么看Inbox分类规则？",
        "不要操作，解释一下怎么分类Inbox",
        "如果我要删除Feed资讯应该怎么做？",
        "假设清空知识库会怎样？",
        "别删除待办‘读书’",
        "我不想删除Inbox内容",
        "Do not delete Feed items",
        "Explain how to add Feed news",
    ],
)
def test_negation_hypothetical_and_explanations_never_become_writes(text):
    intent = resolve(text)
    assert intent is not None and intent.kind == "explain"
    assert intent.action_id is None


@pytest.mark.parametrize("text", ["明天天气怎么样？", "帮我写Python脚本", "什么是量子力学？"])
def test_unrelated_tasks_remain_available_to_normal_runtime(text):
    assert resolve(text) is None


def test_target_folder_workflow_preserves_url_and_link_only_constraint():
    url = "https://github.com/CHENG-LIANG1/real-company-interview-ai-coding-projects"
    intent = resolve(
        f"在知识库创建一个叫面试的文件夹，把 {url} 先放Inbox生成标签再归档，只保存链接不要克隆"
    )
    assert intent.kind == "workflow"
    assert intent.arguments == {"url": url, "folder_name": "面试", "use_ai": False}


def test_relative_task_date_requires_clarification_without_guessing():
    intent = resolve("帮我创建一个明天下午的待办‘读书’")
    assert intent.kind == "clarify"
    assert not intent.arguments.get("due_at")


@pytest.mark.parametrize(
    "target", ["归类到科研下面", "归档到科研文件夹", "收藏到知识库的科研文件夹"]
)
def test_link_collection_extracts_natural_target_folder(target):
    intent = resolve(f"https://infmind.cn/ 帮我收藏一下这个网站，整理到知识库，{target}")
    assert intent.kind == "workflow"
    assert intent.arguments == {
        "url": "https://infmind.cn/", "folder_name": "科研", "use_ai": False
    }
