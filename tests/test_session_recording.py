import asyncio
import json
import os
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import cast

import pytest

from poker_collusion import serialization
from poker_collusion.event_log import JsonlRecorder, RecordingError, read_log
from poker_collusion.poker import PokerHand, generate_schedule
from poker_collusion.records import (
    Action,
    BetDecision,
    Channel,
    Decision,
    FailureKind,
    MessageDecision,
    PassDecision,
    Phase,
    PlayerView,
    SessionConfig,
)
from poker_collusion.replay import IncompleteLogError, replay_session
from poker_collusion.serialization import decode_candidate, object_record
from poker_collusion.session import SessionInterrupted, passive_decider, run_session


def test_views_and_decisions_are_durable_before_calls_and_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "session.jsonl"
    seen = []
    original_apply = PokerHand.apply

    def checked_apply(hand: PokerHand, action: Action) -> None:
        event = read_log(path).events[-1]
        assert event.event == "decision_resolved"
        assert decode_candidate(event.data["decision"]) == BetDecision(action)
        original_apply(hand, action)

    monkeypatch.setattr(PokerHand, "apply", checked_apply)

    async def decide(view: PlayerView) -> Decision:
        journal = read_log(path)
        assert journal.status == "incomplete"
        requests = [event for event in journal.events if event.event == "decision_requested"]
        assert requests[-1].data["view"] == object_record(view)
        seen.append(object_record(view))
        return await passive_decider(view)

    with JsonlRecorder(
        path, session_id="session", run_id="preparation", matched_block_id="block"
    ) as recorder:
        state = asyncio.run(
            run_session(SessionConfig(hands=2), generate_schedule(8, 2), decide, recorder=recorder)
        )
        assert read_log(path).status == "complete"  # Still open: every event has been flushed.
        with pytest.raises(RecordingError):
            recorder.emit("session_started", {})
    assert state.phase == Phase.COMPLETE
    assert path.stat().st_mode & 0o777 == 0o600
    journal = read_log(path)
    assert [
        event.data["view"] for event in journal.events if event.event == "decision_requested"
    ] == seen
    first = json.loads(path.read_text().splitlines()[0])
    assert first["metadata"] == {"run_id": "preparation", "matched_block_id": "block"}
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        JsonlRecorder(path)
    assert path.read_bytes() == before


def test_audit_keeps_forgotten_hands_and_exact_private_views(tmp_path: Path) -> None:
    path = tmp_path / "private.jsonl"
    views: list[PlayerView] = []
    text = "  secret 🂡\nsecond line  "

    async def decide(view: PlayerView) -> Decision:
        views.append(view)
        if view.phase == Phase.COMMUNICATION and view.player_id == "A":
            return MessageDecision(text, "B")
        return await passive_decider(view)

    with JsonlRecorder(path, session_id="audit-only-id") as recorder:
        state = asyncio.run(
            run_session(
                SessionConfig(hands=4, channel=Channel.PRIVATE, memory_hands=1),
                generate_schedule(12, 4),
                decide,
                recorder=recorder,
            )
        )
    assert all(len(history) == 1 for history in state.histories.values())
    journal = read_log(path)
    recorded = [e.data["view"] for e in journal.events if e.event == "decision_requested"]
    assert recorded == [object_record(view) for view in views]
    assert {view.hand_index for view in views} == {0, 1, 2, 3}
    for view in views:
        assert "audit-only-id" not in json.dumps(object_record(view))
        if view.player_id == "C":
            assert text not in json.dumps(object_record(view), ensure_ascii=False)
            assert not view.messages
            assert all(not memory.messages for memory in view.history)
    assert any(message.text == text for view in views for message in view.messages)
    assert asyncio.run(replay_session(path)) == state


@pytest.mark.parametrize("channel", [Channel.NONE, Channel.PRIVATE])
@pytest.mark.parametrize("completed_response", [False, True])
def test_cancellation_preserves_responses_and_replays_partial_state(
    tmp_path: Path,
    channel: Channel,
    completed_response: bool,
) -> None:
    path = tmp_path / "cancelled.jsonl"

    async def scenario() -> None:
        started = asyncio.Event()
        active: set[str] = set()

        async def decide(view: PlayerView) -> Decision:
            if view.hand_index == 0:
                return await passive_decider(view)
            if channel == Channel.PRIVATE and completed_response and view.player_id == "A":
                return MessageDecision("preserve me", "B")
            active.add(view.player_id)
            started.set()
            try:
                await asyncio.Event().wait()
                return PassDecision()
            finally:
                active.remove(view.player_id)

        with JsonlRecorder(path) as recorder:
            task = asyncio.create_task(
                run_session(
                    SessionConfig(hands=3, channel=channel),
                    generate_schedule(9, 3),
                    decide,
                    recorder=recorder,
                )
            )
            await started.wait()
            task.cancel()
            with pytest.raises(SessionInterrupted) as caught:
                await task
        assert not active
        original = caught.value.state
        assert original.completed_hands == 1
        assert read_log(path).status == "interrupted"
        replayed = await asyncio.wait_for(replay_session(path), 2)
        assert replayed == original
        if channel == Channel.PRIVATE and completed_response:
            responses = [e for e in read_log(path).events if e.event == "decision_returned"]
            assert any(
                decode_candidate(e.data["candidate"]) == MessageDecision("preserve me", "B")
                for e in responses
            )

    asyncio.run(scenario())


