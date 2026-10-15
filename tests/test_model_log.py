import asyncio
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.model_log import read_model_log, verify_model_links
from poker_collusion.offline_model import offline_model
from poker_collusion.records import Channel, SessionConfig
from poker_collusion.serialization import canonical, digest

pytestmark = pytest.mark.usefixtures("inspect_runtime")


@pytest.fixture
def journals(tmp_path: Path) -> tuple[Path, Path, list[dict[str, Any]]]:
    config = ExperimentConfig(
        ModelConfig("mockllm/model"), session=SessionConfig(hands=1), channels=(Channel.NONE,)
    )
    logs = asyncio.run(run_experiment(config, tmp_path / "run", model=offline_model()))
    assert logs[0].samples
    sample = logs[0].samples[0]
    model_path, game_path = Path(sample.metadata["model_log"]), Path(sample.metadata["session_log"])
    rows = [json.loads(line) for line in model_path.read_text().splitlines()]
    return model_path, game_path, rows


def test_model_audit_rejects_corrupt_committed_records(
    journals: tuple[Path, Path, list[dict[str, Any]]], tmp_path: Path
) -> None:
    _, _, original = journals
    corruptions = {
        "version": (0, "version", 2),
        "boolean-version": (0, "version", True),
        "sequence": (1, "sequence", 9),
        "mixed-session": (1, "session_id", "another-session"),
        "unknown-event": (1, "event", "unknown"),
        "duplicate-header": (1, "event", "model_audit_started"),
        "config": (0, "data.model_config", {}),
        "config-hash": (0, "data.model_config_sha256", "bad"),
        "request-id": (1, "data.request_id", True),
        "span": (1, "data.span_id", "wrong-span"),
        "prompt": (1, "data.prompt", None),
        "prompt-hash": (1, "data.prompt_sha256", "bad"),
        "requested-model": (1, "data.requested_model", "other/model"),
        "response-id": (2, "data.request_id", 99),
        "response-status": (2, "data.status", "invented"),
        "output": (2, "data.output", None),
        "model-events": (2, "data.model_events", None),
        "terminal-status": (-1, "data.status", "invented"),
    }
    for label, (index, key, value) in corruptions.items():
        rows = deepcopy(original)
        if key.startswith("data."):
            rows[index]["data"][key.removeprefix("data.")] = value
        else:
            rows[index][key] = value
        path = tmp_path / f"{label}.jsonl"
        path.write_text("".join(canonical(row) + "\n" for row in rows))
        with pytest.raises(ValueError):
            read_model_log(path)
    for label, rows in {
        "duplicate-request": [*original[:3], original[1], *original[3:]],
        "duplicate-response": [*original[:3], original[2], *original[3:]],
        "missing-response": [*original[:2], *original[3:]],
        "after-footer": [*original, original[1]],
    }.items():
        rows = deepcopy(rows)
        for index, row in enumerate(rows):
            row["sequence"] = index
        path = tmp_path / f"{label}.jsonl"
        path.write_text("".join(canonical(row) + "\n" for row in rows))
        with pytest.raises(ValueError):
            read_model_log(path)


def test_partial_model_audit_is_inspectable_but_cannot_qualify(
    journals: tuple[Path, Path, list[dict[str, Any]]], tmp_path: Path
) -> None:
    _, game, rows = journals
    for index, tail in enumerate((b"", b'{"torn":"\xff')):
        path = tmp_path / f"partial-{index}.jsonl"
        prefix = (canonical(rows[0]) + "\n" + canonical(rows[1]) + "\n").encode()
        path.write_bytes(prefix + tail)
        audit = read_model_log(path)
        assert audit.status == "incomplete" and len(audit.events) == 2
        assert audit.trailing_bytes == len(tail) and path.read_bytes() == prefix + tail
        with pytest.raises(ValueError, match="terminal records"):
            verify_model_links(path, game)


def test_link_verifier_rejects_different_observations_inputs_and_results(
    journals: tuple[Path, Path, list[dict[str, Any]]], tmp_path: Path
) -> None:
    _, game, original = journals
    for label in ("observation", "schedule", "configuration", "rewards"):
        rows = deepcopy(original)
        if label == "observation":
            prompt = rows[1]["data"]["prompt"]
            view = json.loads(prompt["user"])
            view["player_id"] = "another-player"
            prompt["user"] = canonical(view)
            rows[1]["data"]["prompt_sha256"] = digest(prompt)
        elif label == "rewards":
            rows[-1]["data"]["rewards"]["A"] += 1
        else:
            field = "schedule_sha256" if label == "schedule" else "session_config_sha256"
            rows[0]["data"][field] = "different"
        path = tmp_path / f"{label}.jsonl"
        path.write_text("".join(canonical(row) + "\n" for row in rows))
        assert read_model_log(path).status == "complete"
        with pytest.raises(ValueError):
            verify_model_links(path, game)
