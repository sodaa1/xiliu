import pytest
from cryptography.fernet import Fernet

from xiliu.api.errors import WebError
from xiliu.api.model_catalog import MODEL_CATALOG
from xiliu.api.schemas import ModelUpdate
from xiliu.cloud.model_settings import CloudModelSettings


def test_cloud_models_never_inherit_process_secrets_and_are_encrypted(tmp_path, monkeypatch):
    monkeypatch.setenv("XILIU_API_KEY", "server-secret-never-borrow")
    monkeypatch.setenv("TAVILY_API_KEY", "server-search-never-borrow")
    key = Fernet.generate_key().decode()
    models = CloudModelSettings(tmp_path, key, "workspace-a")
    assert models.read()["api_key_set"] is False
    with pytest.raises(WebError):
        models.runtime_settings()
    models.update(
        ModelUpdate(
            provider="openai",
            model=next(iter(MODEL_CATALOG["openai"]["models"])),
            base_url="https://api.openai.com/v1",
            api_key="personal-secret-key",
            make_default=True,
        )
    )
    assert models.read()["api_key_set"]
    assert "personal-secret-key" not in str(models.read())
    assert models.runtime_settings().api_key.get_secret_value() == "personal-secret-key"
    assert models.runtime_settings().tavily_api_key is None
    assert not any(
        b"personal-secret-key" in path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    assert CloudModelSettings(tmp_path, key, "workspace-a").read() == models.read()
    with pytest.raises(WebError):
        CloudModelSettings(tmp_path, key, "workspace-b").read()
