from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from xiliu.api.errors import WebError

_HASH_SLOTS = BoundedSemaphore(2)


class IdentityStore:
    def __init__(
        self, data_dir: Path, *, clock: Callable[[], float] = time.time, max_users: int = 100
    ):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "accounts.sqlite3"
        self.clock = clock
        self.max_users = max_users
        self.hasher = PasswordHasher()
        self.dummy_hash = self._hash(secrets.token_urlsafe(32))
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL UNIQUE,
                    username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS rate_limits (
                    namespace TEXT NOT NULL, identity_hash TEXT NOT NULL,
                    window REAL NOT NULL, attempts INTEGER NOT NULL,
                    PRIMARY KEY(namespace, identity_hash)
                );
            """)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _hash(self, password: str) -> str:
        with self._hash_slot():
            return self.hasher.hash(password)

    @staticmethod
    @contextmanager
    def _hash_slot():
        if not _HASH_SLOTS.acquire(timeout=5):
            raise WebError("auth_busy", "登录服务繁忙，请稍后重试。", 503)
        try:
            yield
        finally:
            _HASH_SLOTS.release()

    @staticmethod
    def _validate(username: str, password: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", username) or not 12 <= len(password) <= 128:
            raise WebError(
                "invalid_credentials", "用户名需为 3–32 位字母、数字或下划线，密码需为 12–128 位。"
            )
        return username.lower()

    @staticmethod
    def _public(row) -> dict:
        return {key: row[key] for key in ("id", "workspace_id", "username")}

    def register(self, username: str, password: str) -> dict:
        name = self._validate(username, password)
        hashed = self._hash(password)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM users").fetchone()[0] >= self.max_users:
                raise WebError("account_capacity", "当前注册容量已满，请稍后再试。", 503)
            user = {"id": uuid4().hex, "workspace_id": uuid4().hex, "username": name}
            try:
                db.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                    (*user.values(), hashed, self.clock()),
                )
            except sqlite3.IntegrityError:
                raise WebError(
                    "registration_failed", "无法创建此账号，请更换用户名。", 409
                ) from None
        return user

    def login(self, username: str, password: str, *, ttl: int = 86400) -> str:
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE username=?", (username.lower(),)).fetchone()
        hashed = row["password_hash"] if row else self.dummy_hash
        try:
            with self._hash_slot():
                valid = self.hasher.verify(hashed, password)
        except VerificationError:
            valid = False
        if not row or not valid:
            raise WebError("login_failed", "用户名或密码不正确。", 401)
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT password_hash FROM users WHERE id=?", (row["id"],)
            ).fetchone()
            if not current or not secrets.compare_digest(current[0], hashed):
                raise WebError("login_failed", "用户名或密码不正确。", 401)
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (self.clock(),))
            db.execute(
                "INSERT INTO sessions VALUES (?, ?, ?)",
                (self._digest(token), row["id"], self.clock() + ttl),
            )
        return token

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def session(self, token: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
                "WHERE s.token_hash=? AND s.expires_at>?",
                (self._digest(token), self.clock()),
            ).fetchone()
        if not row:
            raise WebError("login_required", "请先登录。", 401)
        return self._public(row)

    def revoke(self, token: str) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (self._digest(token),))

    def reset_password(self, username: str, password: str) -> None:
        self._validate(username, password)
        hashed = self._hash(password)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM users WHERE username=?", (username.lower(),)
            ).fetchone()
            if not row:
                raise WebError("account_not_found", "账号不存在。", 404)
            db.execute("UPDATE users SET password_hash=? WHERE id=?", (hashed, row[0]))
            db.execute("DELETE FROM sessions WHERE user_id=?", (row[0],))

    def rate_limit(self, namespace: str, identity: str, *, limit: int, seconds: int) -> None:
        now = self.clock()
        identity_hash = self._digest(identity)
        denied = False
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT window, attempts FROM rate_limits WHERE namespace=? AND identity_hash=?",
                (namespace, identity_hash),
            ).fetchone()
            start, attempts = (row[0], row[1]) if row and now - row[0] < seconds else (now, 0)
            denied = attempts >= limit
            if not denied:
                db.execute(
                    "INSERT OR REPLACE INTO rate_limits VALUES (?, ?, ?, ?)",
                    (namespace, identity_hash, start, attempts + 1),
                )
        if denied:
            raise WebError("rate_limited", "操作过于频繁，请稍后再试。", 429)
