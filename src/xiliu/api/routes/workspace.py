from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from xiliu.api.context import request_services

router = APIRouter(prefix="/api")


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    completed: bool = False
    due_at: str | None = None
    scope: Literal["day", "week", "goal"] = "day"
    parent_id: str | None = None


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    completed: bool | None = None
    due_at: str | None = None
    scope: Literal["day", "week", "goal"] | None = None
    parent_id: str | None = None


class AutomationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    prompt: str
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    timezone: str = "Asia/Shanghai"


class AutomationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


@router.get("/tasks")
def tasks(request: Request):
    return request_services(request).tasks.list()


@router.post("/tasks", status_code=201)
def create_task(body: TaskCreate, request: Request):
    return request_services(request).tasks.create(body.model_dump())


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate, request: Request):
    return request_services(request).tasks.update(task_id, body.model_dump(exclude_unset=True))


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, request: Request):
    request_services(request).tasks.delete(task_id)
    return Response(status_code=204)


@router.get("/automations")
def automations(request: Request):
    return request_services(request).automations.list()


@router.post("/automations", status_code=201)
def create_automation(body: AutomationCreate, request: Request):
    return request_services(request).automations.create(body.model_dump())


@router.patch("/automations/{task_id}")
def toggle_automation(task_id: str, body: AutomationUpdate, request: Request):
    return request_services(request).automations.toggle(task_id, body.enabled)


@router.delete("/automations/{task_id}", status_code=204)
def delete_automation(task_id: str, request: Request):
    request_services(request).automations.delete(task_id)
    return Response(status_code=204)


@router.get("/automations/{task_id}/runs")
def automation_runs(task_id: str, request: Request):
    return request_services(request).automations.runs(task_id)


@router.get("/today")
def today(request: Request) -> dict[str, Any]:
    state = request_services(request)
    return {
        "feed": state.feed.list()["items"],
        "tasks": state.tasks.list(),
        "inbox_count": len(state.content.list(status="inbox")),
    }


@router.get("/settings/data")
def data_settings(request: Request) -> dict[str, Any]:
    state = request_services(request)
    return {
        "data_dir": str(state.store.path.parent.resolve()),
        "database": str(state.store.path.resolve()),
        "content_count": len(state.content.list(status="inbox"))
        + len(state.content.list(status="knowledge")),
        "scheduler_active": state.automations.scheduler_active,
    }
