import asyncio
import json
import runpy
import sys
from pathlib import Path
from typing import Any

import pytest

from poker_collusion.experiment import experiment_plan, poker_task, run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.offline_model import offline_model
from poker_collusion.records import SessionConfig
from poker_collusion.verification import verify_run

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def selected_config() -> ExperimentConfig:
    return ExperimentConfig(
        ModelConfig("mockllm/model"), session=SessionConfig(hands=1), seeds=(300, 301, 302)
    )


@pytest.mark.parametrize("block_index", [0, 1, 2])
def test_selection_preserves_original_sample_ids_and_schedules(
    tmp_path: Path, block_index: int
) -> None:
    config = selected_config()
    original = list(poker_task(config, tmp_path, "run").dataset)
    selected = list(poker_task(config, tmp_path, "run", block_index=block_index).dataset)
    assert selected == original[3 * block_index : 3 * block_index + 3]
    assert selected[0].metadata is not None
    schedule = json.loads(selected[0].metadata["schedule"])
    assert schedule["seed"] == 300 + block_index
    assert schedule["initial_rotation"] == block_index
    plan = experiment_plan(config, block_index=block_index)
    assert plan["sessions"] == 3 and plan["maximum_decision_calls"] == 27
    assert plan["selected_block_indices"] == [block_index]


@pytest.mark.parametrize("block_index", [-1, 3, True, 1.0, "2"])
def test_invalid_selection_fails_before_artifacts(tmp_path: Path, block_index: Any) -> None:
    output = tmp_path / "run"
    with pytest.raises(ValueError):
        asyncio.run(
            run_experiment(
                selected_config(), output, model=offline_model(), block_index=block_index
            )
        )
    assert not output.exists()


@pytest.fixture
def selected_run(tmp_path: Path) -> Path:
    output = tmp_path / "run"
    asyncio.run(run_experiment(selected_config(), output, model=offline_model(), block_index=2))
    return output


def test_selected_run_verifies_only_three_original_samples(selected_run: Path) -> None:
    report = asyncio.run(verify_run(selected_run))
    assert report["passed"] and report["selected_block_indices"] == [2]
    assert {s["sample_id"] for s in report["sessions"]} == {
        "block-2-none",
        "block-2-public",
        "block-2-private",
    }
    assert len(list((selected_run / "sessions").iterdir())) == 3
    start = json.loads((selected_run / "run.jsonl").read_text().splitlines()[0])
    assert start["block_index"] == 2
    assert start["config"]["seeds"] == [300, 301, 302]
    assert start["plan"]["sessions"] == 3


@pytest.mark.parametrize("damage", ["omit", "change", "invalid"])
def test_verifier_rejects_changed_selection(selected_run: Path, damage: str) -> None:
    path = selected_run / "run.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if damage == "omit":
        rows[0].pop("block_index")
    else:
        rows[0]["block_index"] = 1 if damage == "change" else True
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError):
        asyncio.run(verify_run(selected_run))


@pytest.mark.parametrize("preflight", [True, False])
def test_cli_applies_block_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    preflight: bool,
) -> None:
    config = tmp_path / "config.json"
    config.write_text(selected_config().to_json())
    output = tmp_path / "output"
    args = [
        "scripts/run_experiment.py",
        str(config),
        "--offline",
        "--block-index",
        "2",
        "--output",
        str(output),
    ]
    if preflight:
        args.append("--preflight")
    monkeypatch.setattr(sys, "argv", args)
    runpy.run_path(args[0], run_name="__main__")
    if preflight:
        report = json.loads(capsys.readouterr().out)
        assert report["api_calls"] == 0 and report["plan"]["sessions"] == 3
        assert report["plan"]["selected_block_indices"] == [2]
        assert not output.exists()
    else:
        report = asyncio.run(verify_run(output))
        assert report["passed"] and report["selected_block_indices"] == [2]
