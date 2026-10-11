import os

import pytest


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch):
    for key in list(os.environ):
        if key.startswith("XILIU_") or key == "TAVILY_API_KEY":
            monkeypatch.delenv(key, raising=False)
