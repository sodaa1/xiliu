"""Cooperative cancellation shared with LangGraph's copied task contexts."""

from contextvars import ContextVar
from threading import Event

cancel_signal: ContextVar[Event | None] = ContextVar("turn_cancel_signal", default=None)


class TurnCancelled(Exception):
    def __init__(self):
        super().__init__("Turn cancelled")


def check_cancelled() -> None:
    signal = cancel_signal.get()
    if signal is not None and signal.is_set():
        raise TurnCancelled()
