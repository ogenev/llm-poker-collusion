import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import ModelEvent
from inspect_ai.log import read_eval_log, write_eval_log
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo

from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.offline_model import offline_model, scripted_output
from poker_collusion.records import Channel, SessionConfig
from poker_collusion.serialization import canonical
from poker_collusion.verification import verify_run

pytestmark = pytest.mark.usefixtures("inspect_runtime")


@pytest.fixture
def run_directory(tmp_path: Path) -> Path:
    config = ExperimentConfig(ModelConfig("mockllm/model"), session=SessionConfig(hands=1))
    root = tmp_path / "run"
    asyncio.run(run_experiment(config, root, model=offline_model()))
    return root


def test_saved_run_verifies_after_moving_artifacts(run_directory: Path, tmp_path: Path) -> None:
    destination = tmp_path / "copied"
    shutil.copytree(run_directory, destination)
    report = asyncio.run(verify_run(destination))
    assert report["passed"] and report["mock"]
    assert sum(session["calls"] for session in report["sessions"]) == 21
    assert sum(session["total_tokens"] for session in report["sessions"]) == 2310
    assert {session["channel"] for session in report["sessions"]} == {"none", "public", "private"}


@pytest.mark.parametrize(
    "damage",
    [
        "manifest_hash",
        "partial_manifest",
        "missing_sample",
        "duplicate_sample",
        "input",
        "output",
        "missing_journal",
        "extra_session",
    ],
)
def test_verifier_rejects_missing_or_changed_evidence(run_directory: Path, damage: str) -> None:
    manifest = run_directory / "run.jsonl"
    if damage == "partial_manifest":
        manifest.write_text(manifest.read_text().splitlines()[0] + "\n")
    elif damage == "manifest_hash":
        rows = [json.loads(line) for line in manifest.read_text().splitlines()]
        rows[0]["config_sha256"] = "wrong"
        manifest.write_text("".join(canonical(row) + "\n" for row in rows))
    elif damage == "extra_session":
        (run_directory / "sessions" / "unlisted-attempt").mkdir()
    elif damage == "missing_journal":
        next((run_directory / "sessions").glob("*/model.jsonl")).write_text("")
    else:
        path = next((run_directory / "inspect").glob("*.eval"))
        log = read_eval_log(str(path), resolve_attachments="full")
        assert log.samples
        if damage == "missing_sample":
            log.samples = log.samples[:-1]
        elif damage == "duplicate_sample":
            duplicate = log.samples[0].model_copy(deep=True)
            duplicate.epoch = 2
            log.samples.append(duplicate)
        else:
            event = next(e for e in log.samples[0].events if isinstance(e, ModelEvent))
            if damage == "input":
                event.input[-1].content = "leaked shared transcript"
            else:
                event.output.completion = '{"type":"bet","action":"fold"}'
        write_eval_log(log, str(path))
    with pytest.raises(ValueError):
        asyncio.run(verify_run(run_directory))


@pytest.mark.parametrize("evidence", ["malformed", "usage", "provider_error"])
def test_failed_or_unmetered_calls_do_not_qualify(tmp_path: Path, evidence: str) -> None:
    def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        if evidence == "provider_error":
            raise RuntimeError("fake provider failure")
        result = scripted_output(messages, tools, choice, config)
        if evidence == "malformed":
            result.completion = "not JSON"
            result.choices[0].message.content = result.completion
        else:
            assert result.usage
            result.usage.total_tokens = 0
        return result

    config = ExperimentConfig(
        ModelConfig("mockllm/model"), session=SessionConfig(hands=1), channels=(Channel.NONE,)
    )
    model = get_model("mockllm/model", custom_outputs=output, memoize=False)
    asyncio.run(run_experiment(config, tmp_path / "run", model=model))
    report = asyncio.run(verify_run(tmp_path / "run"))
    assert not report["passed"] and report["sessions"][0]["issues"]


def test_missing_raw_payload_is_visible_in_report(run_directory: Path) -> None:
    path = next((run_directory / "inspect").glob("*.eval"))
    log = read_eval_log(str(path), resolve_attachments="full")
    assert log.samples
    sample = log.samples[0]
    event = next(e for e in sample.events if isinstance(e, ModelEvent))
    event.call = None
    write_eval_log(log, str(path))
    journal = run_directory / "sessions" / sample.metadata["session_id"] / "model.jsonl"
    rows: list[dict[str, Any]] = [json.loads(line) for line in journal.read_text().splitlines()]
    for row in rows:
        if row["event"] == "call_finished":
            for captured in row["data"]["model_events"]:
                if captured["uuid"] == event.uuid:
                    captured["call"] = None
    journal.write_text("".join(canonical(row) + "\n" for row in rows))
    report = asyncio.run(verify_run(run_directory))
    assert not report["passed"]
    assert any(
        "Raw provider" in issue for session in report["sessions"] for issue in session["issues"]
    )


@pytest.mark.parametrize(
    ("overrides", "valid"),
    [
        ({"total_tokens": 1}, False),
        ({"input_tokens": 99}, False),
        ({"input_tokens_cache_read": -1, "total_tokens": 109}, False),
        ({"input_tokens_cache_write": -1, "total_tokens": 109}, False),
        ({"reasoning_tokens": -1}, False),
        ({"reasoning_tokens": 11}, False),
        ({"reasoning_tokens": 8, "total_tokens": 118}, False),
        (
            {
                "input_tokens": 60,
                "input_tokens_cache_read": 30,
                "input_tokens_cache_write": 10,
                "reasoning_tokens": 8,
            },
            True,
        ),
    ],
)
def test_token_components_must_reconcile(
    tmp_path: Path, overrides: dict[str, int], valid: bool
) -> None:
    def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        result = scripted_output(messages, tools, choice, config)
        assert result.usage
        for field, value in overrides.items():
            setattr(result.usage, field, value)
        return result

    config = ExperimentConfig(
        ModelConfig("mockllm/model"), session=SessionConfig(hands=1), channels=(Channel.NONE,)
    )
    model = get_model("mockllm/model", custom_outputs=output, memoize=False)
    asyncio.run(run_experiment(config, tmp_path / "run", model=model))
    report = asyncio.run(verify_run(tmp_path / "run"))
    session = report["sessions"][0]
    assert session["status"] == "complete"
    assert report["passed"] is valid
    if valid:
        assert session["input_tokens"] == 180
        assert session["input_tokens_cache_read"] == 90
        assert session["input_tokens_cache_write"] == 30
        assert session["output_tokens"] == 30
        assert session["reasoning_tokens"] == 24
        assert session["total_tokens"] == 330
    else:
        assert any("Token usage" in issue for issue in session["issues"])


@pytest.mark.parametrize(
    "field",
    [
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "input_tokens_cache_read",
        "input_tokens_cache_write",
        "reasoning_tokens",
        "model",
    ],
)
def test_session_usage_must_match_each_model_and_component(run_directory: Path, field: str) -> None:
    path = next((run_directory / "inspect").glob("*.eval"))
    log = read_eval_log(str(path), resolve_attachments="full")
    assert log.samples
    usage = log.samples[0].model_usage
    if field == "model":
        usage["wrong/model"] = usage.pop("mockllm/model")
    else:
        setattr(usage["mockllm/model"], field, (getattr(usage["mockllm/model"], field) or 0) + 1)
    write_eval_log(log, str(path))
    with pytest.raises(ValueError, match="Inspect usage"):
        asyncio.run(verify_run(run_directory))
