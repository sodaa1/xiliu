from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/inbox")


class BatchClassification(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    item_ids: list[str] = Field(max_length=100)
    save_to_knowledge: bool = True
    use_ai: bool = False
    folder_id: str | None = None


@router.get("")
def list_inbox(request: Request, q: str = "", tag: str = ""):
    return request.app.state.content.list(status="inbox", q=q, tag=tag)


@router.post("/import", status_code=201)
def import_item(body: dict[str, Any], request: Request):
    return request.app.state.inbox.import_item(body)


@router.post("/classify-batch")
def classify_batch(body: BatchClassification, request: Request):
    return request.app.state.inbox.classify_batch(
        body.item_ids,
        save_to_knowledge=body.save_to_knowledge,
        use_ai=body.use_ai,
        folder_id=body.folder_id,
    )


@router.post("/{item_id}/retry")
def retry(item_id: str, request: Request):
    return request.app.state.inbox.retry(item_id)


@router.get("/archive-jobs/{job_id}")
def archive_job(job_id: str, request: Request):
    return request.app.state.inbox.get_archive_job(job_id)
