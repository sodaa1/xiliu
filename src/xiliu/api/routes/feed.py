from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/feed")


class ManualCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: str
    title: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    fetch_title: bool = False


class ManualUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: str | None = None
    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    fetch_title: bool = False


@router.get("")
def feed(request: Request, source: str = "", q: str = "", include_hidden: bool = False):
    return request.app.state.feed.list(source=source, q=q, include_hidden=include_hidden)


@router.post("/refresh")
def refresh_feed(request: Request):
    return request.app.state.feed.refresh()


@router.post("/manual", status_code=201)
def add_manual(body: ManualCreate, request: Request):
    return request.app.state.feed.add_manual(body.model_dump())


@router.patch("/manual/{item_id}")
def update_manual(item_id: str, body: ManualUpdate, request: Request):
    return request.app.state.feed.update_manual(item_id, body.model_dump(exclude_unset=True))


@router.delete("/manual/{item_id}")
def remove_manual(item_id: str, request: Request):
    return request.app.state.feed.remove_manual(item_id)


@router.post("/manual/{item_id}/restore")
def restore_manual(item_id: str, request: Request):
    return request.app.state.feed.restore_manual(item_id)


@router.post("/{item_id}/hide")
def hide_external(item_id: str, request: Request):
    return request.app.state.feed.hide_external(item_id)


@router.post("/{item_id}/unhide")
def unhide_external(item_id: str, request: Request):
    return request.app.state.feed.unhide_external(item_id)


@router.post("/{item_id}/save")
def save_feed(item_id: str, request: Request):
    return request.app.state.feed.save(item_id)


@router.post("/{item_id}/summarize")
def summarize_feed(item_id: str, request: Request):
    return request.app.state.feed.summarize(item_id)
