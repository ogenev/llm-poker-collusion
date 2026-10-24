import asyncio
import json
import runpy
import sys
from dataclasses import replace
from itertools import permutations
from pathlib import Path
from typing import Any

import httpx
import pytest

from poker_collusion.history_context import HistoryContextConfig, history_cases, history_sources
from poker_collusion.inspect_transport import configured_model
from poker_collusion.message_context import context_cases
from poker_collusion.message_context_run import prepare_context, run_context
from poker_collusion.message_context_verification import verify_context
from poker_collusion.poker import PokerHand
from poker_collusion.pricing import configure_model_cost
from poker_collusion.prompts import render_prompt
from poker_collusion.records import Action
from poker_collusion.serialization import canonical, digest

pytestmark = pytest.mark.usefixtures("inspect_runtime")
CONFIG = Path("configs/qualification-history-context-gpt-6-luna-medium-strict.json")
PRICES = Path("configs/openai-gpt-6-luna-cycle3-pricing.json")


def settings() -> HistoryContextConfig:
    value = HistoryContextConfig.from_json(CONFIG.read_text())
    assert isinstance(value, HistoryContextConfig)
    return value


def test_original_replay_and_paired_history_ablations() -> None:
    cases, sources = history_cases(), history_sources()
    assert len(cases) == len({case.case_id for case in cases}) == 13
    error = next(row for row in sources if row["source_id"] == "seed301-public-J")
    assert error["request_id"] == 82 and error["view_sequence"] == 379
    assert cases[0].view.total_hands == 12 and cases[0].view.hand_index == 8
    assert json.loads(canonical(cases[0].view)) == error["view"]
    assert (
        json.loads(canonical(render_prompt(cases[0].view, response_format="strict_json_schema")))
        == error["original_prompt"]
    )
    for index, source in enumerate(sources):
        full, removed = cases[1 + 2 * index : 3 + 2 * index]
        assert len(full.view.history) == 6 and not removed.view.history
        assert replace(full.view, history=()) == removed.view
        assert full.view.total_hands == full.view.hand_index + 1
        original = dict(source["view"], total_hands=full.view.total_hands)
        assert json.loads(canonical(full.view)) == original
        for case in (full, removed):
            snapshot = json.loads(case.snapshot)
            seat = case.view.poker.seat
            for deal in permutations(range(4), 3):
                if deal[seat] != snapshot["deal"][seat]:
                    continue
                hand = PokerHand((deal[0], deal[1], deal[2]))
                for action in snapshot["actions"]:
                    hand.apply(Action(action))
                assert hand.view(seat) == case.view.poker
                returns = {}
                for action in hand.legal_actions:
                    settled = hand.clone()
                    settled.apply(action)
                    assert settled.terminal
                    returns[action] = settled.returns()[seat]
                assert max(returns, key=lambda action: returns[action]) == case.expected_action
            prompt = render_prompt(case.view, response_format="strict_json_schema")
            assert all(
                key not in json.loads(prompt.user)
                for key in ("snapshot", "expected_action", "source_id", "original_prompt")
            )


def test_legacy_fixtures_remain_identical_and_new_config_roundtrips() -> None:
    assert (
        digest(context_cases())
        == "424d0af3e4a97e7c8b12aae47657e93e58656c68d3902151a086d1452e982dd7"
    )
    config = settings()
    assert HistoryContextConfig.from_json(config.to_json()) == config
    with pytest.raises(ValueError):
        replace(config, model=replace(config.model, reasoning_effort="low"))


def test_history_mock_is_verified_without_live_qualification(tmp_path: Path) -> None:
    requested = settings()
    effective, model = prepare_context(requested, offline=True)
    output = tmp_path / "history"
    summary = asyncio.run(run_context(effective, output, model=model, requested_config=requested))
    assert summary["passed"] == summary["planned_calls"] == 26
    assert summary["mock"] and not summary["live_history_context_check_passed"]
    checked = asyncio.run(verify_context(output, config_type=HistoryContextConfig))
    assert checked["passed"] and not checked["live_history_context_check_passed"]
    with pytest.raises(ValueError, match="manifest"):
        asyncio.run(verify_context(output))
    manifest = output / "run.jsonl"
    rows = [json.loads(line) for line in manifest.read_text().splitlines()]
    rows[0]["cases"][1]["view"]["history"] = []
    manifest.write_text("\n".join(canonical(row) for row in rows) + "\n")
    with pytest.raises(ValueError, match="Frozen fixtures differ"):
        asyncio.run(verify_context(output, config_type=HistoryContextConfig))


@pytest.mark.parametrize("wrong", [False, True])
def test_history_raw_payloads_and_fail_gate(tmp_path: Path, wrong: bool) -> None:
    config = settings()
    configure_model_cost(config.model.model, PRICES)
    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        assert body["reasoning_effort"] == "medium" and body["max_completion_tokens"] == 4096
        assert "temperature" not in body and not body.get("tools")
        assert body["response_format"]["json_schema"]["strict"] is True
        view = json.loads(body["messages"][1]["content"])
        action = "call" if wrong or view["poker"]["own_card"] == "A" else "fold"
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
                        "message": {
                            "role": "assistant",
                            "content": canonical({"decision": {"type": "bet", "action": action}}),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 300, "completion_tokens": 10, "total_tokens": 310},
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = configured_model(
                config.model, 1, api_key="offline-http-fixture", http_client=client
            )
            await run_context(config, tmp_path / "history", model=model)

    asyncio.run(run())
    assert len(requests) == 26 and requests[:13] == requests[13:]
    report = asyncio.run(verify_context(tmp_path / "history", config_type=HistoryContextConfig))
    assert report["passed"] is not wrong
    assert report["correct"] == (12 if wrong else 26)
    # An intercepted HTTP response is test evidence, never actual Luna qualification.


def test_history_preflight_makes_no_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "offline-preflight-fixture")
    unused = tmp_path / "unused"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/check_history_context.py",
            str(CONFIG),
            "--preflight",
            "--model-cost-config",
            str(PRICES),
            "--output",
            str(unused),
        ],
    )
    runpy.run_path(sys.argv[0], run_name="__main__")
    result = json.loads(capsys.readouterr().out)
    assert result["api_calls"] == 0 and result["plan"]["maximum_decision_calls"] == 26
    assert not unused.exists()
