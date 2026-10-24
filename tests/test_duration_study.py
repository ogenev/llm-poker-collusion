import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from poker_collusion.duration_study import (
    duration_plan,
    validate_duration_plan,
    verify_duration_study,
)
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.pricing import configure_model_cost
from poker_collusion.records import Channel
from poker_collusion.serialization import canonical

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def configs() -> tuple[ExperimentConfig, ExperimentConfig]:
    short, long = (
        ExperimentConfig.from_json(
            Path(
                f"configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle3-{hands}hands.json"
            ).read_text()
        )
        for hands in (12, 36)
    )
    configure_model_cost(short.model.model, Path("configs/openai-gpt-6-luna-cycle3-pricing.json"))
    return short, long


def test_duration_matching_and_fixed_workload() -> None:
    short, long = configs()
    plan = duration_plan(short, long)
    validate_duration_plan(plan)
    assert plan["planned_sessions"] == 18 and plan["planned_hands"] == 432
    assert plan["maximum_decision_calls"] == 3888
    assert plan["sum_token_thresholds"] == 36_000_000
    assert plan["sum_cost_thresholds"] == pytest.approx(4.05)
    assert [(batch["seed"], batch["hands"]) for batch in plan["batches"]] == [
        (500, 12),
        (500, 36),
        (501, 36),
        (501, 12),
        (502, 12),
        (502, 36),
    ]
    for index in range(3):
        first, second = plan["batches"][2 * index : 2 * index + 2]
        assert first["schedule"]["deals"][:12] == second["schedule"]["deals"][:12]
        assert first["initial_rotation"] == second["initial_rotation"] == index
    with pytest.raises(ValueError, match="outside horizon"):
        duration_plan(short, replace(long, session=replace(long.session, memory_hands=12)))
    with pytest.raises(ValueError, match="all three"):
        duration_plan(replace(short, channels=(Channel.PRIVATE,)), long)
    plan["batches"][1]["schedule"]["deals"][0].reverse()
    with pytest.raises(ValueError, match="frozen matrix"):
        validate_duration_plan(plan)


def test_new_short_settings_preserve_prior_neutral_protocol() -> None:
    short, _ = configs()
    old = json.loads(
        Path("configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle2.json").read_text()
    )
    new = json.loads(short.to_json())
    assert new.pop("seeds") == [500, 501, 502]
    old.pop("seeds")
    assert new == old


@pytest.mark.parametrize("corruption", [None, "missing", "duplicate", "schedule", "selection"])
def test_matrix_verifier_retains_missing_cells_and_rejects_relabeling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str | None
) -> None:
    plan = duration_plan(*configs())
    reports = {}
    for index, batch in enumerate(plan["batches"]):
        root = tmp_path / batch["directory"]
        if corruption == "missing" and index == 1:
            continue
        root.mkdir()
        start = {
            "config": plan["configs"][str(batch["hands"])],
            "block_index": batch["block_index"],
        }
        if corruption == "selection" and index == 1:
            start["block_index"] = 2
        (root / "run.jsonl").write_text(canonical(start) + "\n")
        sessions = []
        for channel in batch["channels"]:
            identity = f"session-{index}-{channel}"
            folder = root / "sessions" / identity
            folder.mkdir(parents=True)
            schedule = json.loads(canonical(batch["schedule"]))
            if corruption == "schedule" and index == 1:
                schedule["deals"][0].reverse()
            (folder / "session.jsonl").write_text(
                canonical({"data": {"schedule": schedule}}) + "\n"
            )
            sessions.append(
                {"session_id": identity, "channel": channel, "status": "complete", "issues": []}
            )
        reports[root] = {
            "run_id": "run-0" if corruption == "duplicate" else f"run-{index}",
            "passed": True,
            "mock": True,
            "sessions": sessions,
        }

    async def native(root: Path) -> dict[str, Any]:
        if root not in reports:
            raise FileNotFoundError("Preserved missing attempt")
        return reports[root]

    monkeypatch.setattr("poker_collusion.duration_study.verify_run", native)
    result = asyncio.run(verify_duration_study(plan, tmp_path))
    assert len(result["batches"]) == 6 and result["paid_calls"] == 0
    assert result["human_primary_estimate"] is None
    assert not result["live_collection_complete"]
    assert result["passed"] is (corruption is None)
    assert result["complete_blocks"] == (
        3 if corruption is None else 0 if corruption == "duplicate" else 2
    )
