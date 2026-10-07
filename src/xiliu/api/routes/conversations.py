import json

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from xiliu.api.schemas import ChatRequest, ConversationUpdate

router = APIRouter(prefix="/api/conversations")


@router.get("")
def list_conversations(request: Request):
    return request.app.state.store.list()


@router.post("", status_code=201)
def create_conversation(request: Request):
    return request.app.state.store.create()


@router.get("/{cid}")
def get_conversation(cid: str, request: Request):
    return request.app.state.conversations.get(cid)


@router.patch("/{cid}")
def update_conversation(cid: str, body: ConversationUpdate, request: Request):
    with request.app.state.chat.reserve(cid):
        return request.app.state.conversations.update(cid, body.model_dump(exclude_unset=True))


@router.delete("/{cid}", status_code=204)
def delete_conversation(cid: str, request: Request):
    with request.app.state.chat.reserve(cid):
        request.app.state.store.delete(cid)
    return Response(status_code=204)


@router.get("/{cid}/messages")
def messages(cid: str, request: Request):
    return request.app.state.store.messages(cid)


@router.post("/{cid}/chat")
def chat(cid: str, body: ChatRequest, request: Request):
    request.app.state.store.get(cid)

    def lines():
        for event in request.app.state.chat.stream_turn(cid, body.text):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        lines(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
