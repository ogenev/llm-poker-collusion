import asyncio
import json
from pathlib import Path
from typing import cast

import pytest

from poker_collusion.event_log import JsonlRecorder, RecordingError, read_log
from poker_collusion.model_adapter import ModelConfig, ModelRequest, model_decider
from poker_collusion.poker import PokerHand, generate_schedule
from poker_collusion.prompts import Instruction
from poker_collusion.records import Channel, FailureKind, Phase, SessionConfig
from poker_collusion.replay import replay_session
from poker_collusion.serialization import decode_candidate
from poker_collusion.session import SessionInterrupted, run_session


@pytest.mark.parametrize("channel", list(Channel))
@pytest.mark.parametrize("instruction", list(Instruction))
@pytest.mark.parametrize("memory", [0, 1])
def test_fake_model_sessions_complete_and_replay(
    tmp_path: Path, channel: Channel, instruction: Instruction, memory: int
) -> None:
    requests: list[ModelRequest] = []
    settings = ModelConfig("mock/offline", instruction, max_tokens=180, temperature=0.4)

    async def generate(request: ModelRequest) -> str:
        requests.append(request)
        assert request.config == settings
        assert not request.config.cache and request.config.max_retries == 0
        view = json.loads(request.prompt.user)
        if view["phase"] == "communication":
            if view["max_message_chars"] == 0:
                return '{"type":"pass"}'
            return json.dumps(
                {
                    "type": "message",
                    "text": "🂡 hi",
                    "recipient": view["private_recipients"][0]
                    if channel == Channel.PRIVATE
                    else None,
                }
            )
        legal = view["poker"]["legal_actions"]
        return json.dumps({"type": "bet", "action": "bet" if "bet" in legal else "call"})

    path = tmp_path / "session.jsonl"
    config = SessionConfig(hands=4, channel=channel, memory_hands=memory, message_budget_chars=4)
    with JsonlRecorder(path) as recorder:
        state = asyncio.run(
            run_session(
                config,
                generate_schedule(2, 4),
                model_decider(settings, generate),
                recorder=recorder,
            )
        )
    assert state.phase == Phase.COMPLETE
    assert state.completed_hands == 4
    assert sum(state.rewards.values()) == 0
    assert all(len(history) == memory for history in state.histories.values())
    assert len(requests) == (12 if channel == Channel.NONE else 36)
    assert asyncio.run(replay_session(path)) == state
    if channel != Channel.NONE:
        assert len(state.messages) == 3  # Second round is pass-only after budget exhaustion.
        assert all(message.text == "🂡 hi" for message in state.messages)


@pytest.mark.parametrize("channel", [Channel.NONE, Channel.PRIVATE])
@pytest.mark.parametrize("raw", ["I cannot play", "{broken", '{"type":"pass","extra":0}'])
def test_parse_failure_is_replayable_and_stops_without_repair(
    tmp_path: Path, channel: Channel, raw: str
) -> None:
    calls: list[ModelRequest] = []

    async def generate(request: ModelRequest) -> str:
        calls.append(request)
        if json.loads(request.prompt.user)["player_id"] == "A":
            return raw
        return '{"type":"message","text":"valid sibling","recipient":"A"}'

    path = tmp_path / "invalid.jsonl"
    config = SessionConfig(hands=2, channel=channel)
    with JsonlRecorder(path) as recorder:
        state = asyncio.run(
            run_session(
                config,
                generate_schedule(0, 2),
                model_decider(ModelConfig("mock/offline"), generate),
                recorder=recorder,
            )
        )
    assert state.phase == Phase.FAILED
    assert state.failure is not None and state.failure.kind == FailureKind.INVALID_DECISION
    assert state.failure.player_id == "A"
    assert len(calls) == (1 if channel == Channel.NONE else 3)
    assert state.completed_hands == 0
    assert state.messages == ()
    budget = 0 if channel == Channel.NONE else 1000
    assert state.budgets == {"A": budget, "B": budget, "C": budget}
    assert state.rewards == {"A": 0, "B": 0, "C": 0}
    assert state.poker_snapshot is not None
    assert PokerHand.from_json(state.poker_snapshot).history == ()
    if channel == Channel.PRIVATE:
        assert len(state.pending_messages) == 2
    returned = [e for e in read_log(path).events if e.event == "decision_returned"]
    assert decode_candidate(returned[0].data["candidate"]) == raw
    assert asyncio.run(replay_session(path)) == state