def test_cancellation_before_round_callbacks_start_is_recorded(tmp_path: Path) -> None:
    path = tmp_path / "early-cancel.jsonl"

    async def scenario() -> None:
        with JsonlRecorder(path) as recorder:
            original_emit = recorder.emit

            def emit(event: str, data: dict[str, object]) -> None:
                original_emit(event, data)
                if event == "decision_requested" and data["request_id"] == 2:
                    task = asyncio.current_task()
                    assert task is not None
                    task.cancel()

            recorder.emit = emit  # type: ignore[method-assign]
            with pytest.raises(SessionInterrupted) as caught:
                await run_session(
                    SessionConfig(hands=1, channel=Channel.PUBLIC),
                    generate_schedule(0, 1),
                    passive_decider,
                    recorder=recorder,
                )
        assert read_log(path).status == "interrupted"
        assert await asyncio.wait_for(replay_session(path), 2) == caught.value.state

    asyncio.run(scenario())


def test_self_cancellation_records_other_finished_responses(tmp_path: Path) -> None:
    path = tmp_path / "self-cancel.jsonl"

    async def decide(view: PlayerView) -> Decision:
        if view.player_id == "A":
            raise asyncio.CancelledError()
        return MessageDecision("finished", "A")

    with JsonlRecorder(path) as recorder, pytest.raises(SessionInterrupted) as caught:
        asyncio.run(
            run_session(
                SessionConfig(hands=1, channel=Channel.PRIVATE),
                generate_schedule(0, 1),
                decide,
                recorder=recorder,
            )
        )
    assert len([e for e in read_log(path).events if e.event == "decision_returned"]) == 2
    assert asyncio.run(replay_session(path)) == caught.value.state


def test_cancellation_after_all_responses_before_delivery_replays(tmp_path: Path) -> None:
    path = tmp_path / "boundary-cancel.jsonl"

    async def scenario() -> None:
        with JsonlRecorder(path) as recorder:
            original_emit = recorder.emit
            parent = asyncio.current_task()
            assert parent is not None

            def emit(event: str, data: dict[str, object]) -> None:
                original_emit(event, data)
                if event == "decision_resolved" and data["request_id"] == 2:
                    parent.cancel()

            recorder.emit = emit  # type: ignore[method-assign]
            with pytest.raises(SessionInterrupted) as caught:
                await run_session(
                    SessionConfig(hands=1, channel=Channel.PRIVATE),
                    generate_schedule(0, 1),
                    passive_decider,
                    recorder=recorder,
                )
        journal = read_log(path)
        assert not any(e.event == "request_cancelled" for e in journal.events)
        assert not caught.value.state.messages
        assert await asyncio.wait_for(replay_session(path), 2) == caught.value.state

    asyncio.run(scenario())


def test_recording_failure_stops_before_action_and_is_not_an_agent_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "disk-error.jsonl"
    actions: list[Action] = []

    def apply(hand: PokerHand, action: Action) -> None:
        actions.append(action)

    monkeypatch.setattr(PokerHand, "apply", apply)
    original_fsync = os.fsync

    def fsync(descriptor: int) -> None:
        if path.exists() and b'"event":"decision_resolved"' in path.read_bytes():
            raise OSError("disk unavailable")
        original_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fsync)
    with JsonlRecorder(path) as recorder, pytest.raises(RecordingError):
        asyncio.run(
            run_session(
                SessionConfig(hands=1),
                generate_schedule(0, 1),
                passive_decider,
                recorder=recorder,
            )
        )
    assert not actions
    assert read_log(path).status == "incomplete"
    assert not any(e.event == "session_failed" for e in read_log(path).events)
    with pytest.raises(IncompleteLogError):
        asyncio.run(replay_session(path))


