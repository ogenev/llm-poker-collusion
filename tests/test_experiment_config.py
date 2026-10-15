import json
from pathlib import Path
from typing import Any

import pytest

from poker_collusion.experiment import poker_task
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.prompts import Instruction
from poker_collusion.records import Channel, SessionConfig


def test_experiment_configuration_round_trips() -> None:
    config = ExperimentConfig(ModelConfig("mockllm/model"), seeds=(-4, 2), max_samples=2)
    assert ExperimentConfig.from_json(config.to_json()) == config


@pytest.mark.parametrize("path", sorted(Path("configs").glob("*.json")))
def test_shipped_configurations_are_valid(path: Path) -> None:
    config = ExperimentConfig.from_json(path.read_text())
    assert ExperimentConfig.from_json(config.to_json()) == config


@pytest.mark.parametrize(
    "updates",
    [
        {"seeds": ()},
        {"seeds": [0]},
        {"seeds": (0, 0)},
        {"seeds": (True,)},
        {"channels": ()},
        {"channels": (Channel.NONE, Channel.NONE)},
        {"channels": ("private",)},
        {"session": SessionConfig(channel=Channel.PUBLIC)},
        {"model": "mockllm/model"},
        {"max_samples": 0},
        {"max_samples": True},
        {"max_connections": 0},
        {"token_limit": 0},
        {"token_limit": 1.5},
        {"cost_limit": 0},
        {"cost_limit": float("nan")},
        {"cost_limit": True},
        {"cost_limit": 10**400},
        {"session_time_limit": 0},
        {"session_time_limit": float("inf")},
    ],
)
def test_invalid_experiment_configuration_is_rejected(updates: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        ExperimentConfig(**{"model": ModelConfig("mockllm/model"), **updates})


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", 2),
        ("version", True),
        ("kind", "other"),
        ("extra", 0),
        ("seeds", "0"),
        ("channels", ["combined"]),
        ("session_time_limit", "30"),
    ],
)
def test_saved_config_rejects_invalid_fields(field: str, value: object) -> None:
    data = json.loads(ExperimentConfig(ModelConfig("mockllm/model")).to_json())
    data[field] = value
    with pytest.raises(ValueError):
        ExperimentConfig.from_json(json.dumps(data))


def test_control_requires_communication_and_stays_separate() -> None:
    model = ModelConfig("mockllm/model", Instruction.COORDINATION_CONTROL)
    with pytest.raises(ValueError, match="communication-enabled"):
        ExperimentConfig(model)
    config = ExperimentConfig(model, channels=(Channel.PRIVATE, Channel.PUBLIC))
    assert ExperimentConfig.from_json(config.to_json()) == config


def test_unpriced_model_cannot_silently_ignore_cost_limit(tmp_path: Path) -> None:
    config = ExperimentConfig(ModelConfig("mockllm/model"), cost_limit=1.0)
    with pytest.raises(ValueError, match="requires Inspect pricing"):
        poker_task(config, tmp_path, "test-run")


def test_task_has_matched_schedules_and_balanced_initial_seats(tmp_path: Path) -> None:
    config = ExperimentConfig(ModelConfig("mockllm/model"), seeds=(10, 20, 30))
    task = poker_task(config, tmp_path, "run")
    samples = list(task.dataset)
    assert len(samples) == 9
    for index in range(3):
        block = samples[index * 3 : index * 3 + 3]
        metadata = [sample.metadata for sample in block]
        assert all(m is not None for m in metadata)
        assert len({m["schedule"] for m in metadata if m}) == 1
        assert len({m["matched_block_id"] for m in metadata if m}) == 1
        assert metadata[0] is not None
        assert json.loads(metadata[0]["schedule"])["initial_rotation"] == index
    assert task.token_limit == config.token_limit
