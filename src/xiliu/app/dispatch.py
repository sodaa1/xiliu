"""Policy, confirmation and durable receipts for every application action."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from xiliu.api.errors import WebError
from xiliu.app.actions import _records, get_registry
from xiliu.execution.cancellation import TurnCancelled, check_cancelled
from xiliu.policy.engine import PolicyEngine

_lock = threading.RLock()


def _failure(error: str, *, status: str = "failed") -> dict:
    return {
        "ok": False,
        "status": status,
        "error": error,
        "records": [],
        "verification": {"passed": False},
    }


def _dump(model: BaseModel) -> dict:
    # Top-level defaults remain meaningful; nested patches include only supplied fields.
    return {
        key: (value.model_dump(exclude_unset=True) if isinstance(value, BaseModel) else value)
        for key, value in model
    }


def _requested_state(action_id: str, args: dict, value: Any) -> bool:
    """A no-op Service must not pass by returning the unchanged stored record."""
    if not isinstance(value, dict) or "counts" in value:
        return True
    requested = dict(args.get("changes", args))
    if action_id == "inbox.import_url":
        requested["source"] = requested.pop("url")
    target_key = (
        "task_id"
        if "task_id" in args
        else "cid"
        if "cid" in args
        else "item_id"
        if "item_id" in args
        else "folder_id"
        if action_id == "knowledge.folders.update"
        else None
    )
    if (
        action_id != "feed.save_to_inbox"
        and target_key is not None
        and "id" in value
        and value["id"] != args[target_key]
    ):
        return False
    if action_id == "knowledge.folders.ensure":
        return value.get("name", "").strip().casefold() == args["name"].strip().casefold()
    if action_id == "content.move_to_inbox":
        requested.update(status="inbox", folder_id=None)
    if action_id == "conversations.model":
        requested["model_override"] = args["model"]
    if action_id == "automations.create":
        requested["schedule"] = {"hour": args["hour"], "minute": args["minute"]}
    stored = value.get("preferences", value)
    fields = {
        "title",
        "name",
        "content",
        "summary",
        "source",
        "type",
        "url",
        "status",
        "folder_id",
        "tags",
        "priority",
        "completed",
        "due_at",
        "enabled",
        "model_override",
        "prompt",
        "schedule",
        "timezone",
    }
    if "preferences" in value:
        if action_id == "preferences.reset":
            from xiliu.api.services.preferences import APPEARANCE, DEFAULTS

            requested = {key: DEFAULTS[key] for key in APPEARANCE}
        fields = set(requested) - {"expected_revision"}
    for key in fields & requested.keys():
        if key not in stored:
            return False
        expected = requested[key]
        if key == "title" and (
            requested.get("fetch_title") or action_id == "feed.add_manual" and not expected
        ):
            continue
        trimmed = (
            {"title"}
            if action_id.startswith("tasks.")
            else {"title", "summary"}
            if action_id.startswith("feed.")
            else {"name", "summary"}
            if action_id.startswith("knowledge.folders.")
            else {"name", "prompt"}
            if action_id.startswith("automations.")
            else {"title", "source"}
            if action_id.startswith(("content.", "inbox.", "knowledge.items."))
            else set()
        )
        if isinstance(expected, str) and key in trimmed:
            expected = expected.strip()
        if key == "due_at" and expected is not None:
            expected = datetime.fromisoformat(expected).isoformat()
        if key == "tags":
            if not isinstance(expected, list):
                return False
            if {tag.strip().casefold() for tag in expected if tag.strip()} != {
                tag.casefold() for tag in stored[key]
            }:
                return False
            continue
        if stored[key] != expected:
            return False
    return True


class AppDispatcher:
    def __init__(self, services: Any, context: Any, *, allowed_actions: set[str] | None = None):
        self.services, self.context = services, context
        self.allowed_actions = allowed_actions
        self.registry = get_registry()

    def _allowed(self, spec: Any, arguments: dict | None = None) -> bool:
        if self.allowed_actions is not None and spec.id not in self.allowed_actions:
            return False
        policy = self.context.policy_engine or PolicyEngine(
            Path(self.context.data_dir or self.context.workspace) / "policy.json"
        )
        permissions = [spec.permission]
        arguments = arguments or {}
        changes = arguments.get("changes")
        if (
            spec.requires_network
            or arguments.get("fetch_title")
            or arguments.get("use_ai")
            or spec.id == "inbox.retry"
            or isinstance(changes, dict)
            and changes.get("fetch_title")
        ):
            if self.context.local_only:
                return False
            permissions.append("network.read")
        return all(
            policy.evaluate(
                actor=self.context.actor_type,
                source="builtin",
                capability_id="builtin:app:" + spec.id,
                permission=permission,
                arguments=arguments,
                profile=self.context.policy_profile,
            ).effect
            == "allow"
            for permission in permissions
        )

    def catalog(self) -> dict:
        return {
            "ok": True,
            "actions": [
                {
                    "action_id": spec.id,
                    "description": spec.description,
                    "domain": spec.domain,
                    "schema": spec.args_schema.model_json_schema(),
                    "permission": spec.permission,
                    "side_effect": spec.side_effect,
                    "requires_network": spec.requires_network,
                    "supports_batch": spec.supports_batch,
                    "confirmation": spec.confirmation_policy,
                }
                for spec in self.registry.values()
                if spec.agent_availability == "enabled" and self._allowed(spec)
            ],
        }

    def describe(self, action_id: str) -> dict:
        spec = self.registry.get(action_id)
        if spec is None or spec.agent_availability != "enabled":
            return _failure("capability_unavailable")
        if not self._allowed(spec):
            return _failure("policy_denied")
        return {
            "ok": True,
            "action_id": action_id,
            "schema": spec.args_schema.model_json_schema(),
            "confirmation": spec.confirmation_policy,
            "supports_batch": spec.supports_batch,
        }

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.services.store.path, timeout=15)
        try:
            # Migration is atomic across threads and processes, including first reads.
            with _lock, db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS app_requests (session TEXT, request TEXT, "
                    "digest TEXT, result TEXT, PRIMARY KEY(session,request))"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS app_confirmations (token TEXT PRIMARY KEY, "
                    "session TEXT, digest TEXT, expires REAL, approved INTEGER DEFAULT 0, "
                    "used INTEGER DEFAULT 0)"
                )
                columns = {row[1] for row in db.execute("PRAGMA table_info(app_confirmations)")}
                if "payload" not in columns:
                    db.execute("ALTER TABLE app_confirmations ADD COLUMN payload TEXT")
                columns = {row[1] for row in db.execute("PRAGMA table_info(app_requests)")}
                if "arguments" not in columns:
                    db.execute("ALTER TABLE app_requests ADD COLUMN arguments TEXT")
            with db:
                yield db
        finally:
            db.close()

    def approve_confirmation(self, confirmation_id: str, *, session_id: str) -> bool:
        # Called by the authenticated human HTTP flow, never exposed as an Agent action.
        with _lock, self._db() as db:
            changed = db.execute(
                "UPDATE app_confirmations SET approved=1 WHERE token=? AND session=? "
                "AND approved=0 AND used=0 AND expires>?",
                (confirmation_id, session_id, time.time()),
            ).rowcount
        return bool(changed)

    def confirm(self, confirmation_id: str) -> dict:
        with self._db() as db:
            row = db.execute(
                "SELECT payload FROM app_confirmations WHERE token=? AND session=? "
                "AND expires>? AND used=0 AND approved=0",
                (confirmation_id, self.context.session_id, time.time()),
            ).fetchone()
        if (
            row is None
            or not row[0]
            or not self.approve_confirmation(confirmation_id, session_id=self.context.session_id)
        ):
            return _failure("confirmation_invalid")
        payload = json.loads(row[0])
        return self.execute(
            payload["action_id"],
            payload["arguments"],
            request_id=payload["request_id"],
            confirmation_id=confirmation_id,
        )

    def get_receipt(self, request_id: str) -> dict | None:
        with self._db() as db:
            row = db.execute(
                "SELECT result,arguments FROM app_requests WHERE session=? AND request=?",
                (self.context.session_id, request_id),
            ).fetchone()
        if not row:
            return None
        result = json.loads(row[0])
        spec = self.registry.get(result.get("action_id", ""))
        arguments = json.loads(row[1]) if row[1] else {}
        if (
            spec is None
            or spec.agent_availability != "enabled"
            or not self._allowed(spec, arguments)
        ):
            return _failure("policy_denied")
        return result

    def get_receipt_arguments(self, request_id: str) -> dict:
        """Recover the original parameters for policy-checked receipt replay."""
        receipt = self.get_receipt(request_id)
        if receipt is None or receipt.get("ok") is not True:
            return {}
        with self._db() as db:
            row = db.execute(
                "SELECT arguments FROM app_requests WHERE session=? AND request=?",
                (self.context.session_id, request_id),
            ).fetchone()
        return json.loads(row[0]) if row and row[0] else {}

    def execute(
        self,
        action_id: str,
        arguments: dict,
        *,
        request_id: str | None = None,
        confirmation_id: str | None = None,
    ) -> dict:
        result = self._execute(
            action_id, arguments, request_id=request_id, confirmation_id=confirmation_id
        )
        handler = getattr(self.context, "approval_handler", None)
        if (
            result.get("status") == "confirmation_required"
            and callable(handler)
            and self.context.approval_mode == "inline"
            and self.context.actor_type == "interactive"
            and self.context.policy_profile == "interactive"
        ):
            from xiliu.core.approval import ApprovalDecision, ApprovalRequest

            # UI/CLI-owned callback runs outside every database transaction and lock.
            try:
                decision = handler(
                    ApprovalRequest(
                        id=result["confirmation_id"],
                        tool_name="app",
                        command=json.dumps(
                            {"action_id": action_id, "arguments": result["arguments"]},
                            ensure_ascii=False,
                        ),
                        risk_reason=result["description"],
                    )
                )
            except Exception:
                return result
            check_cancelled()
            if isinstance(decision, ApprovalDecision) and decision.approved:
                return self.confirm(result["confirmation_id"])
        return result

    def _execute(
        self,
        action_id: str,
        arguments: dict,
        *,
        request_id: str | None = None,
        confirmation_id: str | None = None,
    ) -> dict:
        spec = self.registry.get(action_id)
        if spec is None or spec.agent_availability != "enabled":
            return _failure("capability_unavailable")
        if self.services is None:
            return _failure("service_unavailable")
        try:
            args = _dump(spec.args_schema.model_validate(arguments))
        except (ValidationError, TypeError, ValueError):
            return _failure("invalid_arguments")
        if not self._allowed(spec, args):
            return _failure("policy_denied")
        digest = hashlib.sha256(
            json.dumps([action_id, args], sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        session = self.context.session_id
        check_cancelled()
        # Serialize only the durable claim. Never hold this lock or a SQLite write
        # transaction over Service/network work: independent chats must keep running.
        with _lock, self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            if request_id:
                row = db.execute(
                    "SELECT digest,result FROM app_requests WHERE session=? AND request=?",
                    (session, request_id),
                ).fetchone()
                if row:
                    return json.loads(row[1]) if row[0] == digest else _failure("conflict")
            if spec.confirmation_policy == "explicit":
                row = db.execute(
                    "SELECT approved,used FROM app_confirmations WHERE token=? AND session=? "
                    "AND digest=? AND expires>?",
                    (confirmation_id, session, digest, time.time()),
                ).fetchone()
                if not row or not row[0] or row[1]:
                    token = secrets.token_urlsafe(32)
                    db.execute(
                        "INSERT INTO app_confirmations(token,session,digest,expires,payload) "
                        "VALUES(?,?,?,?,?)",
                        (
                            token,
                            session,
                            digest,
                            time.time() + 300,
                            json.dumps(
                                {
                                    "action_id": action_id,
                                    "arguments": args,
                                    "request_id": request_id,
                                },
                                ensure_ascii=False,
                            ),
                        ),
                    )
                    return {
                        **_failure("confirmation_required", status="confirmation_required"),
                        "confirmation_id": token,
                        "action_id": action_id,
                        "description": spec.description,
                        "arguments": args,
                    }
                changed = db.execute(
                    "UPDATE app_confirmations SET used=1 WHERE token=? AND session=? "
                    "AND digest=? AND approved=1 AND used=0 AND expires>?",
                    (confirmation_id, session, digest, time.time()),
                ).rowcount
                if not changed:
                    return _failure("confirmation_invalid")
            if request_id:
                # Commit an execution marker first. An interrupted process must never
                # silently repeat a potentially completed Service write on retry.
                db.execute(
                    "INSERT INTO app_requests(session,request,digest,result,arguments) "
                    "VALUES(?,?,?,?,?)",
                    (
                        session,
                        request_id,
                        digest,
                        json.dumps(
                            {
                                **_failure("execution_pending", status="pending"),
                                "action_id": action_id,
                            }
                        ),
                        json.dumps(args, ensure_ascii=False),
                    ),
                )
        try:
            value = spec.handler(self.services, args, self.context)
            passed = bool(spec.postcondition(self.services, args, value))
            # Services reject stale writes without overwriting user changes.
            if spec.side_effect == "write":
                passed = passed and _requested_state(action_id, args, value)
            counts = value.get("counts", {}) if isinstance(value, dict) else {}
            partial = bool(counts.get("failed", 0))
            data = value
            if isinstance(value, dict) and "preferences" in value:
                preferences = {k: v for k, v in value["preferences"].items() if k != "avatar"}
                preferences["avatar_present"] = bool(value["preferences"].get("avatar"))
                data = {**value, "preferences": preferences}
            result = {
                "ok": passed and not partial,
                "status": "partial" if partial else "completed" if passed else "failed",
                "action_id": action_id,
                "data": data,
                "records": _records(data),
                "counts": counts,
                "verification": {"passed": passed},
            }
            if isinstance(value, dict) and "job_id" in value:
                result["status"] = value["status"]
                result["ok"] = passed and value["status"] in {"pending", "running", "completed"}
            if not passed:
                result["error"] = "postcondition_failed"
        except TurnCancelled:
            if request_id:
                with _lock, self._db() as db:
                    db.execute(
                        "UPDATE app_requests SET result=? WHERE session=? AND request=?",
                        (
                            json.dumps(
                                {
                                    **_failure("cancelled", status="cancelled"),
                                    "action_id": action_id,
                                }
                            ),
                            session,
                            request_id,
                        ),
                    )
            raise
        except WebError as error:
            result = _failure(error.code)
        except Exception:
            # Provider/validation errors can carry keys or card content; do not echo them.
            result = _failure("service_failed")
        if request_id:
            result.setdefault("action_id", action_id)
            with _lock, self._db() as db:
                db.execute(
                    "UPDATE app_requests SET result=? WHERE session=? AND request=?",
                    (json.dumps(result, ensure_ascii=False), session, request_id),
                )
        return result
