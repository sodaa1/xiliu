from __future__ import annotations

import json
import re
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from xiliu.agents.react import _tool_result_message, create_agent_model, emit, payload, run_react
from xiliu.capabilities.langchain_tools import build_meta_tools
from xiliu.errors import MemoryBudgetError
from xiliu.execution.cancellation import TurnCancelled, check_cancelled
from xiliu.execution.gateway import wrap_tools
from xiliu.graph.routing import external_scope, local_scope
from xiliu.prompts import SEARCH_AGENT_PROMPT
from xiliu.tools.app import build_app_tool
from xiliu.tools.web_search_tool import WebSearchTool


def mcp_source_urls(data: dict) -> list[str]:
    if data.get("ok") is not True or data.get("is_error") is True:
        return []
    content = data.get("text", "")
    structured = data.get("structured_content")
    if structured is not None:
        content += " " + json.dumps(structured, ensure_ascii=False)
    return list(
        dict.fromkeys(
            url.rstrip(".,;)]}\"'") for url in re.findall(r"https?://[^\s<>\"']+", content)
        )
    )


def run_search_agent(state, instruction, *, writer=None, max_loops=4) -> dict:
    messages = [
        SystemMessage(
            content=SEARCH_AGENT_PROMPT
            + "\nUse the available web_search directly for current facts, including weather. "
            "A dedicated weather MCP is not required. Discover MCP only for a requested MCP source."
        ),
        HumanMessage(
            content=json.dumps(
                {
                    "task": state["task"],
                    "instruction": instruction,
                    "research_notes": state.get("research_notes", []),
                },
                ensure_ascii=False,
            )
        ),
    ]
    empty_discovery = False
    search_attempted = False

    def stop_empty_discovery(event):
        nonlocal empty_discovery, search_attempted
        if event["tool"] in {"web_search", "mcp_call"}:
            search_attempted = True
        elif (
            not search_attempted
            and event["tool"] == "capability_search"
            and event["args"].get("kind", "") in {"", "mcp"}
            and event["ok"]
            and payload(event["output"]).get("results") == []
        ):
            empty_discovery = True
            return "No matching MCP capability"
        return None

    try:
        tools = wrap_tools(
            [
                WebSearchTool(),
                build_app_tool(allowed_actions={"knowledge.search", "knowledge.get"}),
                *build_meta_tools(role="search_agent"),
            ]
        )
        result = run_react(
            create_agent_model(),
            tools,
            messages,
            agent="search_agent",
            attempt=state.get("attempt", 0),
            writer=writer,
            max_loops=max_loops,
            after_tool=stop_empty_discovery,
        )
        if empty_discovery and external_scope(state["task"]) and not local_scope(state["task"]):
            # One real, audited call through the same Gateway; no repeated discovery or model loop.
            tool = next(tool for tool in tools if tool.name == "web_search")
            _web_fallback(
                result, tool, state["task"].strip()[:2_000], state.get("attempt", 0), writer
            )
    except (MemoryBudgetError, TurnCancelled):
        raise
    except Exception:
        result = {
            "ok": False,
            "summary": "Search agent initialization failed",
            "messages": messages,
            "tool_events": [],
        }
    queries, sources, answers = [], [], []
    for event in result["tool_events"]:
        if event["tool"] == "mcp_call":
            data = payload(event["output"])
            if event["ok"]:
                query = event["args"].get("capability_id")
                if query and query not in queries:
                    queries.append(query)
                answers.append(data.get("text", ""))
                for url in mcp_source_urls(data):
                    if url not in sources:
                        sources.append(url)
            continue
        if event["tool"] != "web_search":
            continue
        data = payload(event["output"])
        query = event["args"].get("query")
        if query and query not in queries:
            queries.append(query)
        if data.get("ok"):
            answers.append(data.get("answer", ""))
            for source in data.get("results", []):
                url = source.get("url")
                if url and url not in sources:
                    sources.append(url)
    result.update(queries=queries, sources=sources, answers=answers)
    if result["summary"] == "Agent loop limit reached" and sources:
        fallback = "\n\n".join(answer.strip() for answer in answers if answer.strip())
        result["summary"] = fallback[:8_000] or f"Research collected {len(sources)} source(s)."
        result["ok"] = True
    else:
        result["ok"] = result["ok"] and bool(sources)
    return result


def _web_fallback(result, tool, query, attempt, writer) -> None:
    check_cancelled()
    call_id = uuid4().hex
    args = {"query": query}
    emit(
        writer,
        {
            "type": "tool_call",
            "stage": "search_agent",
            "message": "search_agent: web_search",
            "tool": "web_search",
            "args": args,
        },
    )
    try:
        raw = tool.invoke(args)
        output = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    except (MemoryBudgetError, TurnCancelled):
        raise
    except Exception:
        output = json.dumps({"ok": False, "error": "search failed", "retryable": True})
    check_cancelled()
    data = payload(output)
    ok = data.get("ok") is True
    ok = ok and not data.get("timed_out") and not data.get("truncated")
    event = {
        "event_id": f"fallback:{call_id}",
        "agent": "search_agent",
        "tool": "web_search",
        "args": args,
        "output": output,
        "ok": bool(ok),
        "attempt": attempt,
        "phase": data.get("phase"),
    }
    result["tool_events"].append(event)
    result["messages"].extend(
        [
            AIMessage(content="", tool_calls=[{"id": call_id, "name": "web_search", "args": args}]),
            ToolMessage(content=output, tool_call_id=call_id, name="web_search"),
        ]
    )
    emit(
        writer,
        {
            **event,
            "type": "search_results",
            "stage": "search_agent",
            "message": _tool_result_message("search_agent", "web_search", bool(ok), data),
        },
    )
    result["ok"] = bool(ok)
    if ok:
        result["summary"] = str(data.get("answer") or "Web search completed")[:8_000]
        result["retryable"] = False
        if not data.get("results"):
            result["summary"] = "Web search returned no source URLs"
    else:
        result["summary"] = _tool_result_message("search_agent", "web_search", False, data)
        result["retryable"] = data.get("retryable") is not False
        result["error"] = result["summary"].removeprefix("search_agent: ")
