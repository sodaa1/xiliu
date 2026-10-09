from __future__ import annotations

import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from dotenv import dotenv_values, set_key

from xiliu.api.errors import WebError
from xiliu.api.model_catalog import MODEL_CATALOG
from xiliu.api.schemas import ModelUpdate
from xiliu.config import Settings
from xiliu.errors import ConfigError


class ModelSettingsService:
    def __init__(self, env_file: Path = Path(".env")):
        self.env_file = env_file.resolve()
        self._lock = RLock()

    def values(self) -> dict[str, str]:
        with self._lock:
            values = {
                key: value
                for key, value in dotenv_values(self.env_file).items()
                if value is not None
            }
            values.update(os.environ)
            return values

    @staticmethod
    def _provider(values: dict[str, str]) -> str:
        explicit = values.get("XILIU_PROVIDER", "").strip()
        if explicit in MODEL_CATALOG:
            return explicit
        model = values.get("XILIU_MODEL", "")
        address = values.get("XILIU_BASE_URL", "")
        return (
            "deepseek" if model.startswith("deepseek-") or "deepseek.com" in address else "openai"
        )

    def _effective(self, values: dict[str, str]) -> dict[str, str]:
        provider = self._provider(values)
        catalog = MODEL_CATALOG[provider]
        model = values.get("XILIU_MODEL", "") or catalog["models"][0]
        if provider == "deepseek" and model == "deepseek-flash":
            model = "deepseek-v4-flash"
        return {
            "provider": provider,
            "model": model,
            "base_url": values.get("XILIU_BASE_URL", "") or catalog["base_url"],
        }

    def read(self) -> dict[str, Any]:
        values = self.values()
        return {
            **self._effective(values),
            "api_key_set": bool(values.get("XILIU_API_KEY", "").strip()),
        }

    def update(self, update: ModelUpdate) -> dict[str, Any]:
        if update.model not in MODEL_CATALOG[update.provider]["models"]:
            raise WebError("invalid_model", "模型不属于所选厂商。")
        changes = {
            "XILIU_PROVIDER": update.provider,
            "XILIU_MODEL": update.model,
            "XILIU_BASE_URL": update.base_url,
        }
        if update.api_key and update.api_key.get_secret_value().strip():
            changes["XILIU_API_KEY"] = update.api_key.get_secret_value().strip()
        with self._lock:
            self.env_file.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".env-", dir=self.env_file.parent)
            os.close(fd)
            staged = Path(temporary)
            try:
                staged.write_text(
                    self.env_file.read_text(encoding="utf-8") if self.env_file.exists() else "",
                    encoding="utf-8",
                )
                for key, value in changes.items():
                    set_key(staged, key, value, quote_mode="always")
                os.replace(staged, self.env_file)
            finally:
                staged.unlink(missing_ok=True)
        return self.read()

    def runtime_settings(self, model: str | None = None) -> Settings:
        values = self.values()
        effective = self._effective(values)
        values.update({f"XILIU_{key.upper()}": value for key, value in effective.items()})
        if model:
            values["XILIU_MODEL"] = model
        try:
            return Settings.from_env(values)
        except ConfigError:
            raise WebError("model_not_configured", "请先在 Settings 配置模型接口。", 400) from None
