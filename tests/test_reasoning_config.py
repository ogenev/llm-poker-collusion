import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from poker_collusion.inspect_transport import generation_config
from poker_collusion.model_adapter import ModelConfig, ReasoningEffort
from poker_collusion.serialization import canonical, digest


@pytest.mark.parametrize(
    "path", ["configs/qualification-basics-gpt-6.1-sol.json", "configs/inspect-live-smoke.json"]
)
def test_legacy_configuration_bytes_and_hashes_are_preserved(path: str) -> None:
    saved = json.loads(Path(path).read_text())["model"]
    config = ModelConfig.from_json(canonical(saved))
    assert config.reasoning_effort is None
    assert config.to_json() == canonical(saved)
    assert config.sha256 == digest(saved)
    assert "reasoning_effort" not in generation_config(config, 1).model_dump(exclude_none=True)


@pytest.mark.parametrize("effort", ["none", "minimal", "low", "medium", "high", "xhigh", "max"])
def test_explicit_effort_round_trips_and_changes_provenance(effort: ReasoningEffort) -> None:
    default = ModelConfig("openai/gpt-6.1-sol")
    config = replace(default, reasoning_effort=effort)
    saved = json.loads(config.to_json())
    assert saved["version"] == 2 and saved["settings"]["reasoning_effort"] == effort
    assert ModelConfig.from_json(config.to_json()) == config
    assert config.sha256 != default.sha256
    assert generation_config(config, 1).reasoning_effort == effort
    if effort != "high":
        assert config.sha256 != replace(config, reasoning_effort="high").sha256


@pytest.mark.parametrize("effort", ["", "MEDIUM", "ultra", True, 1, [], {}])
def test_invalid_reasoning_is_rejected_in_python_and_json(effort: object) -> None:
    with pytest.raises(ValueError, match="reasoning effort"):
        ModelConfig("model", reasoning_effort=cast(ReasoningEffort, effort))
    saved = json.loads(ModelConfig("model", reasoning_effort="medium").to_json())
    saved["settings"]["reasoning_effort"] = effort
    with pytest.raises(ValueError, match="reasoning effort"):
        ModelConfig.from_json(json.dumps(saved))


@pytest.mark.parametrize("change", ["null", "missing", "v1_with_effort", "future_version"])
def test_reasoning_schema_requires_a_consistent_version(change: str) -> None:
    saved = json.loads(ModelConfig("model", reasoning_effort="medium").to_json())
    if change == "null":
        saved["settings"]["reasoning_effort"] = None
    elif change == "missing":
        del saved["settings"]["reasoning_effort"]
    else:
        saved["version"] = 1 if change == "v1_with_effort" else 4
    with pytest.raises(ValueError):
        ModelConfig.from_json(json.dumps(saved))
