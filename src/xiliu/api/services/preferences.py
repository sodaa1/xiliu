from __future__ import annotations

import json
import re
from typing import Any

from xiliu.api.errors import WebError
from xiliu.api.store import AppStore

DEFAULTS: dict[str, Any] = {
    "displayName": "",
    "email": "",
    "bio": "",
    "avatar": "",
    "theme": "light",
    "fontSize": "small",
    "fontFamily": "system",
    "density": "comfortable",
    "reducedMotion": False,
}
CHOICES = {
    "theme": {"light", "dark", "system"},
    "fontSize": {"small", "medium", "large"},
    "fontFamily": {"system", "rounded", "serif"},
    "density": {"comfortable", "compact"},
}
APPEARANCE = (*CHOICES, "reducedMotion")


class PreferencesService:
    """Non-sensitive preferences shared by HTTP and App actions in the existing store."""

    def __init__(self, store: AppStore):
        self.store = store
        with store.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS app_preferences (
                id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL,
                preferences_json TEXT NOT NULL)""")
        # The desktop sidecar shares this data directory with its legacy backup.
        legacy = store.path.parent / "preferences.json"
        try:
            if legacy.stat().st_size > 262144:
                return
            payload = json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(payload, dict):
            return
        migrated = {}
        for key, value in payload.items():
            if key not in DEFAULTS:
                continue
            if key in {"displayName", "email", "bio"} and isinstance(value, str):
                value = value[: 300 if key == "bio" else 100]
            try:
                migrated.update(self._validate({key: value}))
            except WebError:
                continue
        if migrated:
            with store.connect() as db:
                db.execute(
                    "INSERT OR IGNORE INTO app_preferences VALUES(1,1,?)",
                    (json.dumps({**DEFAULTS, **migrated}, ensure_ascii=False),),
                )

    @staticmethod
    def _validate(payload: dict[str, Any]) -> dict[str, Any]:
        invalid = WebError("invalid_arguments", "偏好设置格式不正确。", 422)
        if not isinstance(payload, dict) or set(payload) - DEFAULTS.keys():
            raise invalid
        for key, value in payload.items():
            if key in CHOICES:
                if not isinstance(value, str) or value not in CHOICES[key]:
                    raise invalid
            elif key == "reducedMotion":
                if type(value) is not bool:
                    raise invalid
            elif not isinstance(value, str):
                raise invalid
            elif key == "avatar":
                if value and (
                    len(value) > 220000
                    or not re.fullmatch(r"data:image/(webp|png|jpeg);base64,[A-Za-z0-9+/=]+", value)
                ):
                    raise invalid
            elif len(value) > (300 if key == "bio" else 100):
                raise invalid
        return dict(payload)

    @staticmethod
    def _snapshot(row) -> dict[str, Any]:
        if row is None:
            return {"preferences": dict(DEFAULTS), "revision": 0, "initialized": False}
        return {
            "preferences": json.loads(row["preferences_json"]),
            "revision": row["revision"],
            "initialized": True,
        }

    def get(self) -> dict[str, Any]:
        with self.store.connect() as db:
            return self._snapshot(db.execute("SELECT * FROM app_preferences WHERE id=1").fetchone())

    def update(
        self,
        payload: dict[str, Any],
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        changes = self._validate(payload)
        if expected_revision is not None and (
            type(expected_revision) is not int or expected_revision < 0
        ):
            raise WebError("invalid_arguments", "偏好版本格式不正确。", 422)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = self._snapshot(
                db.execute("SELECT * FROM app_preferences WHERE id=1").fetchone()
            )
            if expected_revision is not None and expected_revision != current["revision"]:
                raise WebError("conflict", "偏好已在其他窗口或助手中更新，请检查后重试。", 409)
            updated = {**current["preferences"], **changes}
            revision = current["revision"] + 1
            db.execute(
                "INSERT INTO app_preferences VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET "
                "revision=excluded.revision,preferences_json=excluded.preferences_json",
                (revision, json.dumps(updated, ensure_ascii=False)),
            )
            return {"preferences": updated, "revision": revision, "initialized": True}

    def reset(self, expected_revision: int | None = None) -> dict[str, Any]:
        return self.update({key: DEFAULTS[key] for key in APPEARANCE}, expected_revision)
