import asyncio
import json
from dataclasses import replace
from typing import Any

import pytest

from poker_collusion.model_adapter import ModelConfig, parse_response
from poker_collusion.poker import generate_schedule
from poker_collusion.prompts import Instruction, render_prompt
from poker_collusion.records import (
    Action,
    BetDecision,
    Channel,
    Decision,
    DecisionParseError,
    MessageDecision,
    PassDecision,
    Phase,
    PlayerView,
    SessionConfig,
)
from poker_collusion.session import passive_decider, run_session


@pytest.fixture
def betting_view() -> PlayerView:
    seen: list[PlayerView] = []

    async def decide(view: PlayerView) -> Decision:
        seen.append(view)
        return await passive_decider(view)

    asyncio.run(run_session(SessionConfig(hands=1), generate_schedule(0, 1), decide))
    return seen[0]


@pytest.mark.parametrize("instruction", list(Instruction))
@pytest.mark.parametrize("temperature", [None, 0, 0.7, 2.0])
def test_config_round_trip_and_hash(instruction: Instruction, temperature: float | None) -> None:
    config = ModelConfig("mock/offline", instruction, max_tokens=123, temperature=temperature)
    restored = ModelConfig.from_json(config.to_json())
    assert restored == config
    assert restored.sha256 == config.sha256
    assert replace(config, max_tokens=124).sha256 != config.sha256
    assert replace(config, model="mock/another").sha256 != config.sha256


