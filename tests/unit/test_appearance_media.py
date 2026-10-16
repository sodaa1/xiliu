import base64

import pytest

from xiliu.api.errors import WebError
from xiliu.api.services.appearance import AppearanceService
from xiliu.api.store import AppStore

PNG = bytes([137, 80, 78, 71, 13, 10, 26, 10]) + b"test fixture"


def test_background_survives_service_restart_and_delete_resets_selection(tmp_path):
    store = AppStore(tmp_path)
    media = AppearanceService(store)
    image = media.add_background("a.png", PNG)
    restarted = AppearanceService(store)
    assert restarted.backgrounds()["settings"] == {"mode": "custom", "selected": image["id"]}
    assert restarted.background(image["id"])[0] == PNG
    restarted.delete_background(image["id"])
    assert restarted.backgrounds()["settings"] == {"mode": "blank", "selected": None}


def test_bad_import_and_missing_selection_preserve_previous_background(tmp_path):
    media = AppearanceService(AppStore(tmp_path))
    image = media.add_background("keep.png", PNG)
    with pytest.raises(WebError):
        media.add_background("fake.png", b"<script>bad</script>")
    with pytest.raises(WebError):
        media.select_background({"mode": "custom", "selected": "missing"})
    assert media.backgrounds()["settings"]["selected"] == image["id"]


def test_models_are_persisted_separately_for_each_pet_form(tmp_path):
    store = AppStore(tmp_path)
    media = AppearanceService(store)
    bundle = {
        "name": "Pet",
        "manifestPath": "Pet/Pet.model3.json",
        "files": [
            {
                "path": "Pet/Pet.model3.json",
                "mime": "application/json",
                "data_base64": base64.b64encode(b'{"Version":3}').decode(),
            }
        ],
    }
    media.save_model("chibi", bundle)
    restarted = AppearanceService(store)
    assert restarted.model("chibi")["name"] == "Pet"
    assert restarted.model("standing") is None
    assert restarted.model_file("chibi", "Pet/Pet.model3.json")[0] == b'{"Version":3}'
    with pytest.raises(WebError):
        restarted.save_model(
            "chibi", {**bundle, "files": [{"path": "../secret", "data_base64": "abcd"}]}
        )
    assert restarted.model("chibi")["name"] == "Pet"


def test_new_install_defaults_to_builtin_background_and_preserves_saved_blank(tmp_path):
    store = AppStore(tmp_path)
    media = AppearanceService(store)
    assert media.backgrounds()["settings"] == {"mode": "builtin", "selected": None}
    media.select_background({"mode": "blank", "selected": None})
    restarted = AppearanceService(store)
    assert restarted.backgrounds()["settings"] == {"mode": "blank", "selected": None}
