import pytest

from tests.integration.test_semantic_rule_matching import SemanticModel
from xiliu.app.selection import select_objects


@pytest.mark.parametrize("ids", [["invented"], ["real", "invented"], ["real", "real"], []])
def test_selection_rejects_unverified_or_duplicate_ids(ids):
    selected, _ = select_objects(
        SemanticModel({"ids": ids}),
        text="整理之前那份资料",
        memory={},
        rows=[{"id": "real", "title": "论文"}],
        action_id="inbox.classify_selected",
        multiple=True,
    )
    assert selected == []


def test_selection_accepts_only_actual_candidate():
    row = {"id": "real", "title": "论文"}
    selected, _ = select_objects(
        SemanticModel({"ids": ["real"]}),
        text="整理之前那份资料",
        memory={},
        rows=[row],
        action_id="inbox.classify_selected",
    )
    assert selected == [row]
