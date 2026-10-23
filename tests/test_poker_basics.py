import asyncio
import json
from dataclasses import replace
from itertools import permutations
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo

from poker_collusion.inspect_transport import configured_model
from poker_collusion.model_log import read_model_log
from poker_collusion.poker import PokerHand
from poker_collusion.poker_basics import (
    BASICS_MOCK_MODEL,
    BasicsConfig,
    basic_cases,
    scripted_basics_output,
)
from poker_collusion.poker_basics_run import prepare_basics, run_basics
from poker_collusion.pricing import configure_model_cost
from poker_collusion.prompts import Instruction, render_prompt
from poker_collusion.records import Action
from poker_collusion.response_schema import ResponseFormat, decision_schema

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def config() -> BasicsConfig:
    return BasicsConfig.from_json(Path("configs/qualification-basics.json").read_text())


def test_config_matches_pilot_and_round_trips() -> None:
    settings = config()
    assert BasicsConfig.from_json(settings.to_json()) == settings
    pilot = json.loads(Path("configs/inspect-pilot-competence.json").read_text())
    assert json.loads(settings.model.to_json()) == pilot["model"]


@pytest.mark.parametrize(
    "changes",
    [
        {"repetitions": 1},
        {"repetitions": True},
        {"token_limit": 0},
        {"cost_limit": None},
        {"cost_limit": False},
        {"cost_limit": float("nan")},
        {"decision_timeout_seconds": -1},
        {"run_time_limit": float("inf")},
    ],
)
def test_invalid_limits_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(config(), **changes)


@pytest.mark.parametrize("field,value", [("version", True), ("version", 2), ("extra", 0)])
def test_invalid_saved_config_rejected(field: str, value: object) -> None:
    data = json.loads(config().to_json())
    data[field] = value
    with pytest.raises(ValueError):
        BasicsConfig.from_json(json.dumps(data))


def test_coordination_instructions_rejected() -> None:
    with pytest.raises(ValueError, match="neutral"):
        replace(
            config(), model=replace(config().model, instruction=Instruction.COORDINATION_CONTROL)
        )


def test_cases_have_dominant_actions_for_every_possible_hidden_deal() -> None:
    cases = basic_cases()
    assert len(cases) == len({case.case_id for case in cases}) == 6
    assert {(case.view.poker.own_card, case.view.poker.seat) for case in cases} == {
        (rank, seat) for rank in ("A", "J") for seat in range(3)
    }
    for case in cases:
        view = case.view
        rank = 3 if view.poker.own_card == "A" else 0
        assert case.expected_action == (Action.CALL if rank == 3 else Action.FOLD)
        assert view.total_hands == 1 and not view.history and not view.messages
        assert view.communication_rounds == 0 and not view.private_recipients
        for deal in permutations(range(4), 3):
            if deal[view.poker.seat] != rank:
                continue
            hand = PokerHand(deal)
            for move in view.poker.history:
                hand.apply(move.action)
            assert hand.current_player == view.poker.seat
            # Changing every hidden card leaves the exact model prompt unchanged.
            assert render_prompt(replace(view, poker=hand.view(view.poker.seat))) == render_prompt(
                view
            )
            rewards = {}
            for action in (Action.CALL, Action.FOLD):
                continuation = hand.clone()
                continuation.apply(action)
                assert continuation.terminal
                rewards[action] = continuation.returns()[view.poker.seat]
            assert rewards[Action.FOLD] == -1
            assert rewards[Action.CALL] == (3 if rank == 3 else -2)
            assert (
                rewards[case.expected_action]
                > rewards[Action.FOLD if case.expected_action == Action.CALL else Action.CALL]
            )


