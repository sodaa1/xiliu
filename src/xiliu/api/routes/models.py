from fastapi import APIRouter, Request

from xiliu.api.context import request_services
from xiliu.api.model_catalog import MODEL_CATALOG
from xiliu.api.schemas import ModelUpdate

router = APIRouter(prefix="/api")


@router.get("/models/catalog")
def catalog():
    return MODEL_CATALOG


@router.get("/settings/model")
def get_model(request: Request):
    return request_services(request).model_settings.read()


@router.put("/settings/model")
def put_model(body: ModelUpdate, request: Request):
    return request_services(request).model_settings.update(body)