@pytest.mark.parametrize(
    "channel,response",
    [
        (Channel.NONE, '{"type":"bet","action":"call"}'),
        (Channel.NONE, '{"type":"pass"}'),
        (Channel.NONE, '{"type":"message","text":"hi","recipient":null}'),
        (Channel.PRIVATE, '{"type":"bet","action":"check"}'),
        (Channel.PRIVATE, '{"type":"message","text":"hi","recipient":null}'),
        (Channel.PRIVATE, '{"type":"message","text":"hi","recipient":"A"}'),
        (Channel.PRIVATE, '{"type":"message","text":"hi","recipient":"D"}'),
        (Channel.PUBLIC, '{"type":"message","text":"hi","recipient":"B"}'),
        (Channel.PUBLIC, '{"type":"message","text":"   ","recipient":null}'),
        (Channel.PUBLIC, '{"type":"message","text":"toolong","recipient":null}'),
    ],
)
def test_session_enforces_phase_recipients_and_budget(channel: Channel, response: str) -> None:
    async def generate(request: ModelRequest) -> str:
        return response

    config = SessionConfig(hands=1, channel=channel, message_budget_chars=3)
    state = asyncio.run(
        run_session(
            config,
            generate_schedule(0, 1),
            model_decider(ModelConfig("mock/offline"), generate),
        )
    )
    assert state.failure is not None and state.failure.kind == FailureKind.INVALID_DECISION
    assert state.completed_hands == 0 and state.messages == ()
    budget = 0 if channel == Channel.NONE else 3
    assert state.budgets == {"A": budget, "B": budget, "C": budget}


@pytest.mark.parametrize("channel", [Channel.NONE, Channel.PRIVATE])
@pytest.mark.parametrize("failure", ["error", "timeout", "non_text"])
def test_transport_failures_are_not_retried_and_replay(
    tmp_path: Path, channel: Channel, failure: str
) -> None:
    calls: list[ModelRequest] = []
    closed: list[ModelRequest] = []

    async def generate(request: ModelRequest) -> str:
        calls.append(request)
        try:
            if failure == "timeout":
                await asyncio.Event().wait()
            if failure == "non_text":
                return cast(str, {"type": "pass"})
            raise RuntimeError("fake provider unavailable")
        finally:
            closed.append(request)

    path = tmp_path / "failure.jsonl"
    config = SessionConfig(hands=2, channel=channel, decision_timeout_seconds=0.01)
    with JsonlRecorder(path) as recorder:
        state = asyncio.run(
            run_session(
                config,
                generate_schedule(0, 2),
                model_decider(ModelConfig("mock/offline"), generate),
                recorder=recorder,
            )
        )
    assert state.failure is not None
    expected = FailureKind.TIMEOUT if failure == "timeout" else FailureKind.AGENT_ERROR
    assert state.failure.kind == expected
    assert len(calls) == len(closed) == (1 if channel == Channel.NONE else 3)
    assert state.completed_hands == 0 and state.messages == ()
    assert asyncio.run(replay_session(path)) == state


def test_cancellation_cleans_up_model_requests_and_replays(tmp_path: Path) -> None:
    async def scenario() -> None:
        started: list[str] = []
        closed: list[str] = []
        ready = asyncio.Event()

        async def generate(request: ModelRequest) -> str:
            player = json.loads(request.prompt.user)["player_id"]
            started.append(player)
            if len(started) == 3:
                ready.set()
            try:
                await asyncio.Event().wait()
                raise AssertionError("The fake request must be cancelled")
            finally:
                closed.append(player)

        path = tmp_path / "interrupted.jsonl"
        with JsonlRecorder(path) as recorder:
            task = asyncio.create_task(
                run_session(
                    SessionConfig(hands=2, channel=Channel.PRIVATE),
                    generate_schedule(0, 2),
                    model_decider(ModelConfig("mock/offline"), generate),
                    recorder=recorder,
                )
            )
            await asyncio.wait_for(ready.wait(), 2)
            task.cancel()
            with pytest.raises(SessionInterrupted) as caught:
                await task
        assert sorted(closed) == sorted(started) == ["A", "B", "C"]
        assert caught.value.state.phase == Phase.INTERRUPTED
        assert await replay_session(path) == caught.value.state

    asyncio.run(scenario())


def test_recording_error_during_parse_failure_propagates(tmp_path: Path) -> None:
    class BrokenRecorder(JsonlRecorder):
        def emit(self, event: str, data: dict[str, object]) -> None:
            if event == "decision_returned":
                raise RecordingError("fake disk failure while retaining malformed text")
            super().emit(event, data)

    async def generate(request: ModelRequest) -> str:
        return "malformed output"

    path = tmp_path / "incomplete.jsonl"
    with BrokenRecorder(path) as recorder, pytest.raises(RecordingError, match="fake disk"):
        asyncio.run(
            run_session(
                SessionConfig(hands=1),
                generate_schedule(0, 1),
                model_decider(ModelConfig("mock/offline"), generate),
                recorder=recorder,
            )
        )
    assert read_log(path).status == "incomplete"
    assert read_log(path).events[-1].event == "decision_requested"
