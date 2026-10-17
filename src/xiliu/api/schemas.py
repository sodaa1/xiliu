from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class ModelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["openai", "deepseek", "mimo", "custom"]
    model: str = Field(min_length=1, max_length=100)
    base_url: str = Field(max_length=2048)
    api_key: SecretStr | None = None
    profile_id: str | None = Field(default=None, min_length=1, max_length=200)
    label: str = Field(default="", max_length=100)
    make_default: bool = True
    enabled: bool | None = None

    @field_validator("base_url")
    @classmethod
    def valid_base_url(cls, value: str) -> str:
        value = value.strip()
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ValueError("API address must use http or https")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("API address must not contain credentials, query or fragment")
        return value.rstrip("/")


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    model_override: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("title must not be blank")
        return value.strip() if value else value


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=100_000)
    context: str = Field(default="", max_length=40_000)
    source: Literal["own", "trial"] = "own"
    request_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,100}$")

    @field_validator("text")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value.strip()
