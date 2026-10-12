import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from xiliu.agents.react import content_text, payload, unresolved_failures
from xiliu.app.actions import get_registry
from xiliu.execution.gateway import active_run
from xiliu.graph.goal_verification import goal_failure
from xiliu.graph.nodes.common import VerifierOutput
from xiliu.graph.verification import requirements_failure
from xiliu.prompts import VERIFIER_NODE_PROMPT


def execution_verifier_node(state, *, model, memory_manager):
    path = state.get("execution_path")
    events = [e for e in state.get("tool_events", []) if e["attempt"] == state["attempt"]]
    status = state.get("execution_result", {}).get("status", "running")
    reason = None
    context = active_run.get()
    if status in {"clarification_required", "confirmation_required"}:
        reason = state.get("result") or "需要明确对象或由用户确认。"
    elif not state.get("execution_ok"):
        reason = state.get("result") or "Execution did not finish a valid round"
    elif not events:
        reason = "Missing actual execution evidence"
    elif unresolved_failures(events):
        reason = "Unresolved failed or incomplete tool action"
    if reason is None:
        changed_objects = set()
        for event in reversed(events):
            if event["tool"] != "app" or event["args"].get("operation") != "execute":
                continue
            receipt = payload(event["output"])
            if receipt.get("ok") is not True or not receipt.get("verification", {}).get("passed"):
                reason = "App action did not complete a verified receipt"
                break
            spec = get_registry().get(event["args"].get("action_id", ""))
            if spec and spec.side_effect == "read":
                # A read receipt is a verified historical snapshot. A later
                # legal write can supersede it without invalidating the run.
                continue
            arguments = event["args"].get("arguments", {})
            domain = spec.domain if spec else ""
            if domain in {"inbox", "content"} or spec and spec.id.startswith("knowledge.items."):
                domain = "content"
            objects = {
                (domain, str(r["id"])) for r in receipt.get("records", []) if r.get("id")
            } | {
                (domain, str(arguments[key]))
                for key in ("item_id", "task_id", "folder_id", "cid")
                if arguments.get(key)
            }
            if objects and objects <= changed_objects:
                continue
            value = receipt.get("data")
            # A batch may have only some records superseded by later writes.
            # Recheck the remaining records while the latest receipts cover the others.
            if objects.intersection(changed_objects):

                def remaining(records, domain=domain):
                    return [
                        r
                        for r in records
                        if not isinstance(r, dict)
                        or (domain, str(r.get("id", ""))) not in changed_objects
                    ]

                if isinstance(value, list):
                    value = remaining(value)
                elif isinstance(value, dict):
                    value = {
                        key: remaining(records)
                        if key in {"items", "records"} and isinstance(records, list)
                        else records
                        for key, records in value.items()
                    }
            changed_objects.update(objects)
            try:
                if (
                    spec is None
                    or context is None
                    or not spec.postcondition(
                        context.app_services,
                        event["args"].get("arguments", {}),
                        value,
                    )
                ):
                    reason = "App receipt no longer matches persisted state"
                    break
            except Exception:
                reason = "Could not verify persisted App state"
                break
    if reason is None and context and context.hook_failures:
        reason = "Blocking hook failed: " + ", ".join(context.hook_failures)
    if (
        reason is None
        and re.search(r"归档|\barchive\b", state["task"], re.I)
        and not any(
            e.get("ok")
            and e.get("args", {}).get("action_id")
            in {
                "inbox.classify_selected",
                "inbox.classify_all",
                "inbox.move",
                "inbox.archive_after_metadata",
                "content.move_to_inbox",
            }
            for e in events
        )
    ):
        reason = "Missing persisted archive action evidence"
    if path in {"fast_react", "planner"} and reason is None:
        reason = goal_failure(state, events)
    if path == "planner" and reason is None:
        reason = requirements_failure(state)
        if reason is None:
            try:
                memory = memory_manager.assemble(state, current_node="verifier")
                response = model.invoke(
                    [
                        SystemMessage(content=VERIFIER_NODE_PROMPT),
                        HumanMessage(
                            content=json.dumps(
                                {
                                    "memory": memory,
                                    "result": state.get("result", ""),
                                    "actual_execution_receipts": [
                                        {
                                            **event,
                                            "output": event["output"][:4000],
                                            "output_truncated": len(event["output"]) > 4000,
                                        }
                                        for event in events
                                    ],
                                },
                                ensure_ascii=False,
                            )
                        ),
                    ]
                )
                parsed = VerifierOutput.model_validate_json(content_text(response.content))
                if parsed.status != "passed":
                    reason = parsed.reason
            except Exception:
                reason = "Verifier returned invalid output or model request failed"
    passed = reason is None
    if status == "running" or (not passed and status in {"completed", "pending"}):
        status = "completed" if passed else "failed"
    explanation = reason or "Verified actual execution receipts and persisted state"
    return {
        "graph_state": "passed" if passed else "failed",
        "verification": explanation,
        "verifier_summary": explanation,
        "attempt": state["attempt"],
        "execution_result": {
            **state.get("execution_result", {}),
            "status": status,
            "verified": passed,
            "reason": explanation,
        },
        "current_node": "verifier",
        "last_error": "" if passed else explanation,
        "memory": memory_manager.assemble(state, current_node="verifier"),
    }


def clarification_node(state):
    reason = state.get("clarification_reason") or state.get("verification") or state.get("result")
    if not reason or reason == "Tool failed or execution budget exceeded":
        reason = "请明确操作的对象、范围和目标；尚未完成本次任务。"
    return {
        "result": reason,
        "execution_path": state.get("execution_path", "clarification"),
        "execution_result": {
            **state.get("execution_result", {}),
            "status": "clarification_required",
            "verified": False,
        },
        "graph_state": "failed",
    }


def final_node(state, *, memory_manager=None):
    answer = state.get("chat_response") or state.get("result", "")
    if (
        state.get("execution_path") == "app_executor"
        and state.get("execution_result", {}).get("status") == "failed"
    ):
        answer = "操作未完成：" + state.get("verification", answer)
    if state.get("execution_path") in {"fast_react", "planner"}:
        if state.get("graph_state") != "passed":
            answer = (
                f"任务未完成（{state.get('attempt', 0)}/{state.get('max_attempts', 3)}）："
                + state.get("verification", answer)
            )
        else:
            structured = payload(answer)
            if structured.get("ready_for_verification") is True and isinstance(
                structured.get("summary"), str
            ):
                answer = structured["summary"]
                answer = (
                    f"状态：passed\n尝试次数：{state['attempt']}/{state['max_attempts']}\n" + answer
                )
            elif state.get("execution_path") == "planner":
                answer = (
                    f"状态：passed\n尝试次数：{state['attempt']}/{state['max_attempts']}\n" + answer
                )
            evidence = state.get("evidence", [])
            sources = list(
                dict.fromkeys(
                    f"- {e.get('title') or e['source_id']}（{e['source_id']}）"
                    for e in evidence
                    if e.get("tool_ok") and e.get("matched") and e.get("source_id")
                )
            )
            if sources:
                answer += "\n\n来源：\n" + "\n".join(sources)
            elif any(e.get("matched") is False and e.get("source_type") for e in evidence):
                answer = "本次检索未找到相关资料。"
    result = {"final_answer": answer, "current_node": "final"}
    if memory_manager:
        result["memory"] = memory_manager.assemble(state, current_node="final")
    return result
