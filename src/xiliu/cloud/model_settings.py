from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from xiliu.api.errors import WebError
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.config import Settings
from xiliu.tools.workspace import atomic_write_utf8


class CloudRuntimeSettings(Settings):
    cloud_mode: bool = True

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return (init_settings,)


class CloudModelSettings(ModelSettingsService):
    cloud_mode = True

    def __init__(self, directory: Path, master_key: str, workspace_id: str):
        super().__init__(directory / "model-settings.enc")
        self.on_changed: Callable[[], None] | None = None
        derived = hmac.new(
            base64.urlsafe_b64decode(master_key),
            b"workspace-models:" + workspace_id.encode(),
            hashlib.sha256,
        ).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(derived))

    def values(self) -> dict[str, str]:
        with self._lock:
            if not self.env_file.exists():
                return {}
            try:
                values = json.loads(self.cipher.decrypt(self.env_file.read_bytes()))
                if not isinstance(values, dict) or any(
                    not isinstance(key, str) or not isinstance(value, str)
                    for key, value in values.items()
                ):
                    raise ValueError("invalid encrypted settings")
                return values
            except (InvalidToken, ValueError, UnicodeError):
                raise WebError(
                    "model_settings_unavailable", "模型配置无法解密，请联系管理员。", 503
                ) from None

    def _write_values(self, changes: dict[str, str]) -> None:
        values = {**self.values(), **changes}
        encrypted = self.cipher.encrypt(json.dumps(values, ensure_ascii=False).encode()).decode()
        previous = self.env_file.read_text(encoding="utf-8") if self.env_file.exists() else None
        atomic_write_utf8(self.env_file, encrypted)
        callback = getattr(self, "on_changed", None)
        if callback is not None:
            try:
                callback()
            except BaseException:
                if previous is None:
                    self.env_file.unlink(missing_ok=True)
                else:
                    atomic_write_utf8(self.env_file, previous)
                raise

    def _settings_from_values(self, values: dict[str, str]) -> Settings:
        return CloudRuntimeSettings.from_env(values)
