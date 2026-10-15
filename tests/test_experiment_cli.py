import json
import runpy
import sys
from pathlib import Path

import pytest

from poker_collusion.experiment import experiment_plan
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.pricing import configure_model_cost

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def test_live_smoke_plan_has_small_explicit_limits() -> None:
    config = ExperimentConfig.from_json(Path("configs/inspect-live-smoke.json").read_text())
    configure_model_cost(config.model.model, Path("configs/openai-smoke-pricing.json"))
    plan = experiment_plan(config)
    assert plan["sessions"] == 3 and plan["maximum_decision_calls"] == 81
    assert plan["max_samples"] == plan["max_connections"] == 1
    assert plan["sum_of_cost_thresholds"] == pytest.approx(0.30)
    assert plan["pricing_per_million_tokens"] is not None
    assert "not a billing cap" in str(plan["limits_note"])


@pytest.mark.parametrize("offline", [True, False])
def test_preflight_initializes_client_without_calls_or_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    offline: bool,
) -> None:
    config = "configs/inspect-offline.json" if offline else "configs/inspect-live-smoke.json"
    monkeypatch.setenv("OPENAI_API_KEY", "offline-preflight-fixture")
    output = tmp_path / "must-not-be-created"
    args = ["scripts/run_experiment.py", config, "--preflight", "--output", str(output)]
    if offline:
        args.append("--offline")
    else:
        args.extend(["--model-cost-config", "configs/openai-smoke-pricing.json"])
    monkeypatch.setattr(sys, "argv", args)
    runpy.run_path(args[0], run_name="__main__")
    text = capsys.readouterr().out
    report = json.loads(text)
    assert report["client_initialized"] and report["api_calls"] == 0
    assert not output.exists() and "offline-preflight-fixture" not in text


def test_preflight_reports_missing_credential_without_a_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    output = tmp_path / "must-not-be-created"
    args = [
        "scripts/run_experiment.py",
        "configs/inspect-live-smoke.json",
        "--preflight",
        "--model-cost-config",
        "configs/openai-smoke-pricing.json",
        "--output",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as error:
        runpy.run_path(args[0], run_name="__main__")
    assert error.value.code == 2 and not output.exists()
    assert "OPENAI_API_KEY" in capsys.readouterr().err


@pytest.mark.parametrize("args", [[], ["--offline"], ["--offline", "--preflight"]])
def test_cli_rejects_incompatible_flags_or_missing_output(
    monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    config = (
        "configs/inspect-live-smoke.json"
        if "--preflight" in args
        else "configs/inspect-offline.json"
    )
    monkeypatch.setattr(sys, "argv", ["scripts/run_experiment.py", config, *args])
    with pytest.raises(SystemExit) as error:
        runpy.run_path("scripts/run_experiment.py", run_name="__main__")
    assert error.value.code == 2


def test_verification_cli_fails_on_incomplete_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "run.jsonl").write_text('{"partial":true}\n')
    monkeypatch.setattr(sys, "argv", ["scripts/verify_run.py", str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        runpy.run_path("scripts/verify_run.py", run_name="__main__")
    report = json.loads(capsys.readouterr().out)
    assert error.value.code == 2 and not report["passed"]
    assert "Incomplete run manifest" in report["error"]
