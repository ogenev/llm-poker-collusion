import asyncio
import json
from dataclasses import replace
from itertools import permutations
from pathlib import Path
from typing import Any

import httpx
import pytest
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo

from poker_collusion.inspect_transport import configured_model
from poker_collusion.message_context import CONTEXTS, MessageContextConfig, context_cases
from poker_collusion.message_context_run import prepare_context, run_context
from poker_collusion.message_context_verification import verify_context
from poker_collusion.model_log import read_model_log
from poker_collusion.poker import PokerHand
from poker_collusion.poker_basics import BASICS_MOCK_MODEL, scripted_basics_output
from poker_collusion.pricing import configure_model_cost
from poker_collusion.prompts import render_prompt
from poker_collusion.records import CARD_LABELS, PLAYER_IDS, Action
from poker_collusion.serialization import canonical

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def config() -> MessageContextConfig:
    return MessageContextConfig.from_json(
        Path("configs/qualification-message-context-gpt-6-luna-medium-strict.json").read_text()
    )


def test_config_and_cycle2_preserve_settings() -> None:
    settings = config()
    assert MessageContextConfig.from_json(settings.to_json()) == settings
    old = json.loads(
        Path("configs/inspect-pilot-neutral-gpt-6-luna-medium-strict.json").read_text()
    )
    new = json.loads(
        Path("configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle2.json").read_text()
    )
    assert new.pop("seeds") == [400, 401, 402]
    old.pop("seeds")
    assert old == new
    assert json.loads(settings.model.to_json()) == new["model"]
    with pytest.raises(ValueError):
        replace(settings, repetitions=3)
    with pytest.raises(ValueError):
        replace(settings, model=replace(settings.model, reasoning_effort=None))
    with pytest.raises(ValueError):
        replace(settings, model=replace(settings.model, response_format="text"))


def test_fixtures_are_matched_and_final_actions_are_dominant() -> None:
    cases = context_cases()
    assert len(cases) == len({case.case_id for case in cases}) == 30
    assert tuple(case.context for case in cases[:5]) == CONTEXTS
    for start in range(0, 30, 5):
        baseline = cases[start].view
        assert not baseline.messages and not baseline.history and baseline.total_hands == 1
        for case in cases[start : start + 5]:
            assert replace(case.view, messages=()) == baseline
            snapshot = json.loads(case.snapshot)
            seat = case.view.poker.seat
            for message in case.view.messages:
                sender_seat = PLAYER_IDS.index(message.sender)
                actual = CARD_LABELS[snapshot["deal"][sender_seat]]
                assert (message.text == f"I have {actual}.") == case.context.startswith("truthful")
                assert message.recipient == (
                    case.view.player_id if case.context.endswith("private") else None
                )
            for deal in permutations(range(4), 3):
                if deal[seat] != snapshot["deal"][seat]:
                    continue
                hand = PokerHand((deal[0], deal[1], deal[2]))
                for action in snapshot["actions"]:
                    hand.apply(Action(action))
                assert hand.view(seat) == case.view.poker
                values = {}
                for action in hand.legal_actions:
                    settled = hand.clone()
                    settled.apply(action)
                    assert settled.terminal
                    values[action] = settled.returns()[seat]
                assert max(values, key=lambda action: values[action]) == case.expected_action
            prompt = render_prompt(case.view, response_format="strict_json_schema")
            assert json.loads(prompt.user) == json.loads(canonical(case.view))
            assert all(
                label not in prompt.user
                for label in ("expected_action", "case_id", "snapshot", "deal", "context")
            )


def test_offline_screen_is_verified_but_never_qualifies_luna(tmp_path: Path) -> None:
    effective, model = prepare_context(config(), offline=True)
    path = tmp_path / "screen"
    summary = asyncio.run(run_context(effective, path, model=model, requested_config=config()))
    assert summary["passed"] == summary["attempted_calls"] == 60
    assert summary["total_tokens"] == 6600 and summary["metered_cost"] == 0
    assert summary["mock"] and not summary["live_message_context_check_passed"]
    verified = asyncio.run(verify_context(path))
    assert verified["passed"] and not verified["live_message_context_check_passed"]
    with pytest.raises(FileExistsError):
        asyncio.run(run_context(effective, path, model=model))
    # Fabricated summary success cannot override saved evidence.
    summary["total_tokens"] += 1
    (path / "summary.json").write_text(canonical(summary) + "\n")
    with pytest.raises(ValueError, match="reconcile"):
        asyncio.run(verify_context(path))


@pytest.mark.parametrize("failure", ["wrong", "invalid", "usage", "identity", "error", "limit"])
def test_failed_screen_never_passes_or_retries(tmp_path: Path, failure: str) -> None:
    effective, _ = prepare_context(config(), offline=True)
    if failure == "limit":
        effective = replace(effective, token_limit=1)
    calls = 0

    def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        settings: GenerateConfig,
    ) -> ModelOutput:
        nonlocal calls
        calls += 1
        if failure == "error":
            raise RuntimeError("offline failure")
        result = scripted_basics_output(messages, tools, choice, settings)
        if failure in ("wrong", "invalid"):
            content = (
                '{"decision":{"type":"bet","action":"call"}}' if failure == "wrong" else "invalid"
            )
            result.choices[0].message.content = result.completion = content
        elif failure == "usage":
            result.usage = None
        elif failure == "identity":
            result.model = "wrong-model"
        return result

    model = get_model(BASICS_MOCK_MODEL, memoize=False, custom_outputs=output)
    summary = asyncio.run(run_context(effective, tmp_path / "screen", model=model))
    assert not summary["live_message_context_check_passed"]
    assert summary["result"] == ("fail" if failure in ("wrong", "invalid") else "incomplete")
    assert calls == (60 if failure in ("wrong", "invalid") else 1)
    if failure == "wrong":
        assert summary["passed"] == summary["failed"] == 30
        assert not asyncio.run(verify_context(tmp_path / "screen"))["passed"]
    if failure == "limit":
        assert summary["total_tokens"] == 110
        assert read_model_log(tmp_path / "screen" / "model.jsonl").status == "interrupted"


def test_all_sixty_strict_medium_provider_payloads_and_verifier(tmp_path: Path) -> None:
    settings = config()
    configure_model_cost(
        settings.model.model, Path("configs/openai-gpt-6-luna-cycle2-pricing.json")
    )
    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        assert body["reasoning_effort"] == "medium"
        assert body["max_completion_tokens"] == 4096 and body["n"] == 1
        assert "temperature" not in body and "tools" not in body
        assert body["response_format"]["json_schema"]["strict"] is True
        view = json.loads(body["messages"][1]["content"])
        content = canonical(
            {
                "decision": {
                    "type": "bet",
                    "action": "call" if view["poker"]["own_card"] == "A" else "fold",
                }
            }
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
            return await run_context(settings, tmp_path / "screen", model=model)

    summary = asyncio.run(run())
    assert summary["passed"] == len(requests) == 60 and requests[:30] == requests[30:]
    verification = asyncio.run(verify_context(tmp_path / "screen"))
    assert verification["passed"] and verification["calls"] == 60
    # This is an intercepted HTTP integration test, never actual qualification.
    journal_path = tmp_path / "screen" / "model.jsonl"
    rows = [json.loads(line) for line in journal_path.read_text().splitlines()]
    rows[2]["data"]["model_events"][0]["call"]["request"]["reasoning_effort"] = "low"
    journal_path.write_text("\n".join(canonical(row) for row in rows) + "\n")
    with pytest.raises(ValueError, match="Inspect event differs"):
        asyncio.run(verify_context(tmp_path / "screen"))
