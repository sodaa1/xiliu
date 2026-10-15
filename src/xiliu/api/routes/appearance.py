import json

from fastapi import APIRouter, Request, Response

from xiliu.api.errors import WebError

router = APIRouter(prefix="/api/appearance")


async def limited_body(request: Request, maximum: int):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > maximum:
            raise WebError("media_too_large", "导入内容超过大小限制。", 413)
        chunks.append(chunk)
    return b"".join(chunks)


async def json_body(request: Request, maximum: int):
    try:
        return json.loads(await limited_body(request, maximum))
    except (ValueError, UnicodeDecodeError):
        raise WebError("invalid_media", "导入格式无效。") from None


@router.get("/backgrounds")
def backgrounds(request: Request):
    return request.app.state.appearance.backgrounds()


@router.post("/backgrounds", status_code=201)
async def add_background(request: Request, name: str):
    return request.app.state.appearance.add_background(
        name, await limited_body(request, 20 * 1024 * 1024)
    )


@router.put("/backgrounds/selection")
async def select_background(request: Request):
    return request.app.state.appearance.select_background(await json_body(request, 4096))


@router.get("/backgrounds/{identifier}")
def background(identifier: str, request: Request):
    data, mime = request.app.state.appearance.background(identifier)
    return Response(
        data,
        media_type=mime,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=31536000, immutable",
        },
    )


@router.delete("/backgrounds/{identifier}", status_code=204)
def delete_background(identifier: str, request: Request):
    request.app.state.appearance.delete_background(identifier)
    return Response(status_code=204)


@router.get("/models/{form}")
def model(form: str, request: Request):
    return request.app.state.appearance.model(form)


@router.put("/models/{form}")
async def save_model(form: str, request: Request):
    return request.app.state.appearance.save_model(
        form, await json_body(request, 280 * 1024 * 1024)
    )


@router.delete("/models/{form}", status_code=204)
def delete_model(form: str, request: Request):
    request.app.state.appearance.delete_model(form)
    return Response(status_code=204)


@router.get("/model-assets/{form}")
def model_file(form: str, path: str, request: Request):
    data, mime = request.app.state.appearance.model_file(form, path)
    return Response(
        data,
        media_type=mime,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
    )