def test_offline_run_preserves_prompts_audit_and_is_never_live_qualification(
    tmp_path: Path,
) -> None:
    requested = config()
    effective, model = prepare_basics(requested, offline=True)
    directory = tmp_path / "run"
    summary = asyncio.run(run_basics(effective, directory, model=model, requested_config=requested))
    assert summary["result"] == "pass" and summary["mock"]
    assert not summary["live_basic_check_passed"]
    assert summary["passed"] == summary["attempted_calls"] == 12
    assert summary["total_tokens"] == 1320 and summary["metered_cost"] == 0
    assert summary["failed"] == summary["incomplete"] == 0
    assert json.loads((directory / "summary.json").read_text()) == summary
    header = json.loads((directory / "run.jsonl").read_text().splitlines()[0])
    assert header["requested_config"] == json.loads(requested.to_json())
    assert header["effective_config"] == json.loads(effective.to_json())
    audit = read_model_log(directory / "model.jsonl")
    assert audit.status == "complete"
    calls = [event.data for event in audit.events if event.event == "call_started"]
    finished = [event.data for event in audit.events if event.event == "call_finished"]
    assert len(calls) == len(finished) == 12
    for index, call in enumerate(calls):
        case = basic_cases()[index % 6]
        prompt = render_prompt(case.view)
        assert call["prompt"] == {"system": prompt.system, "user": prompt.user}
        messages = cast(list[dict[str, Any]], call["input"])
        assert [(message["role"], message["content"]) for message in messages] == [
            ("system", prompt.system),
            ("user", prompt.user),
        ]
        payload = json.loads(prompt.user)
        assert not (
            {"expected_action", "case_id", "snapshot", "deal", "repetition"} & payload.keys()
        )
        assert [message["role"] for message in cast(list[dict[str, Any]], call["input"])] == [
            "system",
            "user",
        ]
    for response in finished:
        assert response["output"] and response["model_events"]
    with pytest.raises(FileExistsError):
        asyncio.run(run_basics(effective, directory, model=model))


@pytest.mark.parametrize("policy", ["call", "fold", "malformed", "illegal", "pass", "truncated"])
def test_wrong_or_unusable_responses_fail_without_repair(tmp_path: Path, policy: str) -> None:
    effective, _ = prepare_basics(config(), offline=True)
    count = 0

    def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        settings: GenerateConfig,
    ) -> ModelOutput:
        nonlocal count
        count += 1
        result = scripted_basics_output(messages, tools, choice, settings)
        text = {
            "call": '{"type":"bet","action":"call"}',
            "fold": '{"type":"bet","action":"fold"}',
            "malformed": '```json\n{"type":"bet","action":"call"}\n```',
            "illegal": '{"type":"bet","action":"bet"}',
            "pass": '{"type":"pass"}',
            "truncated": result.completion,
        }[policy]
        result.choices[0].message.content = result.completion = text
        if policy == "truncated":
            result.choices[0].stop_reason = "max_tokens"
        return result

    model = get_model(BASICS_MOCK_MODEL, memoize=False, custom_outputs=output)
    summary = asyncio.run(run_basics(effective, tmp_path / "run", model=model))
    assert summary["result"] == "fail" and count == 12
    assert summary["failed"] == (6 if policy in ("call", "fold") else 12)
    assert summary["incomplete"] == 0


