"""The human HTTP bridge to the same Dispatcher used by Agents."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from xiliu.api.context import request_services
from xiliu.api.errors import WebError
from xiliu.app.dispatch import AppDispatcher
from xiliu.execution.gateway import RunContext
from xiliu.policy.engine import PolicyEngine
from xiliu.tools.app import AppInput

router = APIRouter(prefix="/api/app")


class AppRequest(AppInput):
    session_id: str


class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    confirmation_id: str


def _dispatcher(request: Request, session_id: str) -> AppDispatcher:
    state = request_services(request)
    state.store.get(session_id)
    cloud = getattr(state, "cloud_mode", False)
    if cloud:
        from xiliu.cloud.policy import CloudPolicyEngine

        policy = CloudPolicyEngine()
    else:
        policy = PolicyEngine(state.data_dir / "policy.json")
    context = RunContext(
        "http:" + session_id,
        session_id,
        state.data_dir,
        data_dir=state.data_dir,
        app_services=state.app_services,
        policy_engine=policy,
        policy_profile="cloud" if cloud else "interactive",
    )
    return AppDispatcher(state.app_services, context)


@router.post("")
def app_action(body: AppRequest, request: Request):
    dispatch = _dispatcher(request, body.session_id)
    if body.operation == "catalog":
        return dispatch.catalog()
    if body.operation == "describe":
        return dispatch.describe(body.action_id or "")
    return dispatch.execute(
        body.action_id or "",
        body.arguments,
        request_id=body.request_id,
        confirmation_id=body.confirmation_id,
    )


@router.post("/confirm")
def confirm_action(body: Confirmation, request: Request):
    result = _dispatcher(request, body.session_id).confirm(body.confirmation_id)
    if result.get("error") == "confirmation_invalid":
        raise WebError("confirmation_invalid", "确认已失效或不属于当前对话。", 403)
    text = "已确认并完成操作。" if result["ok"] else "操作未完成，请检查结果。"
    result.update(confirmation_id=body.confirmation_id, confirmation_resolved=True)
    request_services(request).store.append_message(
        body.session_id, "assistant", text, metadata={"app_receipts": [result]}
    )
    return result
