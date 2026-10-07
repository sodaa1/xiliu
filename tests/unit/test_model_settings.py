from pathlib import Path

import pytest
from dotenv import dotenv_values
from pydantic import SecretStr

from xiliu.api.errors import WebError
from xiliu.api.schemas import ModelUpdate
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.config import Settings


def service(tmp_path: Path, monkeypatch):
    for key in ("XILIU_API_KEY", "XILIU_MODEL", "XILIU_PROVIDER", "XILIU_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "XILIU_API_KEY=private-test-key\nXILIU_MODEL=deepseek-flash\nXILIU_BASE_URL=https://api.deepseek.com\nOTHER_VALUE=keep\n",
        encoding="utf-8",
    )
    return ModelSettingsService(env)


def test_legacy_provider_inferred_and_key_redacted(tmp_path, monkeypatch):
    settings = service(tmp_path, monkeypatch)
    result = settings.read()
    assert result["provider"] == "deepseek"
    assert result["api_key_set"] is True
    assert "api_key" not in result
    assert "private-test-key" not in repr(result)
    assert settings.runtime_settings().model == "deepseek-flash"


@pytest.mark.parametrize("key", [None, "", "   "])
def test_model_only_update_preserves_key_and_other_values(tmp_path, monkeypatch, key):
    settings = service(tmp_path, monkeypatch)
    result = settings.update(
        ModelUpdate(
            provider="deepseek",
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com",
            api_key=key,
        )
    )
    assert result["model"] == "deepseek-v4-pro"
    values = dotenv_values(settings.env_file)
    assert values["XILIU_API_KEY"] == "private-test-key"
    assert values["OTHER_VALUE"] == "keep"
    assert settings.runtime_settings().model == "deepseek-v4-pro"


def test_mismatched_model_and_invalid_url_leave_env_untouched(tmp_path, monkeypatch):
    settings = service(tmp_path, monkeypatch)
    before = settings.env_file.read_bytes()
    with pytest.raises(WebError) as error:
        settings.update(
            ModelUpdate(
                provider="openai", model="deepseek-v4-pro", base_url="https://api.openai.com/v1"
            )
        )
    assert error.value.code == "invalid_model"
    assert settings.env_file.read_bytes() == before
    with pytest.raises(ValueError):
        ModelUpdate(
            provider="openai",
            model="gpt-5.6-terra",
            base_url="file:///secret",
            api_key=SecretStr("private-test-key"),
        )


def test_unconfigured_read_works_but_runtime_is_rejected(tmp_path, monkeypatch):
    settings = service(tmp_path, monkeypatch)
    settings.env_file.unlink()
    assert settings.read()["api_key_set"] is False
    with pytest.raises(WebError) as error:
        settings.runtime_settings()
    assert error.value.code == "model_not_configured"


def test_config_provider_backwards_compatible():
    settings = Settings.from_env({"XILIU_API_KEY": "fake", "XILIU_MODEL": "existing-custom-model"})
    assert settings.provider == "openai"
    assert settings.model == "existing-custom-model"


def test_process_configuration_keeps_documented_priority(tmp_path, monkeypatch):
    settings = service(tmp_path, monkeypatch)
    monkeypatch.setenv("XILIU_MODEL", "deepseek-v4-pro")
    assert settings.read()["model"] == "deepseek-v4-pro"
    assert settings.runtime_settings().model == "deepseek-v4-pro"


@pytest.mark.parametrize("provider", ["openai", "deepseek"])
def test_runtime_uses_the_same_effective_defaults_as_settings_view(tmp_path, monkeypatch, provider):
    settings = service(tmp_path, monkeypatch)
    settings.env_file.write_text(f"XILIU_PROVIDER={provider}\nXILIU_API_KEY=fake\n")
    effective = settings.read()
    runtime = settings.runtime_settings()
    assert runtime.model == effective["model"]
    assert runtime.base_url == effective["base_url"]
