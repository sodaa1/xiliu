"""Compatibility import for old integrations; graph execution uses app.executor."""
from xiliu.app.executor import execute_app_request as run_app_fast

__all__ = ["run_app_fast"]