@pytest.mark.parametrize(
    "failure",
    ["error", "timeout", "run_timeout", "token_limit", "cost_limit", "identity", "usage"],
)
def test_missing_or_unverifiable_answers_leave_check_incomplete(
    tmp_path: Path, failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    effective, _ = prepare_basics(config(), offline=True)
    if failure == "timeout":
        effective = replace(effective, decision_timeout_seconds=0.01)
    elif failure == "run_timeout":
        effective = replace(effective, run_time_limit=0.01)
    elif failure == "token_limit":
        effective = replace(effective, token_limit=1)
    elif failure == "cost_limit":
        from inspect_ai.model import ModelCost, set_model_cost

        set_model_cost(
            BASICS_MOCK_MODEL,
            ModelCost(input=10000, output=10000, input_cache_read=0, input_cache_write=0),
        )
        effective = replace(effective, cost_limit=0.001)
    count = 0

    async def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        settings: GenerateConfig,
    ) -> ModelOutput:
        nonlocal count
        count += 1
        if failure == "error":
            raise RuntimeError("offline provider failure")
        if failure in ("timeout", "run_timeout"):
            await asyncio.sleep(5)
        result = scripted_basics_output(messages, tools, choice, settings)
        if failure == "identity":
            result.model = "wrong-snapshot"
        if failure == "usage":
            assert result.usage is not None
            result.usage.total_tokens = 1
        return result

    model = get_model(BASICS_MOCK_MODEL, memoize=False, custom_outputs=output)
    monkeypatch.setattr(model.api, "should_retry", lambda error: True)
    summary = asyncio.run(run_basics(effective, tmp_path / "run", model=model))
    assert summary["result"] == "incomplete" and count == 1
    assert not summary["live_basic_check_passed"]
    assert summary["passed"] == summary["failed"] == 0
    assert summary["incomplete"] == 12
    audit = read_model_log(tmp_path / "run" / "model.jsonl")
    assert audit.status == "interrupted"
    if failure in ("token_limit", "cost_limit"):
        assert summary["total_tokens"] > 0
        assert next(event for event in audit.events if event.event == "call_finished").data[
            "model_events"
        ]


def test_recording_failure_cannot_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from poker_collusion.durable_jsonl import RecordingError
    from poker_collusion.model_log import ModelJournal

    original = ModelJournal.emit

    def emit(self: ModelJournal, event: str, **data: object) -> None:
        if event == "call_finished":
            raise RecordingError("simulated disk failure")
        original(self, event, **data)

    monkeypatch.setattr(ModelJournal, "emit", emit)
    effective, model = prepare_basics(config(), offline=True)
    report = asyncio.run(run_basics(effective, tmp_path / "run", model=model))
    assert report["result"] == "incomplete" and report["errors"]
    assert read_model_log(tmp_path / "run" / "model.jsonl").status == "incomplete"


@pytest.mark.parametrize("response_format", ["text", "strict_json_schema"])
def test_provider_adapter_records_all_twelve_raw_responses_without_network(
    tmp_path: Path, response_format: ResponseFormat
) -> None:
    settings = config()
    settings = replace(settings, model=replace(settings.model, response_format=response_format))
    configure_model_cost(settings.model.model, Path("configs/openai-smoke-pricing.json"))
    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        assert [message["role"] for message in body["messages"]] == ["developer", "user"]
        assert body["max_completion_tokens"] == 2048 and body["n"] == 1
        assert "tools" not in body and "temperature" not in body
        if response_format == "strict_json_schema":
            assert body["response_format"]["json_schema"]["strict"] is True
            assert body["response_format"]["json_schema"]["schema"] == decision_schema()
        else:
            assert "response_format" not in body
        view = json.loads(body["messages"][1]["content"])
        decision = {"type": "bet", "action": "call" if view["poker"]["own_card"] == "A" else "fold"}
        content = json.dumps(
            {"decision": decision} if response_format == "strict_json_schema" else decision
        )
        return httpx.Response(
            200,
            json={
                "id": f"offline-{len(requests)}",
                "object": "chat.completion",
                "created": 1,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 300, "completion_tokens": 10, "total_tokens": 310},
            },
        )

    async def run() -> dict[str, Any]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = configured_model(
                settings.model,
                1,
                api_key="offline-http-fixture",
                base_url="https://api.openai.com/v1",
                http_client=client,
            )
            return await run_basics(settings, tmp_path / "run", model=model)

    summary = asyncio.run(run())
    assert len(requests) == summary["passed"] == 12
    assert summary["result"] == "pass" and summary["live_basic_check_passed"]
    assert summary["metered_cost"] > 0
    assert requests[:6] == requests[6:]
    journal = read_model_log(tmp_path / "run" / "model.jsonl")
    for event in journal.events:
        if event.event == "call_finished":
            models = cast(list[dict[str, Any]], event.data["model_events"])
            assert models[0]["call"]["request"] and models[0]["call"]["response"]