@pytest.mark.parametrize(
    "updates",
    [
        {"model": ""},
        {"model": " model"},
        {"model": "model\n"},
        {"model": None},
        {"instruction": "neutral"},
        {"instruction": "fair_play"},
        {"max_tokens": 0},
        {"max_tokens": -1},
        {"max_tokens": True},
        {"max_tokens": 10.5},
        {"temperature": True},
        {"temperature": "0.5"},
        {"temperature": -0.1},
        {"temperature": float("nan")},
        {"temperature": float("inf")},
        {"temperature": 10**400},
        {"cache": True},
        {"cache": 0},
        {"max_retries": 1},
        {"max_retries": False},
    ],
)
def test_invalid_config_is_rejected(updates: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        ModelConfig(**{"model": "mock/offline", **updates})


@pytest.mark.parametrize(
    "change",
    ["version", "boolean_version", "kind", "unknown", "missing", "instruction", "settings"],
)
def test_saved_config_rejects_incompatible_records(change: str) -> None:
    data = json.loads(ModelConfig("mock/offline").to_json())
    if change == "version":
        data["version"] = 2
    elif change == "boolean_version":
        data["version"] = True
    elif change == "kind":
        data["kind"] = "session_config"
    elif change == "unknown":
        data["settings"]["api_key"] = "must-not-be-accepted"
    elif change == "missing":
        del data["settings"]["max_tokens"]
    elif change == "instruction":
        data["settings"]["instruction"] = "fair_play"
    else:
        data["settings"] = []
    with pytest.raises(ValueError):
        ModelConfig.from_json(json.dumps(data))


@pytest.mark.parametrize("payload", ["null", "[]", "{}", '{"version":1,"version":1}', "NaN"])
def test_config_requires_strict_json(payload: str) -> None:
    with pytest.raises(ValueError):
        ModelConfig.from_json(payload)


@pytest.mark.parametrize("action", list(Action))
def test_named_actions_parse_without_reinterpreting_legality(action: Action) -> None:
    assert parse_response(json.dumps({"type": "bet", "action": action})) == BetDecision(action)


def test_pass_and_message_parsing_preserve_exact_text() -> None:
    assert parse_response(' \n {"type": "pass"} \t') == PassDecision()
    text = '  🂡 e\u0301\n"quoted" </system> \\  '
    for recipient in (None, "B"):
        raw = json.dumps({"type": "message", "text": text, "recipient": recipient})
        assert parse_response(raw) == MessageDecision(text, recipient)


@pytest.mark.parametrize(
    "response",
    [
        "",
        "I refuse to play",
        '```json\n{"type":"pass"}\n```',
        'Here is my decision: {"type":"pass"}',
        '{"type":"pass"} trailing',
        '{"type":"pass"}{"type":"pass"}',
        "null",
        "[]",
        '"pass"',
        "{}",
        '{"type":"pass","text":"extra"}',
        '{"type":"Pass"}',
        '{"type":"bet","action":"raise"}',
        '{"type":"bet","action":"CHECK"}',
        '{"type":"bet","action":0}',
        '{"type":"bet","action":true}',
        '{"type":"bet","action":[]}',
        '{"type":"bet"}',
        '{"type":"bet","action":"check","reason":"extra"}',
        '{"type":"message","text":"hi"}',
        '{"type":"message","text":42,"recipient":null}',
        '{"type":"message","text":"hi","recipient":["B","C"]}',
        '{"type":"message","text":"hi","recipient":false}',
        '{"type":"pass","type":"bet","action":"check"}',
        '{"type":"bet","action":"check","action":"bet"}',
        '{"type":"pass","extra":{"key":1,"key":2}}',
        '{"type":"bet","action":NaN}',
        '{"type":"bet","action":Infinity}',
        '{"type":"bet","action":1e999}',
        "[" * 1100 + "0" + "]" * 1100,
    ],
)
def test_malformed_text_is_rejected_and_retained(response: str) -> None:
    with pytest.raises(DecisionParseError) as caught:
        parse_response(response)
    assert caught.value.response == response


def test_prompt_is_deterministic_and_hashes_exact_contents(betting_view: PlayerView) -> None:
    first = render_prompt(betting_view)
    assert first == render_prompt(betting_view)
    assert first.sha256 == render_prompt(betting_view).sha256
    assert json.loads(first.user)["poker"]["own_card"] == betting_view.poker.own_card
    changed = replace(betting_view, poker=replace(betting_view.poker, own_card="different"))
    assert render_prompt(changed).sha256 != first.sha256
    assert replace(first, system=first.system + " ").sha256 != first.sha256
    assert '["check","bet"]' in first.system
    facing_bet = replace(
        betting_view, poker=replace(betting_view.poker, legal_actions=(Action.CALL, Action.FOLD))
    )
    assert '["call","fold"]' in render_prompt(facing_bet).system


def test_coordination_instructions_are_separate_from_neutral(betting_view: PlayerView) -> None:
    neutral = render_prompt(betting_view)
    control = render_prompt(betting_view, Instruction.COORDINATION_CONTROL)
    assert neutral.user == control.user
    assert neutral.sha256 != control.sha256
    assert "maximize your own cumulative net chip winnings" in neutral.system
    for word in ("partner", "coordinate", "collusion", "coalition", "fair-play"):
        assert word not in neutral.system
    assert "actively seek an agreement with one other player" in control.system
    assert "rewards are not pooled" in control.system


@pytest.mark.parametrize("channel", [Channel.PUBLIC, Channel.PRIVATE])
@pytest.mark.parametrize("budget", [0, 7])
def test_prompt_describes_only_available_message_options(channel: Channel, budget: int) -> None:
    seen: list[PlayerView] = []

    async def decide(view: PlayerView) -> Decision:
        seen.append(view)
        return await passive_decider(view)

    config = SessionConfig(hands=1, channel=channel, message_budget_chars=budget)
    asyncio.run(run_session(config, generate_schedule(0, 1), decide))
    prompt = render_prompt(seen[0])
    assert '{"type":"pass"}' in prompt.system
    if budget == 0:
        assert "Sending a message is unavailable" in prompt.system
        assert '{"type":"message"' not in prompt.system
    elif channel == Channel.PUBLIC:
        assert '"recipient":null' in prompt.system
        assert "delivered to all three players" in prompt.system
    else:
        assert '["B","C"]' in prompt.system
        assert "only to you and that recipient" in prompt.system
    assert json.loads(prompt.user)["max_message_chars"] == budget


def test_terminal_view_cannot_request_a_model_decision(betting_view: PlayerView) -> None:
    with pytest.raises(ValueError, match="Only communication and betting"):
        render_prompt(replace(betting_view, phase=Phase.COMPLETE))
