import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.inspect_transport import generation_config
from poker_collusion.model_adapter import ModelConfig, ModelRequest, model_decider, parse_response
from poker_collusion.model_log import read_model_log
from poker_collusion.offline_model import offline_model
from poker_collusion.poker import generate_schedule
from poker_collusion.poker_basics import BasicsConfig, basic_cases
from poker_collusion.poker_basics_run import prepare_basics, run_basics
from poker_collusion.prompts import render_prompt
from poker_collusion.records import (
    Action,
    BetDecision,
    Channel,
    DecisionParseError,
    FailureKind,
    MessageDecision,
    PassDecision,
    Phase,
    SessionConfig,
)
from poker_collusion.response_schema import ResponseFormat, decision_schema
from poker_collusion.serialization import canonical, digest
from poker_collusion.session import run_session
from poker_collusion.verification import verify_run


@pytest.mark.parametrize(
    "path",
    [
        "configs/inspect-live-smoke.json",
        "configs/qualification-basics-gpt-6.1-sol.json",
        "configs/qualification-basics-gpt-6.1-sol-medium.json",
        "configs/inspect-pilot-competence-gpt-6.1-sol-medium.json",
    ],
)
def test_legacy_model_records_keep_exact_bytes_and_hashes(path: str) -> None:
    saved = json.loads(Path(path).read_text())["model"]
    model = ModelConfig.from_json(canonical(saved))
    assert model.response_format == "text"
    assert model.to_json() == canonical(saved)
    assert model.sha256 == digest(saved)
    assert generation_config(model, 1).response_schema is None


@pytest.mark.parametrize("explicit_reasoning", [False, True])
def test_strict_format_has_distinct_versioned_provenance(explicit_reasoning: bool) -> None:
    legacy = ModelConfig(
        "openai/gpt-6.1-sol", reasoning_effort="medium" if explicit_reasoning else None
    )
    strict = replace(legacy, response_format="strict_json_schema")
    saved = json.loads(strict.to_json())
    assert saved["version"] == 3
    assert saved["settings"]["response_format"] == "strict_json_schema"
    assert saved["settings"]["reasoning_effort"] == legacy.reasoning_effort
    assert ModelConfig.from_json(strict.to_json()) == strict
    assert strict.sha256 != legacy.sha256
    experiment = ExperimentConfig(strict)
    assert ExperimentConfig.from_json(experiment.to_json()) == experiment
    assert json.loads(experiment.to_json())["version"] == 1


@pytest.mark.parametrize("value", [None, True, 1, "json_object", "strict", "", [], {}])
def test_unsupported_response_format_rejected(value: object) -> None:
    with pytest.raises(ValueError, match="response format"):
        ModelConfig("model", response_format=cast(ResponseFormat, value))


@pytest.mark.parametrize("change", ["default", "missing", "reasoning", "v1", "v2", "future"])
def test_strict_record_requires_consistent_version_and_fields(change: str) -> None:
    saved = json.loads(ModelConfig("model", response_format="strict_json_schema").to_json())
    if change == "default":
        saved["settings"]["response_format"] = "text"
    elif change == "missing":
        del saved["settings"]["response_format"]
    elif change == "reasoning":
        del saved["settings"]["reasoning_effort"]
    else:
        saved["version"] = {"v1": 1, "v2": 2, "future": 4}[change]
    with pytest.raises(ValueError):
        ModelConfig.from_json(json.dumps(saved))


@pytest.mark.parametrize(
    "decision,expected",
    [
        ({"type": "pass"}, PassDecision()),
        ({"type": "bet", "action": "call"}, BetDecision(Action.CALL)),
        (
            {"type": "message", "text": "  🂡 e\u0301\n  ", "recipient": None},
            MessageDecision("  🂡 e\u0301\n  ", None),
        ),
        ({"type": "message", "text": "hello", "recipient": "B"}, MessageDecision("hello", "B")),
    ],
)
def test_structured_schema_and_parser_accept_exact_decisions(
    decision: dict[str, Any], expected: object
) -> None:
    wrapped = {"decision": decision}
    Draft202012Validator.check_schema(decision_schema())
    Draft202012Validator(decision_schema()).validate(wrapped)
    assert parse_response(json.dumps(wrapped), response_format="strict_json_schema") == expected
    with pytest.raises(DecisionParseError):
        parse_response(json.dumps(wrapped))
    with pytest.raises(DecisionParseError):
        parse_response(json.dumps(decision), response_format="strict_json_schema")


