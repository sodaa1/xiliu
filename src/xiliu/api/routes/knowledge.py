from typing import Any

from fastapi import APIRouter, Request, Response

from xiliu.api.services.content import _invalid

router = APIRouter(prefix="/api/knowledge")


@router.get("/folders")
def list_folders(request: Request):
    return request.app.state.knowledge.list_folders()


@router.post("/folders", status_code=201)
def create_folder(body: dict[str, Any], request: Request):
    return request.app.state.knowledge.create_folder(body)


@router.get("/folders/{folder_id}")
def get_folder(folder_id: str, request: Request):
    return request.app.state.knowledge.get_folder(folder_id)


@router.patch("/folders/{folder_id}")
def update_folder(folder_id: str, body: dict[str, Any], request: Request):
    return request.app.state.knowledge.update_folder(folder_id, body)


@router.delete("/folders/{folder_id}", status_code=204)
def delete_folder(folder_id: str, request: Request):
    request.app.state.knowledge.delete_folder(folder_id)
    return Response(status_code=204)


@router.get("/folders/{folder_id}/items")
def folder_items(folder_id: str, request: Request, q: str = "", tag: str = ""):
    return request.app.state.knowledge.folder_items(folder_id, q=q, tag=tag)


@router.get("/search")
def search(request: Request, q: str, mode: str = "auto", limit: int = 6):
    try:
        return request.app.state.retrieval.search(q, limit=limit, mode=mode)
    except ValueError:
        raise _invalid("检索参数无效，请检查查询、模式和数量。") from None
