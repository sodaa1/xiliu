from fastapi import Request

from xiliu.api.errors import WebError


def request_services(request: Request):
    if getattr(request.app.state, "cloud_mode", False):
        state = request.scope.get("xiliu.services")
        if state is None:
            raise WebError("login_required", "请先登录。", 401)
        return state
    return request.app.state