@pytest.mark.parametrize(
    "payload",
    [
        {"decision": {"type": "message", "text": "hello"}},
        {"decision": {"type": "pass", "text": None}},
        {"decision": {"type": "bet", "action": "raise"}},
        {"decision": {"type": "message", "text": 1, "recipient": None}},
        {"decision": {"type": "message", "text": "hello", "recipient": ["B", "C"]}},
        {"decision": {"type": "pass"}, "reason": "extra"},
        {"decision": None},
        {"decision": [{"type": "pass"}]},
        {"decision": {"decision": {"type": "pass"}}},
        {"type": "pass"},
    ],
)
def test_missing_recipient_and_other_shape_errors_are_rejected(payload: object) -> None:
    assert not Draft202012Validator(decision_schema()).is_valid(payload)
    raw = json.dumps(payload)
    with pytest.raises(DecisionParseError) as caught:
        parse_response(raw, response_format="strict_json_schema")
    assert caught.value.response == raw


@pytest.mark.parametrize(
    "raw",
    [
        '{"decision":{"type":"pass"},"decision":{"type":"pass"}}',
        '{"decision":{"type":"pass","type":"pass"}}',
        '{"decision":{"type":"message","text":"x","recipient":NaN}}',
        '```json\n{"decision":{"type":"pass"}}\n```',
        "I refuse to play",
    ],
)
def test_strict_decoder_preserves_original_malformed_text(raw: str) -> None:
    with pytest.raises(DecisionParseError) as caught:
        parse_response(raw, response_format="strict_json_schema")
    assert caught.value.response == raw


def test_format_changes_only_authored_response_examples_and_configured_schema() -> None:
    view = basic_cases()[0].view
    legacy = render_prompt(view)
    assert legacy.sha256 == "28b6a702c224c21bfc0279f406b2976badbaeab8ae6ff080ef7f4b9618aa8e7c"
    strict = render_prompt(view, response_format="strict_json_schema")
    assert strict.user == legacy.user
    assert strict.system == legacy.system.replace(
        '{"type":"bet","action":ACTION}', '{"decision":{"type":"bet","action":ACTION}}'
    )
    config = generation_config(ModelConfig("model", response_format="strict_json_schema"), 1)
    assert config.response_schema is not None and config.response_schema.strict is True
    assert config.response_schema.json_schema.model_dump(exclude_none=True) == decision_schema()


@pytest.mark.usefixtures("inspect_runtime")
def test_strict_mock_sessions_complete_verify_and_replay(tmp_path: Path) -> None:
    model = ModelConfig("mockllm/model", response_format="strict_json_schema")
    config = ExperimentConfig(model, session=SessionConfig(hands=1))
    asyncio.run(run_experiment(config, tmp_path / "run", model=offline_model()))
    report = asyncio.run(verify_run(tmp_path / "run"))
    assert report["passed"] and len(report["sessions"]) == 3
    assert all(session["completed_hands"] == 1 for session in report["sessions"])


@pytest.mark.usefixtures("inspect_runtime")
def test_strict_basics_roundtrip_offline_and_model_journal(tmp_path: Path) -> None:
    original = BasicsConfig.from_json(Path("configs/qualification-basics.json").read_text())
    requested = replace(
        original, model=replace(original.model, response_format="strict_json_schema")
    )
    assert BasicsConfig.from_json(requested.to_json()) == requested
    effective, model = prepare_basics(requested, offline=True)
    directory = tmp_path / "run"
    result = asyncio.run(run_basics(effective, directory, model=model, requested_config=requested))
    assert result["result"] == "pass" and result["passed"] == result["attempted_calls"] == 12
    assert result["mock"] and not result["live_basic_check_passed"]
    audit = read_model_log(directory / "model.jsonl")
    for event in audit.events:
        if event.event == "call_started":
            generation = cast(dict[str, Any], event.data["generation"])
            assert generation["response_schema"]["strict"] is True


@pytest.mark.parametrize(
    "channel,decision",
    [
        (Channel.PUBLIC, {"type": "bet", "action": "check"}),
        (Channel.PRIVATE, {"type": "message", "text": "hi", "recipient": "A"}),
        (Channel.PUBLIC, {"type": "message", "text": "toolong", "recipient": None}),
        (Channel.PUBLIC, {"type": "message", "text": "   ", "recipient": None}),
    ],
)
def test_schema_does_not_replace_game_legality(channel: Channel, decision: dict[str, Any]) -> None:
    raw = json.dumps({"decision": decision})
    assert Draft202012Validator(decision_schema()).is_valid(json.loads(raw))

    async def generate(request: ModelRequest) -> str:
        return raw

    config = ModelConfig("mock/offline", response_format="strict_json_schema")
    session = SessionConfig(hands=1, channel=channel, max_message_chars=3)
    state = asyncio.run(
        run_session(session, generate_schedule(0, 1), model_decider(config, generate))
    )
    assert state.phase == Phase.FAILED and state.failure is not None
    assert state.failure.kind == FailureKind.INVALID_DECISION
