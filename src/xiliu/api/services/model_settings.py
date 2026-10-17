from __future__ import annotations

import hashlib
import json
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
        model = values.get("XILIU_MODEL", "") or next(iter(catalog["models"]), "")
        if provider == "deepseek" and model == "deepseek-flash":
            model = "deepseek-v4-flash"
        return {
            "provider": provider,
            "model": model,
            "base_url": values.get("XILIU_BASE_URL", "") or catalog["base_url"],
        }

    def read(self, model: str | None = None) -> dict[str, Any]:
        values = self.values()
        connections = self._connections(values)
        selected = self._selected_connection(model, connections, values)
        return {
            **(
                {key: selected[key] for key in ("provider", "model", "base_url")}
                if selected
                else self._effective(values)
            ),
            "api_key_set": bool(
                (selected["api_key"] if selected else values.get("XILIU_API_KEY", "")).strip()
            ),
            "connections": [self._public_connection(c) for c in connections.values()],
            "profiles": {
                provider: {
                    "model": profile["model"],
                    "base_url": profile["base_url"],
                    "api_key_set": bool(profile["api_key"].strip()),
                }
                for provider in MODEL_CATALOG
                for profile in [self._profile(provider, values)]
            },
        }

    def _profile(self, provider: str, values: dict[str, str]) -> dict[str, str]:
        prefix = f"XILIU_{provider.upper()}_"
        if provider == self._provider(values):
            effective = self._effective(values)
            return {**effective, "api_key": values.get("XILIU_API_KEY", "")}
        catalog = MODEL_CATALOG[provider]
        return {
            "model": values.get(prefix + "MODEL", "") or next(iter(catalog["models"]), ""),
            "base_url": values.get(prefix + "BASE_URL", "") or catalog["base_url"],
            "api_key": values.get(prefix + "API_KEY", ""),
        }

    def _selected_connection(self, model, connections, values):
        if not model:
            return None
        if model in connections:
            return connections[model]
        return next(
            (
                connection
                for connection in connections.values()
                if connection["provider"] == self._provider(values) and connection["model"] == model
            ),
            None,
        )

    @staticmethod
    def _connection_id(provider: str, model: str, address: str) -> str:
        if provider == "custom":
            return "custom:" + hashlib.sha256(f"{address}\n{model}".encode()).hexdigest()[:16]
        return f"{provider}:{model}"

    @staticmethod
    def _public_connection(connection: dict) -> dict:
        return {
            **{k: connection[k] for k in ("id", "label", "provider", "model", "base_url")},
            "api_key_set": bool(connection["api_key"].strip()),
            "enabled": connection.get("enabled", True),
        }

    def _connections(self, values: dict[str, str]) -> dict[str, dict]:
        try:
            saved = json.loads(values.get("XILIU_MODEL_CONNECTIONS", "{}"))
            if not isinstance(saved, dict):
                raise ValueError("invalid configuration")
            for value in saved.values():
                if not isinstance(value, dict) or any(
                    not isinstance(value.get(k), str)
                    for k in ("id", "label", "provider", "model", "base_url", "api_key")
                ):
                    raise ValueError("invalid connection")
        except (ValueError, TypeError):
            raise WebError(
                "invalid_model_settings", "模型连接配置无法读取，请检查本机配置。"
            ) from None
        for provider, catalog in MODEL_CATALOG.items():
            profile = self._profile(provider, values)
            for model in catalog["models"]:
                identifier = self._connection_id(provider, model, profile["base_url"])
                saved.setdefault(
                    identifier,
                    {
                        "id": identifier,
                        "label": model,
                        "provider": provider,
                        "model": model,
                        "base_url": profile["base_url"],
                        "api_key": profile["api_key"],
                    },
                )
        current = self._effective(values)
        if current["model"]:
            identifier = values.get("XILIU_CONNECTION_ID") or self._connection_id(
                current["provider"], current["model"], current["base_url"]
            )
            saved.setdefault(
                identifier,
                {
                    "id": identifier,
                    "label": current["model"],
                    **current,
                    "api_key": values.get("XILIU_API_KEY", ""),
                },
            )
        return saved

    def update(self, update: ModelUpdate) -> dict[str, Any]:
        if (
            update.provider != "custom"
            and update.model not in MODEL_CATALOG[update.provider]["models"]
        ):
            raise WebError("invalid_model", "模型不属于所选厂商。")
        with self._lock:
            values = self.values()
            current_provider = self._provider(values)
            connections = self._connections(values)
            identifier = update.profile_id or self._connection_id(
                update.provider, update.model, update.base_url
            )
            target_connection = connections.get(identifier)
            if target_connection and target_connection["provider"] != update.provider:
                raise WebError("invalid_model", "连接厂商不匹配，请新增连接。")
            target: dict[str, Any] = dict(
                target_connection
                or {"api_key": "", "model": update.model, "base_url": update.base_url}
            )
            supplied = update.api_key.get_secret_value().strip() if update.api_key else ""
            target.update(
                model=update.model, base_url=update.base_url, api_key=supplied or target["api_key"]
            )
            target.update(
                id=identifier,
                provider=update.provider,
                label=update.label or target.get("label") or update.model,
            )
            if update.enabled is not None:
                target["enabled"] = update.enabled
            active = self._effective(values)
            active_id = values.get("XILIU_CONNECTION_ID") or self._connection_id(
                active["provider"], active["model"], active["base_url"]
            )
            if not target.get("enabled", True) and (update.make_default or identifier == active_id):
                raise WebError("default_model_disabled", "请先更换默认模型，再停用此模型。")
            connections[identifier] = target
            # Preserve the legacy active profile before switching; never borrow its key.
            changes = {
                f"XILIU_{provider.upper()}_{field.upper()}": value
                for provider, profile in (
                    (current_provider, self._profile(current_provider, values)),
                    (update.provider, target),
                )
                for field, value in profile.items()
                if field in {"model", "base_url", "api_key"}
            }
            changes["XILIU_MODEL_CONNECTIONS"] = json.dumps(connections, ensure_ascii=False)
            active = self._effective(values)
            active_id = values.get("XILIU_CONNECTION_ID") or self._connection_id(
                active["provider"], active["model"], active["base_url"]
            )
            if update.make_default or identifier == active_id:
                changes.update(
                    {
                        "XILIU_PROVIDER": update.provider,
                        "XILIU_CONNECTION_ID": identifier,
                        **{
                            f"XILIU_{field.upper()}": target[field]
                            for field in ("model", "base_url", "api_key")
                        },
                    }
                )
            self._write_values(changes)
        return self.read()

    def _write_values(self, changes: dict[str, str]) -> None:
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

    def _settings_from_values(self, values: dict[str, str]) -> Settings:
        return Settings.from_env(values)

    def runtime_settings(self, model: str | None = None) -> Settings:
        values = self.values()
        effective = self._effective(values)
        selected = self._selected_connection(model, self._connections(values), values)
        if selected and not selected.get("enabled", True):
            raise WebError("model_disabled", "此模型已停用，请切换模型或在设置中重新启用。", 400)
        if selected:
            effective = {k: selected[k] for k in ("provider", "model", "base_url")}
            values["XILIU_API_KEY"] = selected["api_key"]
        values.update({f"XILIU_{key.upper()}": value for key, value in effective.items()})
        if model and not selected:
            values["XILIU_MODEL"] = model
        try:
            return self._settings_from_values(values)
        except ConfigError:
            raise WebError("model_not_configured", "请先在设置中配置模型接口。", 400) from None
