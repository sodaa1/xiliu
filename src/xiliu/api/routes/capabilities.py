from fastapi import APIRouter, Request

from xiliu.api.context import request_services
from xiliu.api.services.commands import COMMANDS

router = APIRouter(prefix="/api")


@router.get("/commands")
def commands():
    return COMMANDS


@router.get("/capabilities/skills")
def skills(request: Request):
    return request_services(request).commands.skills()


@router.get("/capabilities/mcp")
def mcp(request: Request):
    return request_services(request).commands.mcp()
