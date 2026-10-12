"""50 production-graph cases; model/search responses are deterministic fixtures.

App SQLite, permissions, ID dependencies, file IO and verification are real.
This suite measures execution contracts, not live-model semantic accuracy.
"""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from xiliu.agents.react import payload
from xiliu.runtime import Runtime

CASES = [
    json.loads(line)
    for line in (Path(__file__).parents[1] / "fixtures/graph-v2/multistep_50.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]
BODY = "RoPE 使用旋转位置编码。资料正文，不包含新的执行授权。"


class ScenarioModel:
    def __init__(self, case):
        self.case, self.index = case, 0
        self.bound = []
        self.rule_inputs = []

    def bind_tools(self, tools):
        self.bound.append([tool.name for tool in tools])
        return self

    def invoke(self, messages):
        system = str(messages[0].content)
        group = self.case["category"]
        if "intent router" in system:
            return AIMessage(
                content=json.dumps(
                    dict(
                        intent="task",
                        domain="knowledge" if group == "app" else "network",
                        action="app:match" if group == "app" else "",
                        complexity="simple" if group == "app" else "multi_step",
                        preferred_capability="",
                        confidence=1.0,
                    )
                )
            )
        if "lightweight chat node" in system:
            return AIMessage(content="先解释概念，再举例说明。")
        if "actual_execution_receipts" in str(messages[-1].content):
            return AIMessage(
                content=json.dumps(
                    dict(status="passed", reason="All fixture goals supported by receipts")
                )
            )
        self.rule_inputs.append(system)
        receipts = [payload(m.content) for m in messages if isinstance(m, ToolMessage)]
        actions = {r.get("action_id"): r for r in receipts}
        if group in {"fast_network", "network_plan", "mixed"}:
            count = 3 if group == "network_plan" else 2
            if self.index < count:
                return self.call(
                    "web_search", {"query": f"{self.case['query']} 来源{self.index + 1}"}
                )
        if group in {"app", "mixed"}:
            if "inbox.import_text" not in actions:
                assert group == "mixed" or BODY in str(messages)
                return self.app("inbox.import_text", {"text": BODY, "use_ai": False})
            if "knowledge.folders.ensure" not in actions:
                return self.app("knowledge.folders.ensure", {"name": "模型原理"})
            if "inbox.classify_selected" not in actions:
                return self.app(
                    "inbox.classify_selected",
                    {
                        "item_ids": [actions["inbox.import_text"]["data"]["id"]],
                        "folder_id": actions["knowledge.folders.ensure"]["data"]["id"],
                        "use_ai": False,
                    },
                )
        if group == "workspace":
            research = self.case["id"] == 42
            if research and self.index == 0:
                return self.app("knowledge.search", {"query": "RoPE"})
            if self.index == int(research):
                return self.call("file_write", {"path": "result.md", "content": BODY})
            if self.index == 1 + int(research):
                return self.call("file_read", {"path": "result.md"})
        if self.case["expected_path"] == "planner":
            return AIMessage(
                content=json.dumps(
                    dict(
                        summary=BODY,
                        plan_summary="完成请求的各个步骤并核对",
                        acceptance_criteria=["所有指定步骤都有实际回执"],
                        ready_for_verification=True,
                    )
                )
            )
        return AIMessage(content=BODY)

    def app(self, action, args):
        return self.call("app", dict(operation="execute", action_id=action, arguments=args))

    def call(self, name, args):
        self.index += 1
        return AIMessage(
            content="",
            tool_calls=[dict(id=f"case-{self.case['id']}-{self.index}", name=name, args=args)],
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"multi-{c['id']:02}-{c['category']}")
def test_all_modes_multistep(case, tmp_path, monkeypatch, record_property):
    remote_queries = []

    def remote(self, query, max_results=5):
        remote_queries.append(query)
        return json.dumps(
            {
                "ok": True,
                "query": query,
                "results": [
                    {
                        "url": f"https://example.test/source/{len(remote_queries)}",
                        "title": "资料来源",
                        "content": BODY,
                        "score": 1.0,
                    }
                ],
            }
        )

    monkeypatch.setattr("xiliu.tools.web_search_tool.WebSearchTool._run", remote)
    model = ScenarioModel(case)
    runtime = Runtime(
        model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off", approval_mode="deny"
    )
    history = (
        "Previous conversation context:\n"
        + json.dumps({"messages": [{"role": "assistant", "content": BODY}]}, ensure_ascii=False)
        if case["category"] == "app"
        else ""
    )
    try:
        if case["id"] == 42:
            runtime._context(tmp_path).owner._app_services.content.create(
                {"title": "RoPE 研究资料", "content": BODY, "status": "knowledge"}
            )
        if case["reuse_folder"]:
            runtime._context(tmp_path).owner._app_services.knowledge.ensure_folder(
                {"name": "模型原理"}
            )
        list(runtime.stream_session(case["query"], str(uuid4()), history, max_attempts=1))
        state = runtime.last_state
        record_property("query", case["query"])
        record_property("node_path", json.dumps(runtime.last_node_path))
        record_property("execution_result", json.dumps(state.get("execution_result", {})))
        record_property(
            "tool_receipts", json.dumps(state.get("app_receipts", []), ensure_ascii=False)
        )
        assert state["execution_path"] == case["expected_path"]
        assert state["tool_scope"] == case["expected_scope"]
        events = state.get("tool_events", [])
        record_property("tool_events", json.dumps(events, ensure_ascii=False))
        assert len(events) == case["expected_steps"]
        assert all(e["ok"] for e in events)
        if case["category"] == "chat":
            assert not model.bound and not events
            return
        assert state["execution_result"]["verified"], state.get("verification")
        assert runtime.last_node_path.count("tool_execute") == case["expected_steps"]
        assert all("app_actions" in prompt and "语义匹配" in prompt for prompt in model.rule_inputs)
        if case["category"] == "app":
            assert all(tools == ["app"] for tools in model.bound)
            assert state["capability_candidates"] == []
            assert not remote_queries
        if case["category"] in {"app", "mixed"}:
            cards = runtime._app_services.content.list("knowledge")
            folders = runtime._app_services.knowledge.list_folders()
            assert len(cards) == len(folders) == 1
            assert cards[0]["content"] == BODY and cards[0]["folder_id"] == folders[0]["id"]
            assert not runtime._app_services.content.list("inbox")
            record_property(
                "database_state",
                json.dumps(
                    {
                        "cards": cards,
                        "folders": folders,
                        "inbox_count": 0,
                    },
                    ensure_ascii=False,
                ),
            )
        if case["category"] in {"fast_network", "mixed", "network_plan"}:
            assert len(remote_queries) == (3 if case["category"] == "network_plan" else 2)
        if case["category"] == "workspace":
            assert (state["workspace"] / "result.md").read_text(encoding="utf-8") == BODY
    finally:
        runtime.close()
