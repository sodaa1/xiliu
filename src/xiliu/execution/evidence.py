"""Explicit, replay-safe mapping of actual tool outputs into shared evidence."""

from __future__ import annotations

from typing import Any

from xiliu.agents.react import payload


def _merge(left: list[dict], right: list[dict], keys: tuple[str, ...]) -> list[dict]:
    result = [dict(item) for item in left]
    positions = {
        tuple(item.get(key) for key in keys): index
        for index, item in enumerate(result)
        if item.get(keys[0])
    }
    for item in right:
        identity = tuple(item.get(key) for key in keys)
        if item.get(keys[0]) and identity in positions:
            result[positions[identity]] = dict(item)
        else:
            if item.get(keys[0]):
                positions[identity] = len(result)
            result.append(dict(item))
    return result


def merge_events_by_id(left: list[dict], right: list[dict]) -> list[dict]:
    return _merge(left, right, ("event_id",))


def merge_evidence_by_event_id(left: list[dict], right: list[dict]) -> list[dict]:
    return _merge(left, right, ("event_id", "source_id"))


def merge_agent_results_by_call_id(left: list[dict], right: list[dict]) -> list[dict]:
    return _merge(left, right, ("call_id",))


def evidence_from_events(events: list[dict]) -> list[dict[str, Any]]:
    evidence = []
    for event in events:
        # Legacy snapshots without IDs remain readable but cannot manufacture new evidence.
        if not event.get("event_id"):
            continue
        data = payload(event.get("output", ""))
        tool = event.get("tool", "")
        ok = bool(event.get("ok")) and data.get("ok") is not False
        ok = ok and not data.get("timed_out") and not data.get("truncated")
        local = tool in {"knowledge_search", "knowledge_get"}
        web = tool in {'web_search', 'mcp_call'}
        hits = data.get("hits", data.get("items", data.get("results", [])))
        if tool == 'mcp_call' and ok:
            from xiliu.agents.search_agent import mcp_source_urls
            hits = [{'url': url, 'snippet': str(data.get('text', ''))[:1000]}
                    for url in mcp_source_urls(data)]
        if tool == "knowledge_get" and isinstance(data.get("document"), dict):
            hits = [data["document"]]
        valid = []
        if ok and isinstance(hits, list):
            valid = [
                h
                for h in hits
                if isinstance(h, dict)
                and (
                    isinstance(h.get("document_id"), str) and h["document_id"].strip()
                    if local
                    else isinstance(h.get("url"), str)
                    and h["url"].startswith(("http://", "https://"))
                )
            ]
        base = {
            "event_id": event["event_id"],
            "tool_id": tool,
            "origin": event.get("agent", "unknown"),
            "tool_ok": bool(ok),
            "matched": bool(valid) if local or web else None,
            "source_type": "knowledge" if local else "web" if web else None,
            "source_id": None,
            "source_uri": None,
            "snippet": None,
        }
        if valid:
            for hit in valid:
                evidence.append(
                    {
                        **base,
                        "source_id": hit.get("document_id") or hit["url"],
                        "source_uri": hit.get("source_uri") or hit.get("url"),
                        "snippet": str(hit.get("snippet", hit.get("content", "")))[:1000],
                        "title": str(hit.get("title", ""))[:300],
                    }
                )
        else:
            evidence.append(base)
    return evidence


def state_evidence(events: list[dict]) -> dict[str, Any]:
    evidence = evidence_from_events(events)
    hits = []
    for event in events:
        if event.get("tool") == "knowledge_search":
            data = payload(event.get("output", ""))
            raw = data.get("hits", data.get("items", []))
            hits = (
                [h for h in raw if isinstance(h, dict) and h.get("document_id")]
                if (event.get("ok") and data.get("ok") is not False and isinstance(raw, list))
                else []
            )
    notes = [
        {
            "summary": e.get("snippet") or e.get("title", ""),
            "queries": [],
            "sources": [e["source_uri"] or e["source_id"]],
            "attempt": 0,
        }
        for e in evidence
        if e["tool_ok"] and e["matched"] and e["source_id"]
    ]
    return {"evidence": evidence, "retrieval_hits": hits, "research_notes": notes}
