import pytest
from dotenv import dotenv_values

from xiliu.api.errors import WebError
from xiliu.api.schemas import ModelUpdate
from xiliu.api.services.model_settings import ModelSettingsService


def test_disable_restore_preserves_connection_and_rejects_default(tmp_path, monkeypatch):
    service = profiles(tmp_path, monkeypatch)
    args = dict(
        provider="deepseek",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        make_default=False,
    )
    result = service.update(ModelUpdate(**args, enabled=False))
    assert next(c for c in result["connections"] if c["model"] == args["model"])["enabled"] is False
    with pytest.raises(WebError, match="停用"):
        service.runtime_settings("deepseek:deepseek-v4-pro")
    restored = ModelSettingsService(service.env_file)
    restored.update(ModelUpdate(**args, enabled=True))
    assert (
        restored.runtime_settings("deepseek:deepseek-v4-pro").api_key.get_secret_value()
        == "deep-test"
    )
    before = service.env_file.read_bytes()
    with pytest.raises(WebError, match="默认"):
        service.update(ModelUpdate(**{**args, "model": "deepseek-v4-flash"}, enabled=False))
    assert service.env_file.read_bytes() == before


def profiles(tmp_path, monkeypatch):
    for key in ("XILIU_API_KEY", "XILIU_MODEL", "XILIU_PROVIDER", "XILIU_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "XILIU_PROVIDER=deepseek\nXILIU_API_KEY=deep-test\nXILIU_MODEL=deepseek-v4-flash\nXILIU_BASE_URL=https://api.deepseek.com\n",
        encoding="utf-8",
    )
    return ModelSettingsService(env)


def select(service, provider, key=None, address=None):
    return service.update(
        ModelUpdate(
            provider=provider,
            model="deepseek-v4-flash" if provider == "deepseek" else "gpt-5.6-terra",
            base_url=address
            or (
                "https://api.deepseek.com"
                if provider == "deepseek"
                else "https://api.openai.com/v1"
            ),
            api_key=key,
        )
    )


def test_switch_round_trip_restores_each_provider_key_and_address(tmp_path, monkeypatch):
    service = profiles(tmp_path, monkeypatch)
    select(service, "openai", "open-test", "https://open.example.test/v1")
    select(service, "deepseek")
    deep = service.runtime_settings()
    assert deep.api_key.get_secret_value() == "deep-test"
    assert deep.base_url == "https://api.deepseek.com"
    select(service, "openai", address="https://open.example.test/v1")
    assert service.runtime_settings().api_key.get_secret_value() == "open-test"
    assert dotenv_values(service.env_file)["XILIU_DEEPSEEK_API_KEY"] == "deep-test"
    public = service.read()
    assert public["profiles"]["deepseek"]["api_key_set"] is True
    assert "deep-test" not in repr(public) and "open-test" not in repr(public)


def test_unconfigured_provider_does_not_borrow_other_provider_key(tmp_path, monkeypatch):
    service = profiles(tmp_path, monkeypatch)
    result = select(service, "openai")
    assert result["api_key_set"] is False
    with pytest.raises(WebError, match="设置"):
        service.runtime_settings()
    select(service, "deepseek")
    assert service.runtime_settings().api_key.get_secret_value() == "deep-test"


def test_read_exposes_independent_saved_provider_model_without_keys(tmp_path, monkeypatch):
    service = profiles(tmp_path, monkeypatch)
    select(service, "openai", "open-test")
    service.update(
        ModelUpdate(
            provider="deepseek",
            model="deepseek-v4-pro",
            base_url="https://deep.example.test",
            api_key="deep-new-test",
        )
    )
    public = service.read()
    assert public["profiles"]["openai"]["model"] == "gpt-5.6-terra"
    assert public["profiles"]["deepseek"]["base_url"] == "https://deep.example.test"
    assert all("api_key" not in profile for profile in public["profiles"].values())