def test_process_exit_retains_committed_prefix_without_terminal_record(tmp_path: Path) -> None:
    path = tmp_path / "crash.jsonl"
    program = """
import asyncio, os, sys
from poker_collusion.event_log import JsonlRecorder
from poker_collusion.poker import generate_schedule
from poker_collusion.records import SessionConfig
from poker_collusion.session import passive_decider, run_session
async def decide(view):
    if view.hand_index == 1:
        os._exit(23)
    return await passive_decider(view)
with JsonlRecorder(sys.argv[1]) as recorder:
    asyncio.run(run_session(
        SessionConfig(hands=3), generate_schedule(0, 3), decide, recorder=recorder,
    ))
"""
    result = subprocess.run([sys.executable, "-c", program, str(path)], check=False)
    assert result.returncode == 23
    log = read_log(path)
    assert log.status == "incomplete"
    assert log.trailing_bytes == 0
    assert len([e for e in log.events if e.event == "memory_updated"]) == 1
    assert log.events[-1].event == "decision_requested"
    with pytest.raises(IncompleteLogError):
        asyncio.run(replay_session(path))


def test_unsupported_python_output_is_diagnostic_and_still_fails(tmp_path: Path) -> None:
    class Invalid:
        def __repr__(self) -> str:
            raise RuntimeError("no repr")

    async def decide(view: PlayerView) -> Decision:
        return cast(Decision, Invalid())

    path = tmp_path / "invalid.jsonl"
    with JsonlRecorder(path) as recorder:
        state = asyncio.run(
            run_session(
                SessionConfig(hands=1),
                generate_schedule(0, 1),
                decide,
                recorder=recorder,
            )
        )
    assert state.phase == Phase.FAILED
    assert "<repr unavailable>" in path.read_text()
    assert asyncio.run(replay_session(path)) == state


@pytest.mark.parametrize("subclass", ["decision", "text", "recipient", "container"])
def test_subclasses_cannot_be_accepted_without_a_replayable_schema(
    tmp_path: Path,
    subclass: str,
) -> None:
    class CustomBet(BetDecision):
        pass

    class CustomString(str):
        pass

    class CustomList(list[str]):
        pass

    async def decide(view: PlayerView) -> Decision:
        return cast(
            Decision,
            {
                "decision": CustomBet(Action.CHECK),
                "text": MessageDecision(CustomString("hello"), "B"),
                "recipient": MessageDecision("hello", CustomString("B")),
                "container": CustomList(["unexpected"]),
            }[subclass],
        )

    path = tmp_path / "unsupported-subclass.jsonl"
    channel = Channel.NONE if subclass == "decision" else Channel.PRIVATE
    with JsonlRecorder(path) as recorder:
        state = asyncio.run(
            run_session(
                SessionConfig(hands=1, channel=channel),
                generate_schedule(0, 1),
                decide,
                recorder=recorder,
            )
        )
    assert state.phase == Phase.FAILED
    assert state.completed_hands == 0
    assert asyncio.run(replay_session(path)) == state


@pytest.mark.parametrize("recording", [False, True])
@pytest.mark.parametrize("shape", ["deep", "cyclic", "large_integer"])
@pytest.mark.parametrize("field", ["response", "action", "text", "recipient"])
def test_malformed_values_fail_without_serialization_crashes(
    tmp_path: Path,
    recording: bool,
    shape: str,
    field: str,
) -> None:
    malformed: object = "leaf"
    if shape == "deep":
        for _ in range(1100):
            malformed = [malformed]
    elif shape == "cyclic":
        cycle: list[object] = []
        cycle.append(cycle)
        malformed = cycle
    else:
        malformed = 1 << 20000
    candidate = {
        "response": malformed,
        "action": BetDecision(cast(Action, malformed)),
        "text": MessageDecision(cast(str, malformed), "B"),
        "recipient": MessageDecision("hello", cast(str, malformed)),
    }[field]

    async def decide(view: PlayerView) -> Decision:
        return cast(Decision, candidate) if view.player_id == "A" else await passive_decider(view)

    channel = Channel.NONE if field in ("response", "action") else Channel.PRIVATE
    path = tmp_path / "malformed.jsonl"
    with JsonlRecorder(path) if recording else nullcontext() as recorder:
        state = asyncio.run(
            run_session(
                SessionConfig(hands=2, channel=channel),
                generate_schedule(0, 2),
                decide,
                recorder=recorder,
            )
        )
    assert state.phase == Phase.FAILED
    assert state.completed_hands == 0
    assert state.failure is not None
    assert state.failure.kind == FailureKind.INVALID_DECISION
    if recording:
        assert read_log(path).status == "failed"
        assert asyncio.run(replay_session(path)) == state
    else:
        assert not path.exists()


def test_unlogged_sessions_never_invoke_audit_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*args: object, **kwargs: object) -> str:
        raise AssertionError("Audit serialization ran without a recorder")

    monkeypatch.setattr(serialization, "canonical", unexpected)
    monkeypatch.setattr(serialization, "encode_candidate", unexpected)
    state = asyncio.run(
        run_session(
            SessionConfig(hands=2, channel=Channel.PUBLIC),
            generate_schedule(0, 2),
            passive_decider,
        )
    )
    assert state.phase == Phase.COMPLETE
