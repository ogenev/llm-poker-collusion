import asyncio
import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from inspect_ai.event import ModelEvent
from inspect_ai.log import read_eval_log, write_eval_log

from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.inspect_transport import configured_model, generation_config
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.model_log import read_model_log
from poker_collusion.pricing import configure_model_cost
from poker_collusion.records import Channel
from poker_collusion.response_schema import SCHEMA_NAME, ResponseFormat, decision_schema
from poker_collusion.serialization import canonical
from poker_collusion.verification import verify_run

pytestmark = pytest.mark.usefixtures("inspect_runtime")


@pytest.mark.parametrize(
    "outcome",
    [
        "valid",
        "cached",
        "malformed",
        "missing_recipient",
        "refusal",
        "truncated",
        "rate_limit",
        "wrong_model",
        "usage",
        "schema_mismatch",
        "schema_strict_false",
        "raw_format_mismatch",
        "raw_schema_weakening",
    ],
)
@pytest.mark.parametrize("explicit_reasoning", [False, True])
@pytest.mark.parametrize("response_format", ["text", "strict_json_schema"])
def test_openai_sdk_transport_and_audits_without_network(
    tmp_path: Path, outcome: str, explicit_reasoning: bool, response_format: ResponseFormat
) -> None:
    config = ExperimentConfig.from_json(Path("configs/inspect-live-smoke.json").read_text())
    pricing = "configs/openai-smoke-pricing.json"
    if explicit_reasoning:
        config = replace(
            config,
            model=replace(
                config.model, model="openai/gpt-6.1-sol", reasoning_effort="medium", max_tokens=4096
            ),
            cost_limit=1.0,
        )
        pricing = "configs/openai-gpt-6.1-sol-pricing.json"
    config = replace(config, model=replace(config.model, response_format=response_format))
    configure_model_cost(config.model.model, Path(pricing))
    provider_model = config.model.model.partition("/")[2]
    successful = outcome in ("valid", "cached")
    if not successful:
        channel = Channel.PUBLIC if outcome == "missing_recipient" else Channel.NONE
        config = replace(config, session=replace(config.session, hands=1), channels=(channel,))
    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openai.com" and request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        requests.append(body)
        assert body["model"] == provider_model
        assert body["max_completion_tokens"] == config.model.max_tokens and body["n"] == 1
        if explicit_reasoning:
            assert body["reasoning_effort"] == "medium"
        else:
            assert "reasoning_effort" not in body
        assert "max_tokens" not in body
        assert "temperature" not in body and "tools" not in body
        if response_format == "strict_json_schema":
            assert body["response_format"] == {
                "type": "json_schema",
                "json_schema": {
                    "name": SCHEMA_NAME,
                    "schema": decision_schema(),
                    "description": "A poker decision.",
                    "strict": True,
                },
            }
        else:
            assert "response_format" not in body
        assert [m["role"] for m in body["messages"]] == ["developer", "user"]
        view = json.loads(body["messages"][1]["content"])
        if outcome == "rate_limit":
            return httpx.Response(
                429, json={"error": {"message": "fake rate limit", "type": "rate_limit_error"}}
            )
        if view["phase"] == "communication":
            # Exercise real SDK message delivery, not just passing every round.
            decision = {
                "type": "message",
                "text": "offline HTTP fixture",
                "recipient": None
                if view["public_message_allowed"]
                else view["private_recipients"][0],
            }
        else:
            decision = {"type": "bet", "action": view["poker"]["legal_actions"][0]}
        if outcome == "missing_recipient":
            del decision["recipient"]
        content = json.dumps(
            {"decision": decision} if response_format == "strict_json_schema" else decision
        )
        if outcome == "malformed":
            content = "not JSON"
        # Synthetic sizing from the actual English/JSON payload, at three UTF-8
        # bytes per token plus chat framing. This is not provider-measured usage,
        # but exercises realistic context growth without downloading a tokenizer.
        input_tokens = 12 + sum(
            math.ceil(len(message["content"].encode("utf-8")) / 3) for message in body["messages"]
        )
        reasoning_tokens = 64 if outcome == "cached" else 0
        output_tokens = math.ceil(len(content.encode("utf-8")) / 3) + reasoning_tokens
        return httpx.Response(
            200,
            headers={"x-request-id": f"fake-http-{len(requests)}"},
            json={
                "id": f"fake-completion-{len(requests)}",
                "object": "chat.completion",
                "created": 1,
                "model": "different-model" if outcome == "wrong_model" else body["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": {"refusal": "content_filter", "truncated": "length"}.get(
                            outcome, "stop"
                        ),
                    }
                ],
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": 1 if outcome == "usage" else input_tokens + output_tokens,
                    "prompt_tokens_details": {"cached_tokens": 128 if outcome == "cached" else 0},
                    "completion_tokens_details": {"reasoning_tokens": reasoning_tokens},
                },
            },
        )

    async def run() -> dict[str, Any]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = configured_model(
                config.model,
                config.max_connections,
                api_key="offline-http-fixture",
                base_url="https://api.openai.com/v1",
                http_client=client,
            )
            await run_experiment(config, tmp_path / "run", model=model)
        if outcome.startswith(("schema_", "raw_")):
            damage_response_schema(tmp_path / "run", outcome, response_format)
        return await verify_run(tmp_path / "run")

    report = asyncio.run(run())
    assert report["passed"] is successful
    assert report["mock"] is False  # Provider adapter, with simulated HTTP only.
    if successful:
        assert len(report["sessions"]) == 3 and len(requests) == 63
        for session in report["sessions"]:
            assert session["completed_hands"] == 3 and session["cost"] > 0
            assert session["raw_payloads"] == session["calls"]
            assert session["total_tokens"] < config.token_limit
            if session["channel"] != "none":
                # The old 20,000-token limit could not finish these sessions.
                assert session["total_tokens"] > 20_000
            if outcome == "cached":
                assert session["input_tokens_cache_read"] == 128 * session["calls"]
                assert session["reasoning_tokens"] == 64 * session["calls"]
            audit = read_model_log(
                tmp_path / "run" / "sessions" / session["session_id"] / "model.jsonl"
            )
            prompts = {
                e.data["request_id"]: cast(dict[str, Any], e.data["prompt"])
                for e in audit.events
                if e.event == "call_started"
            }
            for finished in audit.events:
                if finished.event != "call_finished":
                    continue
                event = cast(dict[str, Any], finished.data)["model_events"][0]
                prompt = prompts[finished.data["request_id"]]
                messages = [
                    {"role": "developer", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ]
                assert event["call"]["request"]["messages"] == messages
                assert any(request["messages"] == messages for request in requests)
                assert event["call"]["response"]["model"] == provider_model
    elif outcome == "wrong_model":
        assert any(
            "Returned model identifier differs" in issue
            for issue in report["sessions"][0]["issues"]
        )
    elif outcome == "usage":
        assert report["sessions"][0]["status"] == "complete"
        assert any("Token usage" in issue for issue in report["sessions"][0]["issues"])
    elif outcome.startswith(("schema_", "raw_")):
        expected = (
            "Generation settings"
            if outcome.startswith("schema_")
            else "Raw provider response format"
        )
        assert report["sessions"][0]["status"] == "complete"
        assert any(expected in issue for issue in report["sessions"][0]["issues"])
    else:
        assert len(requests) == (3 if outcome == "missing_recipient" else 1)
        # Public round siblings complete once; there is no response repair or retry.
        assert report["sessions"][0]["status"] == "failed"


def damage_response_schema(directory: Path, outcome: str, response_format: ResponseFormat) -> None:
    """Alter both stored copies so artifact equality alone cannot catch the mismatch."""
    path = next((directory / "inspect").glob("*.eval"))
    log = read_eval_log(str(path), resolve_attachments="full")
    assert log.samples
    sample = log.samples[0]
    event = next(e for e in sample.events if isinstance(e, ModelEvent))
    if outcome == "schema_mismatch":
        other_format: ResponseFormat = (
            "text" if response_format == "strict_json_schema" else "strict_json_schema"
        )
        other = ModelConfig("model", response_format=other_format)
        event.config.response_schema = generation_config(other, 1).response_schema
    elif outcome == "schema_strict_false":
        other = ModelConfig("model", response_format="strict_json_schema")
        schema = generation_config(other, 1).response_schema
        assert schema is not None
        schema.strict = False
        event.config.response_schema = schema
    else:
        assert event.call and isinstance(event.call.request, dict)
        if outcome == "raw_format_mismatch":
            event.call.request["response_format"] = {"type": "json_object"}
        else:
            schema_record = cast(dict[str, Any], decision_schema())
            schema_record["properties"]["decision"]["anyOf"][2]["required"].remove("recipient")
            event.call.request["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": SCHEMA_NAME,
                    "schema": schema_record,
                    "description": "A poker decision.",
                    "strict": True,
                },
            }
    write_eval_log(log, str(path))
    journal = directory / "sessions" / sample.metadata["session_id"] / "model.jsonl"
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    for row in rows:
        if row["event"] == "call_finished":
            for captured in row["data"]["model_events"]:
                if captured["uuid"] == event.uuid:
                    captured["config"] = event.config.model_dump(mode="json")
                    captured["call"] = (
                        None if event.call is None else event.call.model_dump(mode="json")
                    )
    journal.write_text("".join(canonical(row) + "\n" for row in rows))
