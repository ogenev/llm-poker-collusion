import asyncio
import json
from pathlib import Path
from typing import Any, cast

import pytest
from inspect_ai.event import ModelEvent
from inspect_ai.log import read_eval_log
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.tool import ToolChoice, ToolInfo

from poker_collusion.event_log import read_log
from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.model_log import read_model_log, verify_model_links
from poker_collusion.offline_model import offline_model, scripted_output
from poker_collusion.prompts import Instruction
from poker_collusion.records import Channel, Phase, SessionConfig
from poker_collusion.replay import replay_session

pytestmark = pytest.mark.usefixtures("inspect_runtime")


def test_inspect_runs_matched_sessions_with_complete_linked_evidence(tmp_path: Path) -> None:
    config = ExperimentConfig(
        ModelConfig("mockllm/model"), session=SessionConfig(hands=3), seeds=(0, 1), max_samples=2
    )
    root = tmp_path / "run"
    logs = asyncio.run(run_experiment(config, root, model=offline_model()))
    assert len(logs) == 1 and logs[0].status == "success"
    assert logs[0].location is not None
    saved = read_eval_log(logs[0].location, resolve_attachments="full")
    assert saved.samples is not None and len(saved.samples) == 6
    for sample in saved.samples:
        assert sample.error is None and sample.metadata["session_status"] == "complete"
        game_path, model_path = (
            Path(sample.metadata["session_log"]),
            Path(sample.metadata["model_log"]),
        )
        audit = verify_model_links(model_path, game_path)
        game = read_log(game_path)
        assert audit.status == "complete"
        state = asyncio.run(replay_session(game_path))
        assert state.phase == Phase.COMPLETE and state.completed_hands == 3
        assert state.rewards == sample.metadata["session_result"]["rewards"]
        started = {
            e.data["request_id"]: cast(dict[str, Any], e.data)
            for e in audit.events
            if e.event == "call_started"
        }
        finished = [
            cast(dict[str, Any], e.data) for e in audit.events if e.event == "call_finished"
        ]
        requested = {
            e.data["request_id"]: e.data for e in game.events if e.event == "decision_requested"
        }
        inspect_events = {e.uuid: e for e in sample.events if isinstance(e, ModelEvent)}
        assert len(finished) == len(started) == len(requested) == len(inspect_events)
        for call in finished:
            request = started[call["request_id"]]
            assert call["status"] == "returned" and call["output"]["usage"]["total_tokens"] == 110
            assert len(call["model_events"]) == 1
            event = call["model_events"][0]
            assert event["uuid"] in inspect_events and event["span_id"] == request["span_id"]
            assert event["call"]["response"]["content"] == call["output"]["completion"]
            assert event["call"]["request"]["messages"][0]["content"] == request["prompt"]["system"]
            assert (
                json.loads(event["call"]["request"]["messages"][1]["content"])
                == requested[call["request_id"]]["view"]
            )
            assert len(event["input"]) == 2 and not event["tools"]
            assert event["config"]["max_retries"] == 0 and event["cache"] is None
        assert game_path.stat().st_mode & 0o777 == model_path.stat().st_mode & 0o777 == 0o600
    manifest = [json.loads(line) for line in (root / "run.jsonl").read_text().splitlines()]
    assert [row["event"] for row in manifest] == ["started", "ended"]
    assert manifest[1]["inspect_logs"][0]["eval_id"] == saved.eval.eval_id
    assert manifest[0]["provenance"]["packages"]["inspect-ai"]


def test_concurrent_calls_keep_player_request_links(tmp_path: Path) -> None:
    active = peak = 0
    arrivals: list[str] = []

    async def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        nonlocal active, peak
        view = json.loads(messages[-1].text)
        active += 1
        peak = max(peak, active)
        await asyncio.sleep({"A": 0.03, "B": 0.02, "C": 0.01}[view["player_id"]])
        active -= 1
        arrivals.append(view["player_id"])
        result = scripted_output(messages, tools, choice, config)
        if view["phase"] == "communication":
            text = json.dumps(
                {
                    "type": "message",
                    "text": "from-" + view["player_id"],
                    "recipient": view["private_recipients"][0],
                }
            )
            result.choices[0].message.content = text
            result.completion = text
        return result

    model = get_model("mockllm/model", memoize=False, custom_outputs=output)
    config = ExperimentConfig(
        ModelConfig("mockllm/model"),
        session=SessionConfig(hands=1, communication_rounds=1),
        channels=(Channel.PRIVATE,),
    )
    logs = asyncio.run(run_experiment(config, tmp_path / "run", model=model))
    assert peak == 3 and arrivals[:3] == ["C", "B", "A"]
    assert logs[0].samples is not None
    sample = logs[0].samples[0]
    audit = verify_model_links(sample.metadata["model_log"], sample.metadata["session_log"])
    calls = [e.data for e in audit.events if e.event == "call_finished"]
    assert [call["request_id"] for call in calls[:3]] == [2, 1, 0]
    state = asyncio.run(replay_session(sample.metadata["session_log"]))
    assert [message.text for message in state.messages] == ["from-A", "from-B", "from-C"]


def test_connection_limit_is_enforced_across_concurrent_sessions(tmp_path: Path) -> None:
    active = peak = 0

    async def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.002)
        active -= 1
        return scripted_output(messages, tools, choice, config)

    config = ExperimentConfig(
        ModelConfig("mockllm/model"),
        session=SessionConfig(hands=1),
        max_samples=3,
        max_connections=1,
    )
    model = get_model("mockllm/model", memoize=False, custom_outputs=output)
    logs = asyncio.run(run_experiment(config, tmp_path / "run", model=model))
    assert peak == 1 and logs[0].samples is not None
    assert all(sample.metadata["session_status"] == "complete" for sample in logs[0].samples)


def test_independent_attempts_do_not_reuse_outputs_or_overwrite_files(tmp_path: Path) -> None:
    calls = 0

    def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        nonlocal calls
        calls += 1
        return scripted_output(messages, tools, choice, config)

    config = ExperimentConfig(
        ModelConfig("mockllm/model"), session=SessionConfig(hands=1), channels=(Channel.NONE,)
    )
    model = get_model("mockllm/model", memoize=False, custom_outputs=output)
    first = asyncio.run(run_experiment(config, tmp_path / "one", model=model))
    second = asyncio.run(run_experiment(config, tmp_path / "two", model=model))
    assert calls == 6
    assert first[0].samples and second[0].samples
    assert first[0].samples[0].metadata["session_id"] != second[0].samples[0].metadata["session_id"]
    with pytest.raises(FileExistsError):
        asyncio.run(run_experiment(config, tmp_path / "one", model=model))
    assert calls == 6


def test_control_uses_its_own_instructions(tmp_path: Path) -> None:
    config = ExperimentConfig(
        ModelConfig("mockllm/model", Instruction.COORDINATION_CONTROL),
        session=SessionConfig(hands=1),
        channels=(Channel.PUBLIC,),
    )
    logs = asyncio.run(run_experiment(config, tmp_path / "control", model=offline_model()))
    assert logs[0].samples
    audit = read_model_log(logs[0].samples[0].metadata["model_log"])
    assert any(
        "actively seek an agreement" in cast(dict[str, Any], e.data)["prompt"]["system"]
        for e in audit.events
        if e.event == "call_started"
    )
