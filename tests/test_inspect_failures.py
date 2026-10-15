import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from inspect_ai.model import (
    ChatMessage,
    GenerateConfig,
    ModelCost,
    ModelInfo,
    ModelOutput,
    get_model,
    set_model_info,
)
from inspect_ai.tool import ToolChoice, ToolInfo

from poker_collusion.event_log import JsonlRecorder, RecordingError, read_log
from poker_collusion.experiment import run_experiment
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import ModelConfig
from poker_collusion.model_log import ModelJournal, read_model_log, verify_model_links
from poker_collusion.offline_model import scripted_output
from poker_collusion.records import Channel, SessionConfig
from poker_collusion.replay import replay_session

pytestmark = pytest.mark.usefixtures("inspect_runtime")


@pytest.mark.parametrize(
    "failure",
    [
        "malformed",
        "provider_error",
        "retryable_error",
        "refusal",
        "truncated",
        "no_choices",
        "decision_timeout",
        "token_limit",
        "cost_limit",
        "session_timeout",
    ],
)
def test_failures_remain_visible_and_replayable(
    tmp_path: Path, failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    closed = 0
    model_name = "mockllm/priced-test" if failure == "cost_limit" else "mockllm/model"
    if failure == "cost_limit":
        # Deliberately artificial pricing verifies Inspect's dollar-limit path
        # without involving a real provider or changing other mock models.
        set_model_info(
            model_name,
            ModelInfo(
                cost=ModelCost(input=10000, output=10000, input_cache_write=0, input_cache_read=0)
            ),
        )

    async def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        nonlocal calls, closed
        calls += 1
        try:
            if failure in {"decision_timeout", "session_timeout"}:
                await asyncio.sleep(5)
            if failure in {"provider_error", "retryable_error"}:
                raise RuntimeError("fake provider error")
            result = scripted_output(messages, tools, choice, config)
            result.model = model_name
            if failure == "malformed":
                result.completion = "not JSON"
                result.choices[0].message.content = result.completion
            elif failure == "refusal":
                result.choices[0].stop_reason = "content_filter"
            elif failure == "truncated":
                result.choices[0].stop_reason = "max_tokens"
            elif failure == "no_choices":
                result.choices = []
            return result
        finally:
            closed += 1

    config = ExperimentConfig(
        ModelConfig(model_name),
        session=SessionConfig(
            hands=1, decision_timeout_seconds=0.02 if failure == "decision_timeout" else 30
        ),
        channels=(Channel.NONE,),
        token_limit=50 if failure == "token_limit" else 10000,
        cost_limit=0.01 if failure == "cost_limit" else None,
        session_time_limit=0.05 if failure == "session_timeout" else 30,
    )
    model = get_model(model_name, memoize=False, custom_outputs=output)
    if failure == "retryable_error":
        monkeypatch.setattr(model.api, "should_retry", lambda error: True)
    logs = asyncio.run(run_experiment(config, tmp_path / "run", model=model))
    assert calls == closed == 1
    assert logs[0].samples and logs[0].samples[0].error is not None
    sample = logs[0].samples[0]
    expected_status = "interrupted" if failure == "session_timeout" else "failed"
    assert sample.metadata["session_status"] == expected_status
    audit = verify_model_links(sample.metadata["model_log"], sample.metadata["session_log"])
    assert audit.status == expected_status
    state = asyncio.run(replay_session(sample.metadata["session_log"]))
    assert state.completed_hands == 0 and state.phase.value == expected_status
    response = next(
        cast(dict[str, Any], e.data) for e in audit.events if e.event == "call_finished"
    )
    if failure in {"malformed", "refusal", "truncated", "no_choices"}:
        assert state.failure is not None and state.failure.kind.value == "invalid_decision"
        assert response["status"] == "returned"
    elif failure in {"token_limit", "cost_limit"}:
        # Inspect meters after receiving the response. Preserve that response
        # even when generate raises instead of returning it to the adapter.
        assert response["status"] == "error"
        assert response["model_events"][0]["output"]["completion"]
        if failure == "cost_limit":
            assert response["model_events"][0]["output"]["usage"]["total_cost"] > 0.01
    elif failure in {"decision_timeout", "session_timeout"}:
        assert response["status"] == "cancelled" and response["output"] is None
    else:
        assert response["status"] == "error" and response["output"] is None
    assert not any(
        e.event == "action_applied" for e in read_log(sample.metadata["session_log"]).events
    )


def test_model_recording_error_aborts_before_game_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    emit = ModelJournal.emit

    def fail(self: ModelJournal, event: str, **data: object) -> None:
        if event == "call_finished":
            raise RecordingError("fake model audit disk failure")
        emit(self, event, **data)

    monkeypatch.setattr(ModelJournal, "emit", fail)
    config = ExperimentConfig(
        ModelConfig("mockllm/model"), session=SessionConfig(hands=1), channels=(Channel.NONE,)
    )
    model = get_model("mockllm/model", memoize=False, custom_outputs=scripted_output)
    logs = asyncio.run(run_experiment(config, tmp_path / "run", model=model))
    assert logs[0].samples
    sample = logs[0].samples[0]
    assert sample.error is not None and "fake model audit disk failure" in sample.error.message
    assert sample.metadata["session_status"] == "incomplete"
    game = read_log(sample.metadata["session_log"])
    assert game.status == read_model_log(sample.metadata["model_log"]).status == "incomplete"
    assert game.events[-1].event == "decision_requested"


def test_raw_output_is_durable_before_session_accepts_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    emit = JsonlRecorder.emit
    checked = 0

    def check(self: JsonlRecorder, event: str, data: dict[str, object]) -> None:
        nonlocal checked
        if event == "decision_returned":
            audit = read_model_log(self.path.with_name("model.jsonl"))
            response = audit.events[-1]
            assert response.event == "call_finished"
            assert response.data["request_id"] == data["request_id"]
            assert response.data["status"] == "returned"
            checked += 1
        emit(self, event, data)

    monkeypatch.setattr(JsonlRecorder, "emit", check)
    config = ExperimentConfig(
        ModelConfig("mockllm/model"), session=SessionConfig(hands=1), channels=(Channel.NONE,)
    )
    model = get_model("mockllm/model", memoize=False, custom_outputs=scripted_output)
    logs = asyncio.run(run_experiment(config, tmp_path / "run", model=model))
    assert checked == 3 and logs[0].status == "success"
