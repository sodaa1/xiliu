from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime

from xiliu.api.errors import WebError


class TrialLedger:
    def __init__(self, identity, *, daily_limit=100, clock=time.time):
        self.identity, self.daily_limit, self.clock = identity, daily_limit, clock
        with identity.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS cloud_turns (
                user_id TEXT NOT NULL REFERENCES users(id), request_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL,
                day TEXT NOT NULL, expires REAL NOT NULL, dispatched INTEGER NOT NULL DEFAULT 0,
                receipt TEXT, PRIMARY KEY(user_id,request_id)
            )""")
            db.execute(
                "CREATE INDEX IF NOT EXISTS cloud_turns_day ON cloud_turns(day,source,status)"
            )

    def _recover(self, db):
        # An interrupted process cannot prove that an already dispatched request
        # did not generate output. Only untouched reservations can be refunded.
        db.execute(
            """UPDATE cloud_turns SET
            status=CASE WHEN dispatched=1 OR status='started' THEN 'consumed' ELSE 'refunded' END,
            receipt=? WHERE status IN ('reserved','started') AND expires<?""",
            (
                json.dumps(
                    {
                        "type": "error",
                        "code": "turn_interrupted",
                        "message": "上次请求已中断，请使用新的请求重试。",
                    }
                ),
                self.clock(),
            ),
        )

    @staticmethod
    def _used(db, user):
        return db.execute(
            """SELECT count(*) FROM cloud_turns WHERE user_id=? AND source='trial'
            AND status IN ('reserved','started','consumed')""",
            (user,),
        ).fetchone()[0]

    def balance(self, user):
        with self.identity.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._recover(db)
            return {"limit": 5, "remaining": max(0, 5 - self._used(db, user))}

    def reserve(self, user, request_id, fingerprint, *, source):
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", request_id) or source not in {"own", "trial"}:
            raise WebError("invalid_request_id", "请使用有效的请求标识。", 422)
        with self.identity.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._recover(db)
            row = db.execute(
                "SELECT * FROM cloud_turns WHERE user_id=? AND request_id=?", (user, request_id)
            ).fetchone()
            if row:
                if row["fingerprint"] != fingerprint or row["source"] != source:
                    raise WebError("request_conflict", "同一请求标识不能用于不同内容。", 409)
                return {
                    "fresh": False,
                    "status": row["status"],
                    "receipt": json.loads(row["receipt"]) if row["receipt"] else None,
                }
            day = datetime.fromtimestamp(self.clock(), UTC).date().isoformat()
            if source == "trial":
                if self._used(db, user) >= 5:
                    raise WebError("trial_exhausted", "5 次试用已用完，请配置自有 API。", 403)
                active = db.execute("""SELECT count(*) FROM cloud_turns
                    WHERE source='trial' AND status IN ('reserved','started')""").fetchone()[0]
                own_active = db.execute(
                    """SELECT 1 FROM cloud_turns WHERE user_id=?
                    AND source='trial' AND status IN ('reserved','started')""",
                    (user,),
                ).fetchone()
                if own_active or active >= 4:
                    raise WebError("trial_busy", "试用回复正在处理中，请稍后再试。", 429)
                used_today = db.execute(
                    """SELECT count(*) FROM cloud_turns WHERE day=?
                    AND source='trial' AND status IN ('reserved','started','consumed')""",
                    (day,),
                ).fetchone()[0]
                if used_today >= self.daily_limit:
                    raise WebError(
                        "trial_daily_limit", "今日公共试用额度已用完，请使用自有 API。", 429
                    )
            db.execute(
                """INSERT INTO cloud_turns
                (user_id,request_id,fingerprint,source,status,day,expires)
                VALUES(?,?,?,?,'reserved',?,?)""",
                (user, request_id, fingerprint, source, day, self.clock() + 120),
            )
            return {"fresh": True, "status": "reserved", "receipt": None}

    def dispatched(self, user, request_id):
        with self.identity.connect() as db:
            db.execute(
                """UPDATE cloud_turns SET dispatched=1
                WHERE user_id=? AND request_id=? AND status='reserved'""",
                (user, request_id),
            )

    def started(self, user, request_id):
        with self.identity.connect() as db:
            db.execute(
                """UPDATE cloud_turns SET status='started',dispatched=1
                WHERE user_id=? AND request_id=? AND status='reserved'""",
                (user, request_id),
            )

    def settle(self, user, request_id, receipt):
        with self.identity.connect() as db:
            db.execute(
                """UPDATE cloud_turns SET
                status=CASE WHEN status='started' OR source='own'
                    THEN 'consumed' ELSE 'refunded' END,
                receipt=? WHERE user_id=? AND request_id=? AND status IN ('reserved','started')""",
                (json.dumps(receipt, ensure_ascii=False), user, request_id),
            )
