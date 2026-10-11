"""Desktop Git discovery, launch isolation, and safe failure diagnostics."""

import json
import logging
import subprocess
import sys
from types import SimpleNamespace

import pytest

from xiliu.core import checkpoint
from xiliu.errors import CheckpointError


@pytest.mark.skipif(sys.platform != "win32", reason="Windows installation fallback")
def test_standard_windows_git_is_found_when_path_is_missing(tmp_path, monkeypatch):
    installed = tmp_path / "Program Files" / "Git" / "cmd" / "git.exe"
    installed.parent.mkdir(parents=True)
    installed.touch()
    monkeypatch.setattr(checkpoint.shutil, "which", lambda _name: None)
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "Program Files"))
    monkeypatch.delenv("ProgramW6432", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    launches = []

    def launch(command, **kwargs):
        launches.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(checkpoint.subprocess, "run", launch)
    checkpoint._git(tmp_path, tmp_path / ".xiliu" / "checkpoints", "init", "--bare")

    assert launches[0][0] == str(installed)


def test_path_git_takes_precedence_over_standard_installation(tmp_path, monkeypatch):
    selected = str(tmp_path / "portable-git" / "git.exe")
    monkeypatch.setattr(checkpoint.shutil, "which", lambda _name: selected)
    launches = []

    def launch(command, **kwargs):
        launches.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(checkpoint.subprocess, "run", launch)
    checkpoint._git(tmp_path, tmp_path / ".xiliu" / "checkpoints", "init", "--bare")

    assert launches[0][0] == selected


def test_git_does_not_inherit_owner_pipe_or_open_console(tmp_path, monkeypatch):
    launches = []

    def launch(command, **kwargs):
        launches.append(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="refs/heads/checkpoint\n")

    monkeypatch.setattr(checkpoint.subprocess, "run", launch)
    value = checkpoint._git(
        tmp_path, tmp_path / ".xiliu" / "checkpoints", "symbolic-ref", "HEAD", output=True
    )

    assert value == "refs/heads/checkpoint"
    assert launches[0].get("stdin") == subprocess.DEVNULL
    assert launches[0].get("creationflags", 0) == (0x08000000 if sys.platform == "win32" else 0)
    assert launches[0]["shell"] is False


@pytest.mark.parametrize(
    ("error_type", "exit_code"),
    [("CalledProcessError", 128), ("TimeoutExpired", None), ("FileNotFoundError", None)],
)
def test_git_failure_logs_safe_metadata_only(tmp_path, monkeypatch, caplog, error_type, exit_code):
    private = "secret-path-sk-test-token"

    def launch(command, **kwargs):
        if error_type == "CalledProcessError":
            raise subprocess.CalledProcessError(128, command, output=private, stderr=private)
        if error_type == "TimeoutExpired":
            raise subprocess.TimeoutExpired(command, 30, output=private, stderr=private)
        raise FileNotFoundError(private)

    monkeypatch.setattr(checkpoint.subprocess, "run", launch)
    with (
        caplog.at_level(logging.WARNING, logger=checkpoint.__name__),
        pytest.raises(CheckpointError, match="Checkpoint persistence failed"),
    ):
        checkpoint._git(tmp_path / private, tmp_path / private, "init", "--bare", private)

    records = [record for record in caplog.records if record.name == checkpoint.__name__]
    assert len(records) == 1
    record = records[0]
    assert record.checkpoint_step == "init"
    assert record.checkpoint_error_type == error_type
    assert record.checkpoint_exit_code == exit_code
    assert private not in caplog.text
    assert str(tmp_path) not in caplog.text
    assert record.exc_info is None


def test_unknown_git_step_cannot_leak_argument_into_log(tmp_path, monkeypatch, caplog):
    private = "secret-path-sk-test-token"

    def launch(command, **kwargs):
        raise subprocess.CalledProcessError(128, command, stderr=private)

    monkeypatch.setattr(checkpoint.subprocess, "run", launch)
    with (
        caplog.at_level(logging.WARNING, logger=checkpoint.__name__),
        pytest.raises(CheckpointError),
    ):
        checkpoint._git(tmp_path, tmp_path, private)

    records = [record for record in caplog.records if record.name == checkpoint.__name__]
    assert len(records) == 1
    assert records[0].checkpoint_step == "unknown"
    assert private not in caplog.text


def test_absent_git_ref_is_not_logged_as_failure(tmp_path, monkeypatch, caplog):
    def launch(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(checkpoint.subprocess, "run", launch)
    with caplog.at_level(logging.WARNING, logger=checkpoint.__name__):
        result = checkpoint._git(tmp_path, tmp_path, "show-ref", absent_ok=True)

    assert result == "<absent>"
    assert not [record for record in caplog.records if record.name == checkpoint.__name__]


def test_snapshot_blob_reads_use_same_isolated_git_launcher(tmp_path, monkeypatch):
    launches = []
    selected = str(tmp_path / "portable-git" / "git.exe")
    monkeypatch.setattr(checkpoint.shutil, "which", lambda _name: selected)

    def launch(command, **kwargs):
        launches.append((command, kwargs))
        if "symbolic-ref" in command:
            return subprocess.CompletedProcess(command, 0, stdout="refs/heads/checkpoint\n")
        return subprocess.CompletedProcess(command, 0, stdout=b"" if not kwargs.get("text") else "")

    monkeypatch.setattr(checkpoint.subprocess, "run", launch)
    result = checkpoint._read_tree(tmp_path, tmp_path / ".xiliu" / "checkpoints", "a" * 40)

    assert result == {}
    assert len(launches) == 3
    for command, kwargs in launches:
        assert command[0] == selected
        assert kwargs.get("stdin") == subprocess.DEVNULL
        assert kwargs.get("creationflags", 0) == (0x08000000 if sys.platform == "win32" else 0)
    assert launches[-1][1].get("text") is False


def test_checkpoint_timeout_is_not_retried_during_run_cleanup(tmp_path, monkeypatch):
    from xiliu.core.agent import stream_agent
    from xiliu.core.trace import TraceRecorder

    context = SimpleNamespace(workspace=tmp_path, checkpoint_mode="light", trace_mode="full")
    manager = checkpoint.CheckpointManager(context)
    trace = TraceRecorder(context)
    launches = []

    def launch(command, **kwargs):
        launches.append(command)
        raise subprocess.TimeoutExpired(command, 30)

    monkeypatch.setattr(checkpoint.subprocess, "run", launch)
    with pytest.raises(CheckpointError, match="Checkpoint persistence failed"):
        list(
            stream_agent(
                object(),
                {"task": "offline timeout", "session_id": "fixture", "max_attempts": 1},
                memory_manager=None,
                checkpoint_manager=manager,
                trace_recorder=trace,
            )
        )

    assert len(launches) == 1, "cleanup must not repeat a failed 30 second Git operation"
    summary = json.loads((trace.root / "trace.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["checkpoint_count"] == 0


@pytest.mark.parametrize("workflow_fails", [False, True])
def test_terminal_checkpoint_and_trace_are_preserved_for_other_outcomes(
    tmp_path, monkeypatch, workflow_fails
):
    from xiliu.core import agent
    from xiliu.core.trace import TraceRecorder

    context = SimpleNamespace(workspace=tmp_path, checkpoint_mode="light", trace_mode="full")
    manager = checkpoint.CheckpointManager(context)
    trace = TraceRecorder(context)

    class Workflow:
        def stream(self, *args, **kwargs):
            if workflow_fails:
                raise ValueError("offline workflow failure")
            return iter(())

    monkeypatch.setattr(agent, "build_workflow", lambda *args, **kwargs: Workflow())
    events = agent.stream_agent(
        object(),
        {"task": "offline cleanup", "session_id": "fixture", "max_attempts": 1},
        memory_manager=None,
        checkpoint_manager=manager,
        trace_recorder=trace,
    )
    if workflow_fails:
        with pytest.raises(ValueError, match="offline workflow failure"):
            list(events)
    else:
        list(events)

    expected_status = "failed" if workflow_fails else "completed"
    payload = json.loads((manager.root / "checkpoint.json").read_text(encoding="utf-8"))
    summary = json.loads((trace.root / "trace.json").read_text(encoding="utf-8"))
    assert payload["status"] == expected_status
    assert summary["status"] == expected_status
    assert summary["checkpoint_count"] == 2
