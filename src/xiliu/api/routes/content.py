from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/content")


@router.get("")
def list_content(request: Request, status: str = "inbox", q: str = "", tag: str = ""):
    return request.app.state.content.list(status=status, q=q, tag=tag)


@router.post("", status_code=201)
def create_content(body: dict[str, Any], request: Request):
    return request.app.state.content.create(body)


@router.get("/{item_id}")
def get_content(item_id: str, request: Request):
    return request.app.state.content.get(item_id)


@router.patch("/{item_id}")
def update_content(item_id: str, body: dict[str, Any], request: Request):
    return request.app.state.content.update(item_id, body)


@router.delete("/{item_id}", status_code=204)
def delete_content(item_id: str, request: Request):
    request.app.state.content.delete(item_id)
    return Response(status_code=204)


@router.get("/{item_id}/original")
def original_content(item_id: str, request: Request):
    service = request.app.state.content
    path = service.original(item_id)
    return FileResponse(
        path, filename=service.get(item_id)["filename"], media_type="application/octet-stream"
    )
