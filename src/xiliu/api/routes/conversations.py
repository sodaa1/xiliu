import asyncio
import json
from contextlib import nullcontext, suppress
from threading import Event, Thread

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from xiliu.api.context import request_services
from xiliu.api.errors import WebError
from xiliu.api.schemas import ChatRequest, ConversationUpdate

router = APIRouter(prefix="/api/conversations")


@router.get("")
def list_conversations(request: Request):
    return request_services(request).store.list()


@router.post("", status_code=201)
def create_conversation(request: Request):
    return request_services(request).store.create()


@router.get("/{cid}")
def get_conversation(cid: str, request: Request):
    return request_services(request).conversations.get(cid)


@router.patch("/{cid}")
def update_conversation(cid: str, body: ConversationUpdate, request: Request):
    with request_services(request).chat.reserve(cid):
        return request_services(request).conversations.update(
            cid, body.model_dump(exclude_unset=True)
        )


@router.delete("/{cid}", status_code=204)
def delete_conversation(cid: str, request: Request):
    with request_services(request).chat.reserve(cid):
        request_services(request).store.delete(cid)
    return Response(status_code=204)


@router.get("/{cid}/messages")
def messages(cid: str, request: Request):
    return request_services(request).store.messages(cid)


@router.post("/{cid}/chat")
async def chat(cid: str, body: ChatRequest, request: Request):
    request_services(request).store.get(cid)

    async def lines():
        # One owner thread keeps generator ContextVars stable and lets disconnects
        # signal cancellation even while a provider request is waiting for data.
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        signal = Event()

        def publish(event):
            with suppress(RuntimeError):
                loop.call_soon_threadsafe(queue.put_nowait, event)

        def produce():
            try:
                lease = request.scope.get("xiliu.workspace_lease")
                with lease() if lease else nullcontext():
                    turn = request_services(request).chat.stream_turn(
                        cid, body.text, context=body.context, signal=signal
                    )
                    try:
                        for event in turn:
                            publish(event)
                    finally:
                        turn.close()
            except WebError as error:
                publish({"type": "error", "code": error.code, "message": error.message})
            except Exception:
                publish(
                    {
                        "type": "error",
                        "code": "chat_failed",
                        "message": "对话未能完成，请稍后重试。",
                    }
                )
            finally:
                publish(None)

        Thread(target=produce, name=f"chat-{cid}", daemon=True).start()
        try:
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.25)
                except TimeoutError:
                    continue
                if event is None:
                    break
                yield json.dumps(event, ensure_ascii=False) + "\n"
        finally:
            signal.set()

    return StreamingResponse(
        lines(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{cid}/stop")
def stop(cid: str, request: Request):
    return request_services(request).chat.cancel(cid)
