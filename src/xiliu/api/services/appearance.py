from __future__ import annotations

import base64
import binascii
import json
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from xiliu.api.errors import WebError
from xiliu.api.store import AppStore


class AppearanceService:
    def __init__(self, store: AppStore):
        self.store = store
        with store.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS appearance_assets (kind TEXT NOT NULL,id TEXT "
                "NOT NULL,name TEXT NOT NULL,mime TEXT NOT NULL,data BLOB NOT NULL,PRIMARY "
                "KEY(kind,id))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS appearance_settings (kind TEXT PRIMARY "
                "KEY,value TEXT NOT NULL)"
            )

    @staticmethod
    def _mime(data: bytes) -> str:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data[4:8] == b"ftyp" and (b"avif" in data[8:64] or b"avis" in data[8:64]):
            return "image/avif"
        if data.startswith(b"BM"):
            return "image/bmp"
        raise WebError("invalid_background", "请选择 PNG、JPEG、WebP、GIF、AVIF 或 BMP 图片。")

    @staticmethod
    def _settings(db: Any, kind: str, default: Any = None) -> Any:
        row = db.execute("SELECT value FROM appearance_settings WHERE kind=?", (kind,)).fetchone()
        return json.loads(row["value"]) if row else default

    @staticmethod
    def _write(db: Any, kind: str, value: Any):
        db.execute(
            "INSERT INTO appearance_settings VALUES(?,?) ON CONFLICT(kind) DO UPDATE "
            "SET value=excluded.value",
            (kind, json.dumps(value)),
        )

    def backgrounds(self):
        with self.store.connect() as db:
            return {
                "settings": self._settings(db, "background", {"mode": "builtin", "selected": None}),
                "images": [
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "url": f"/api/appearance/backgrounds/{row['id']}",
                    }
                    for row in db.execute(
                        "SELECT id,name FROM appearance_assets WHERE kind='background' ORDER BY "
                        "rowid DESC"
                    )
                ],
            }

    def add_background(self, name: str, data: bytes):
        if not data or len(data) > 20 * 1024 * 1024:
            raise WebError("invalid_background", "背景图片必须在 20 MiB 以内。")
        if not isinstance(name, str) or not name.strip() or len(name) > 240:
            raise WebError("invalid_background", "图片名称无效。")
        mime, identifier = self._mime(data), str(uuid4())
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO appearance_assets VALUES(?,?,?,?,?)",
                ("background", identifier, name, mime, data),
            )
            self._write(db, "background", {"mode": "custom", "selected": identifier})
        return {"id": identifier, "name": name}

    def select_background(self, settings: dict):
        if not isinstance(settings, dict) or settings.get("mode") not in (
            "blank",
            "builtin",
            "custom",
        ):
            raise WebError("invalid_background", "背景选项无效。")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            identifier = settings.get("selected") if settings["mode"] == "custom" else None
            if settings["mode"] == "custom" and (
                not isinstance(identifier, str)
                or not db.execute(
                    "SELECT 1 FROM appearance_assets WHERE kind='background' AND id=?",
                    (identifier,),
                ).fetchone()
            ):
                raise WebError("background_not_found", "背景图片不存在，请重新选择。", 404)
            value = {"mode": settings["mode"], "selected": identifier}
            self._write(db, "background", value)
            return value

    def background(self, identifier: str):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT data,mime FROM appearance_assets WHERE kind='background' AND id=?",
                (identifier,),
            ).fetchone()
            if not row:
                raise WebError("background_not_found", "背景图片不存在。", 404)
            return row["data"], row["mime"]

    def delete_background(self, identifier: str):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            settings = self._settings(db, "background", {})
            if settings.get("selected") == identifier:
                self._write(db, "background", {"mode": "blank", "selected": None})
            db.execute(
                "DELETE FROM appearance_assets WHERE kind='background' AND id=?", (identifier,)
            )

    @staticmethod
    def _kind(form: str):
        if form not in ("chibi", "standing"):
            raise WebError("invalid_model", "桌宠形态无效。")
        return f"model-{form}"

    def model(self, form: str):
        kind = self._kind(form)
        with self.store.connect() as db:
            settings = self._settings(db, kind)
            if settings is None:
                return None
            return {
                **settings,
                "form": form,
                "files": [
                    {
                        "path": row["id"],
                        "url": (
                            f"/api/appearance/model-assets/{form}?path={quote(row['id'], safe='')}"
                        ),
                    }
                    for row in db.execute("SELECT id FROM appearance_assets WHERE kind=?", (kind,))
                ],
            }

    def save_model(self, form: str, bundle: dict):
        kind = self._kind(form)
        if (
            not isinstance(bundle, dict)
            or not isinstance(bundle.get("name"), str)
            or not 0 < len(bundle["name"]) <= 240
            or not isinstance(bundle.get("files"), list)
            or not 0 < len(bundle["files"]) <= 1000
        ):
            raise WebError("invalid_model", "模型导入格式无效。")
        values, seen, size = [], set(), 0
        mimes = {
            ".json": "application/json",
            ".moc3": "application/octet-stream",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }
        for item in bundle["files"]:
            if not isinstance(item, dict):
                raise WebError("invalid_model", "模型文件格式无效。")
            path, encoded = item.get("path"), item.get("data_base64")
            if (
                not isinstance(path, str)
                or len(path) > 800
                or path in seen
                or path.startswith("/")
                or any(c in path for c in ("\\", ":", "?", "#", "\x00"))
                or any(p in ("", "..", ".") for p in path.split("/"))
                or PurePosixPath(path).suffix.lower() not in mimes
            ):
                raise WebError("invalid_model", "模型文件路径或格式无效。")
            try:
                if not isinstance(encoded, str):
                    raise ValueError
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error):
                raise WebError("invalid_model", "模型文件编码无效。") from None
            size += len(data)
            if not data or size > 200 * 1024 * 1024:
                raise WebError("invalid_model", "模型文件为空或超过 200 MiB。")
            seen.add(path)
            values.append(
                (
                    kind,
                    path,
                    PurePosixPath(path).name,
                    mimes[PurePosixPath(path).suffix.lower()],
                    data,
                )
            )
        manifest = bundle.get("manifestPath")
        if (
            not isinstance(manifest, str)
            or manifest not in seen
            or not manifest.endswith(".model3.json")
        ):
            raise WebError("invalid_model", "模型配置缺失。")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM appearance_assets WHERE kind=?", (kind,))
            db.executemany("INSERT INTO appearance_assets VALUES(?,?,?,?,?)", values)
            self._write(db, kind, {"name": bundle["name"], "manifestPath": manifest})
        return {"saved": True}

    def model_file(self, form: str, path: str):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT data,mime FROM appearance_assets WHERE kind=? AND id=?",
                (self._kind(form), path),
            ).fetchone()
            if not row:
                raise WebError("model_not_found", "模型文件不存在。", 404)
            return row["data"], row["mime"]

    def delete_model(self, form: str):
        kind = self._kind(form)
        with self.store.connect() as db:
            db.execute("DELETE FROM appearance_assets WHERE kind=?", (kind,))
            db.execute("DELETE FROM appearance_settings WHERE kind=?", (kind,))
