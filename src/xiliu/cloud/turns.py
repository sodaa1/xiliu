from __future__ import annotations

import hashlib
import json
from threading import Timer
from uuid import uuid4

from xiliu.api.errors import WebError
from xiliu.cloud.budget import CloudCallBudget, active_budget
from xiliu.cloud.model_settings import CloudRuntimeSettings


class CloudChatTurns:
    def __init__(self, config, ledger):
        self.config, self.ledger = config, ledger

    def stream(self, state, user, cid, body, signal):
        request_id = body.request_id or uuid4().hex
        if len(body.text) + len(body.context) > 24_000:
            raise WebError("context_too_large", "本次输入过长。", 413)
        settings = None
        if body.source == "trial":
            if not self.config.trial_enabled:
                raise WebError("trial_unavailable", "公共模型试用尚未开放，请配置自有 API。", 503)
            if body.text.lstrip().startswith("/"):
                raise WebError("trial_command", "试用仅用于对话；请切换自有 API 使用命令。", 400)
            settings = CloudRuntimeSettings(
                api_key=self.config.trial_api_key,
                model=self.config.trial_model,
                base_url=self.config.trial_base_url,
                data_dir=state.data_dir,
                timeout_seconds=20,
                context_window_tokens=16_000,
                compression_keep_tokens=2_000,
                trace_mode="off",
            )
        fingerprint = hashlib.sha256(
            json.dumps([cid, body.text, body.context, body.source], ensure_ascii=False).encode()
        ).hexdigest()
        reservation = self.ledger.reserve(user, request_id, fingerprint, source=body.source)
        if not reservation["fresh"]:
            receipt = reservation["receipt"]
            if receipt is None:
                raise WebError("request_in_progress", "该请求正在处理中，请勿重复发送。", 409)
            if receipt.get("message_id"):
                message = next(
                    (m for m in state.store.messages(cid) if m["id"] == receipt["message_id"]), None
                )
                receipt = {**receipt, "text": message["content"] if message else "该请求已完成。"}
            yield {**receipt, "request_id": request_id, "source": body.source}
            yield self.usage(user, request_id)
            return
        budget = CloudCallBudget(
            on_dispatch=lambda: self.ledger.dispatched(user, request_id),
            on_start=lambda: self.ledger.started(user, request_id),
            maximum_calls=8 if body.source == "trial" else 16,
        )
        timer = Timer(60, signal.set)
        timer.daemon = True
        token = active_budget.set(budget)
        terminal = {"type": "error", "code": "turn_interrupted", "message": "本次请求已中断。"}
        turn = None
        secret = self.config.trial_api_key if body.source == "trial" else ""

        def redact(text):
            return text.replace(secret, "[已隐藏]") if secret else text

        try:
            timer.start()
            turn = state.chat.stream_turn(
                cid,
                body.text,
                context=body.context,
                signal=signal,
                settings_override=settings,
                response_filter=redact,
            )
            for event in turn:
                event = json.loads(redact(json.dumps(event, ensure_ascii=False)))
                if event.get("type") == "error":
                    event["message"] = "请求未完成，请检查配置或稍后重试。"
                if event.get("type") in {"final", "error"}:
                    terminal = event
                    continue  # Settle before exposing the terminal receipt.
                yield event
        finally:
            try:
                if turn is not None:
                    turn.close()
            finally:
                timer.cancel()
                active_budget.reset(token)
                receipt = terminal
                if terminal.get("message_id"):
                    receipt = {
                        "type": "final",
                        "message_id": terminal["message_id"],
                        "role": terminal.get("role", "assistant"),
                    }
                self.ledger.settle(user, request_id, receipt)
        yield {**terminal, "request_id": request_id, "source": body.source}
        yield self.usage(user, request_id)

    def usage(self, user, request_id):
        return {
            "type": "usage",
            "request_id": request_id,
            "trial": {
                "enabled": self.config.trial_enabled,
                **self.ledger.balance(user),
            },
        }