def test_mimo_and_two_deepseek_models_have_independent_connections(tmp_path, monkeypatch):
    service = profiles(tmp_path, monkeypatch)
    service.update(
        ModelUpdate(
            provider="deepseek",
            model="deepseek-v4-pro",
            base_url="https://pro.example.test",
            api_key="pro-test",
        )
    )
    service.update(
        ModelUpdate(
            provider="mimo",
            model="mimo-v2.6-pro",
            base_url="https://api.xiaomimimo.com/v1",
            api_key="mimo-test",
        )
    )
    flash = service.runtime_settings("deepseek:deepseek-v4-flash")
    pro = service.runtime_settings("deepseek:deepseek-v4-pro")
    mimo = service.runtime_settings("mimo:mimo-v2.6-pro")
    assert flash.api_key.get_secret_value() == "deep-test"
    assert pro.api_key.get_secret_value() == "pro-test"
    assert pro.base_url == "https://pro.example.test"
    assert mimo.api_key.get_secret_value() == "mimo-test"
    assert mimo.provider == "mimo"
    assert "mimo-test" not in repr(service.read())


def test_custom_connection_can_be_saved_without_changing_default(tmp_path, monkeypatch):
    service = profiles(tmp_path, monkeypatch)
    service.update(
        ModelUpdate(
            provider="custom",
            model="my-model",
            label="研究接口",
            base_url="https://custom.example.test/v1",
            api_key="custom-test",
            make_default=False,
        )
    )
    public = service.read()
    custom = next(c for c in public["connections"] if c["provider"] == "custom")
    assert custom["label"] == "研究接口"
    assert public["provider"] == "deepseek"
    selected = service.runtime_settings(custom["id"])
    assert selected.model == "my-model"
    assert selected.api_key.get_secret_value() == "custom-test"


def test_conversation_can_switch_between_connections_without_changing_global(tmp_path, monkeypatch):
    from xiliu.api.services.conversations import ConversationService
    from xiliu.api.store import AppStore

    service = profiles(tmp_path, monkeypatch)
    service.update(
        ModelUpdate(
            provider="mimo",
            model="mimo-v2.6-pro",
            base_url="https://api.xiaomimimo.com/v1",
            api_key="mimo-test",
            make_default=False,
        )
    )
    store = AppStore(tmp_path)
    conversations = ConversationService(store, service)
    cid = store.create()["id"]
    conversations.update(cid, {"model_override": "mimo:mimo-v2.6-pro"})
    assert conversations.get(cid)["model_override"] == "mimo:mimo-v2.6-pro"
    assert service.read()["provider"] == "deepseek"
    assert service.read("mimo:mimo-v2.6-pro")["provider"] == "mimo"
    conversations.update(cid, {"model_override": "deepseek:deepseek-v4-flash"})
    assert (
        service.runtime_settings(
            conversations.get(cid)["model_override"]
        ).api_key.get_secret_value()
        == "deep-test"
    )


def test_editing_active_connection_updates_default_without_switching_provider(
    tmp_path, monkeypatch
):
    service = profiles(tmp_path, monkeypatch)
    service.update(
        ModelUpdate(
            provider="deepseek",
            model="deepseek-v4-flash",
            base_url="https://new.example.test/v1",
            api_key="rotated-test",
            profile_id="deepseek:deepseek-v4-flash",
            make_default=False,
        )
    )
    selected = service.runtime_settings()
    assert selected.api_key.get_secret_value() == "rotated-test"
    assert selected.base_url == "https://new.example.test/v1"
    assert service.read()["provider"] == "deepseek"


def test_legacy_bare_override_uses_its_independent_connection(tmp_path, monkeypatch):
    service = profiles(tmp_path, monkeypatch)
    service.update(
        ModelUpdate(
            provider="deepseek",
            model="deepseek-v4-pro",
            base_url="https://pro.example.test/v1",
            api_key="pro-only-test",
            make_default=False,
        )
    )
    selected = service.runtime_settings("deepseek-v4-pro")
    assert selected.api_key.get_secret_value() == "pro-only-test"
    assert selected.base_url == "https://pro.example.test/v1"
