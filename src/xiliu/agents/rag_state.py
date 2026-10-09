from typing import TypedDict


class RAGState(TypedDict):
    queries: list[str]
    hits: list[dict]
    tool_events: list[dict]
    iteration: int
    answer_supported: bool
