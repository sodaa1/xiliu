"""Bounded semantic repair remains supported by the checkpoint-compatible adapter."""

import pytest

from tests.integration.test_app_semantic_boundaries import run
from tests.integration.test_semantic_rule_matching import SemanticModel


class SequenceModel(SemanticModel):
    def __init__(self, outputs):
        super().__init__(outputs[0])
        self.outputs = outputs

    def with_structured_output(self, schema, **kwargs):
        outer = self

        class Parser:
            def invoke(self, messages):
                index = min(len(outer.rule_reads), len(outer.outputs) - 1)
                outer.rule_reads.append(messages.copy())
                return schema.model_validate(outer.outputs[index])

        return Parser()


@pytest.mark.parametrize(
    "bad",
    [
        dict(kind="workflow", domain="automations", action_id="automations.create"),
        dict(kind="write", domain="automations", action_id=None),
        dict(
            kind="write",
            domain="automations",
            action_id="automations.create",
            arguments={"name": "晨报", "prompt": "总结昨天待办", "hour": "9", "minute": 0},
        ),
    ],
)
def test_bad_labels_and_parameters_are_repaired_before_any_execution(tmp_path, bad):
    correct = dict(
        kind="write",
        domain="automations",
        action_id="automations.create",
        arguments={"name": "晨报", "prompt": "总结昨天待办", "hour": 9, "minute": 0},
    )
    model = SequenceModel([bad, correct])
    state, app, _ = run(
        tmp_path, correct, "创建自动任务「晨报」，每天九点总结昨天待办", model=model
    )
    assert len(model.rule_reads) == 2
    assert state["execution_result"]["status"] == "confirmation_required"
    assert len(state["app_receipts"]) == 1
    assert state["app_receipts"][0]["action_id"] == "automations.create"
    assert state["execution_result"]["semantic_repairs"]
    assert app.automations.list() == [] and app.tasks.list() == []


def test_repair_budget_is_bounded_and_failed_contract_never_writes(tmp_path):
    bad = dict(kind="write", domain="tasks", action_id="invented.action")
    model = SequenceModel([bad])
    state, app, _ = run(tmp_path, bad, "创建待办「论文」", model=model)
    assert len(model.rule_reads) == 3
    assert app.tasks.list() == []
    assert not state["app_receipts"]
    assert state["execution_result"]["reason_code"] == "semantic_contract_failed"


def test_real_missing_information_returns_model_question_without_retry(tmp_path):
    output = dict(kind="clarify", domain="automations", clarification="每天几点执行？")
    model = SequenceModel([output])
    state, _, _ = run(tmp_path, output, "创建自动任务「晨报」", model=model)
    assert len(model.rule_reads) == 1
    assert state["result"] == "每天几点执行？"


def test_read_write_conflict_is_repaired_to_registry_contract(tmp_path):
    bad = dict(kind="write", domain="tasks", action_id="tasks.list")
    correct = dict(kind="read", domain="tasks", action_id="tasks.list")
    model = SequenceModel([bad, correct])
    state, app, _ = run(tmp_path, correct, "目前待办有哪些", model=model)
    assert state["execution_result"]["verified"]
    assert len(model.rule_reads) == 2
    assert app.tasks.list() == []
