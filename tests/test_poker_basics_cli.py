import json
import runpy
import sys
from pathlib import Path

import pytest
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo

from poker_collusion.offline_model import scripted_output
from poker_collusion.poker_basics import BasicsConfig
from poker_collusion.poker_basics_run import prepare_basics

pytestmark = pytest.mark.usefixtures("inspect_runtime")


@pytest.mark.parametrize("offline", [True, False])
def test_preflight_makes_no_calls_and_creates_no_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    offline: bool,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "offline-preflight-fixture")
    args = [
        "scripts/check_poker_basics.py",
        "configs/qualification-basics.json",
        "--preflight",
        "--output",
        str(tmp_path / "unused"),
    ]
    args += (
        ["--offline"] if offline else ["--model-cost-config", "configs/openai-smoke-pricing.json"]
    )
    monkeypatch.setattr(sys, "argv", args)
    runpy.run_path(args[0], run_name="__main__")
    result = json.loads(capsys.readouterr().out)
    assert result["api_calls"] == 0 and result["mock"] == offline
    assert result["plan"]["maximum_decision_calls"] == 12
    assert not (tmp_path / "unused").exists()


def test_offline_cli_needs_no_key_and_keeps_mock_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    args = [
        "scripts/check_poker_basics.py",
        "configs/qualification-basics.json",
        "--offline",
        "--output",
        str(tmp_path / "offline"),
    ]
    monkeypatch.setattr(sys, "argv", args)
    runpy.run_path(args[0], run_name="__main__")
    capsys.readouterr()
    summary = json.loads((tmp_path / "offline" / "summary.json").read_text())
    assert summary["result"] == "pass" and summary["mock"]
    assert not summary["live_basic_check_passed"]


def test_cli_requires_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/check_poker_basics.py", "configs/qualification-basics.json", "--offline"],
    )
    with pytest.raises(SystemExit) as error:
        runpy.run_path(sys.argv[0], run_name="__main__")
    assert error.value.code == 2


def test_cli_failure_is_nonzero_and_retains_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The existing offline policy always calls here, so every J probe fails.
    requested = BasicsConfig.from_json(Path("configs/qualification-basics.json").read_text())
    effective, _ = prepare_basics(requested, offline=True)

    def always_call(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        settings: GenerateConfig,
    ) -> ModelOutput:
        response = scripted_output(messages, tools, choice, settings)
        response.model = effective.model.model
        return response

    model = get_model(effective.model.model, memoize=False, custom_outputs=always_call)
    monkeypatch.setattr(
        "poker_collusion.poker_basics_run.prepare_basics",
        lambda config, offline: (effective, model),
    )
    args = [
        "scripts/check_poker_basics.py",
        "configs/qualification-basics.json",
        "--offline",
        "--output",
        str(tmp_path / "failed"),
    ]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as error:
        runpy.run_path(args[0], run_name="__main__")
    assert error.value.code == 2
    summary = json.loads((tmp_path / "failed" / "summary.json").read_text())
    assert summary["result"] == "fail" and summary["failed"] == 6
    assert summary["attempted_calls"] == 12
