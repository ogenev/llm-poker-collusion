import asyncio
from typing import cast

import pytest

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
from poker_collusion.session import SessionInterrupted, passive_decider, run_session


@pytest.mark.parametrize(
    "channel,invalid",
    [
        (Channel.PUBLIC, MessageDecision("hello", "B")),
        (Channel.PRIVATE, MessageDecision("hello")),
        (Channel.PRIVATE, MessageDecision("hello", "A")),
        (Channel.PRIVATE, MessageDecision("hello", "D")),
        (Channel.PRIVATE, MessageDecision("hello", cast(str, ["B", "C"]))),
        (Channel.PUBLIC, MessageDecision("    ")),
        (Channel.PUBLIC, MessageDecision(cast(str, 42))),
        (Channel.PUBLIC, MessageDecision("x" * 501)),
        (Channel.PUBLIC, BetDecision(Action.BET)),
        (Channel.PUBLIC, None),
        (Channel.PUBLIC, {"text": "unparsed message"}),
    ],
)
def test_malformed_communication_fails_without_delivery(channel: Channel, invalid: object) -> None:
    calls = []

    async def decide(view: PlayerView) -> Decision:
        calls.append(view)
        if view.player_id == "A":
            return cast(Decision, invalid)
        return MessageDecision("valid", "A" if channel == Channel.PRIVATE else None)

    config = SessionConfig(hands=2, channel=channel)
    state = asyncio.run(run_session(config, generate_schedule(0, 2), decide))
    assert state.phase == Phase.FAILED
    assert state.failure is not None
    assert state.failure.kind == FailureKind.INVALID_DECISION
    assert state.failure.player_id == "A"
    assert state.failure.phase == Phase.COMMUNICATION
    assert state.messages == ()
    assert len(state.pending_messages) == 2
    assert state.budgets == {"A": 1000, "B": 1000, "C": 1000}
    assert state.completed_hands == 0
    assert state.rewards == {"A": 0, "B": 0, "C": 0}
    assert len(calls) == 3  # No retries, betting requests, or subsequent hand.
    assert state.poker_snapshot is not None
    assert PokerHand.from_json(state.poker_snapshot).history == ()


@pytest.mark.parametrize(
    "invalid",
    [
        PassDecision(),
        MessageDecision("hello"),
        BetDecision(Action.CALL),
        BetDecision(cast(Action, "check")),
        None,
    ],
)
def test_bad_betting_preserves_completed_hands_without_substitution(invalid: object) -> None:
    async def decide(view: PlayerView) -> Decision:
        if view.hand_index == 1:
            return cast(Decision, invalid)
        return await passive_decider(view)

    config = SessionConfig(hands=3)
    schedule = generate_schedule(0, 3)
    state = asyncio.run(run_session(config, schedule, decide))
    assert state.phase == Phase.FAILED
    assert state.completed_hands == 1
    assert state.failure is not None
    assert state.failure.kind == FailureKind.INVALID_DECISION
    assert state.failure.hand_index == 1
    assert state.failure.player_id == "B"  # Seat 0 after rotation.
    assert state.failure.phase == Phase.BETTING
    assert sum(state.rewards.values()) == 0
    assert all(len(history) == 1 for history in state.histories.values())
    assert state.poker_snapshot is not None
    assert PokerHand.from_json(state.poker_snapshot).history == ()


def test_exhausted_budget_fails_the_entire_second_round() -> None:
    async def decide(view: PlayerView) -> Decision:
        return MessageDecision("abc")

    config = SessionConfig(hands=1, channel=Channel.PUBLIC, message_budget_chars=4)
    state = asyncio.run(run_session(config, generate_schedule(0, 1), decide))
    assert state.phase == Phase.FAILED
    assert state.failure is not None
    assert state.failure.round_index == 1
    assert len(state.messages) == 3
    assert all(m.round_index == 0 for m in state.messages)
    assert state.budgets == {"A": 1, "B": 1, "C": 1}


@pytest.mark.parametrize("channel", [Channel.NONE, Channel.PRIVATE])
def test_callback_exception_and_timeout_stop_without_retries(channel: Channel) -> None:
    async def scenario(timeout: bool) -> None:
        calls: list[str] = []
        closed: list[str] = []

        async def decide(view: PlayerView) -> Decision:
            calls.append(view.player_id)
            try:
                if timeout:
                    await asyncio.Event().wait()
                raise RuntimeError("simulated provider failure")
            finally:
                closed.append(view.player_id)

        config = SessionConfig(hands=1, channel=channel, decision_timeout_seconds=0.01)
        state = await run_session(config, generate_schedule(0, 1), decide)
        assert state.phase == Phase.FAILED
        assert state.failure is not None
        assert state.failure.kind == (FailureKind.TIMEOUT if timeout else FailureKind.AGENT_ERROR)
        assert (
            sorted(calls)
            == sorted(closed)
            == (["A"] if channel == Channel.NONE else ["A", "B", "C"])
        )
        assert state.completed_hands == 0
        assert not state.messages

    asyncio.run(scenario(False))
    asyncio.run(scenario(True))


@pytest.mark.parametrize("channel", [Channel.NONE, Channel.PRIVATE])
def test_external_cancellation_preserves_partial_state_and_closes_pending_calls(
    channel: Channel,
) -> None:
    async def scenario() -> None:
        started = asyncio.Event()
        active: set[str] = set()

        async def decide(view: PlayerView) -> Decision:
            active.add(view.player_id)
            started.set()
            try:
                await asyncio.Event().wait()
                return PassDecision()
            finally:
                active.remove(view.player_id)

        task = asyncio.create_task(
            run_session(SessionConfig(hands=1, channel=channel), generate_schedule(0, 1), decide)
        )
        await started.wait()
        task.cancel()
        with pytest.raises(SessionInterrupted) as caught:
            await task
        state = caught.value.state
        assert state.phase == Phase.INTERRUPTED
        assert state.failure is not None
        assert state.failure.kind == FailureKind.INTERRUPTED
        assert state.completed_hands == 0
        assert state.poker_snapshot is not None
        assert not active
        assert task.cancelled()

    asyncio.run(scenario())


def test_callback_cancellation_also_cleans_up_its_round_siblings() -> None:
    async def scenario() -> None:
        all_started = asyncio.Event()
        active: set[str] = set()

        async def decide(view: PlayerView) -> Decision:
            active.add(view.player_id)
            if len(active) == 3:
                all_started.set()
            try:
                await all_started.wait()
                if view.player_id == "A":
                    raise asyncio.CancelledError()
                await asyncio.Event().wait()
                return PassDecision()
            finally:
                active.remove(view.player_id)

        config = SessionConfig(hands=1, channel=Channel.PRIVATE)
        with pytest.raises(SessionInterrupted):
            await run_session(config, generate_schedule(0, 1), decide)
        assert not active

    asyncio.run(scenario())
