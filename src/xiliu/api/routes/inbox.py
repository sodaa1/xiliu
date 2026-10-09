from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/inbox")


@router.get("")
def list_inbox(request: Request, q: str = "", tag: str = ""):
    return request.app.state.content.list(status="inbox", q=q, tag=tag)


@router.post("/import", status_code=201)
def import_item(body: dict[str, Any], request: Request):
    return request.app.state.inbox.import_item(body)


@router.post("/classify-batch")
def classify_batch(body: dict[str, Any], request: Request):
    return request.app.state.inbox.classify_batch(body.get("item_ids"))


@router.post("/{item_id}/retry")
def retry(item_id: str, request: Request):
    return request.app.state.inbox.retry(item_id)
