from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/settings/preferences")


class PreferenceRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0, strict=True)


class PreferenceUpdate(PreferenceRevision):
    changes: dict[str, Any]


@router.get("")
def get_preferences(request: Request):
    return request.app.state.preferences.get()


@router.put("")
def update_preferences(body: PreferenceUpdate, request: Request):
    return request.app.state.preferences.update(body.changes, body.expected_revision)


@router.post("/reset")
def reset_preferences(body: PreferenceRevision, request: Request):
    return request.app.state.preferences.reset(body.expected_revision)
