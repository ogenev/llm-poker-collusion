import asyncio
from dataclasses import replace

import pytest

from poker_collusion.poker import generate_schedule
from poker_collusion.records import (
    PLAYER_IDS,
    Action,
    BetDecision,
    Channel,
    Decision,
    MessageDecision,
    PassDecision,
    Phase,
    PlayerView,
    SessionConfig,
)
from poker_collusion.session import passive_decider, run_session, seeded_random_decider


@pytest.mark.parametrize("channel", list(Channel))
@pytest.mark.parametrize("offset", range(3))
def test_complete_sessions_match_deals_seats_rewards_and_memory(
    channel: Channel, offset: int
) -> None:
    config = SessionConfig(hands=30, channel=channel, memory_hands=3)
    schedule = generate_schedule(17, config.hands, offset)
    seen: list[PlayerView] = []

    async def decide(view: PlayerView) -> Decision:
        seen.append(view)
        return await passive_decider(view)

    state = asyncio.run(run_session(config, schedule, decide))
    assert state.phase == Phase.COMPLETE
    assert state.completed_hands == 30
    assert state.failure is None
    assert state.messages == state.pending_messages == ()
    assert state.current_player is None
    assert state.round_index is None
    expected = dict.fromkeys(PLAYER_IDS, 0)
    for index, deal in enumerate(schedule.deals):
        seats = schedule.seats_for_hand(index)
        winner = deal.index(max(deal))
        for player in PLAYER_IDS:
            views = [v for v in seen if v.hand_index == index and v.player_id == player]
            assert len(views) == (1 if channel == Channel.NONE else 3)
            for view in views:
                assert view.seats == seats
                assert view.poker.seat == seats.index(player)
                assert view.own_total_reward == expected[player]
                assert [memory.hand_index for memory in view.history] == list(
                    range(max(0, index - 3), index)
                )
            expected[player] += 2 if seats.index(player) == winner else -1
    assert state.rewards == expected
    assert sum(state.rewards.values()) == 0
    for player in PLAYER_IDS:
        assert [memory.hand_index for memory in state.histories[player]] == [27, 28, 29]
        assert state.histories[player][-1].poker.terminal
    if channel == Channel.NONE:
        assert all(view.phase == Phase.BETTING for view in seen)
        assert all(view.communication_rounds == view.remaining_message_chars == 0 for view in seen)


@pytest.mark.parametrize("channel", [Channel.PUBLIC, Channel.PRIVATE])
def test_messages_and_budget_reset_each_hand(channel: Channel) -> None:
    config = SessionConfig(
        hands=2,
        channel=channel,
        communication_rounds=3,
        max_message_chars=3,
        message_budget_chars=4,
    )
    seen: list[PlayerView] = []

    async def decide(view: PlayerView) -> Decision:
        seen.append(view)
        if view.phase == Phase.BETTING:
            return await passive_decider(view)
        assert view.poker.legal_actions == ()
        assert view.poker.current_player is None
        if view.round_index == 2:
            assert view.max_message_chars == view.remaining_message_chars == 0
            assert not view.public_message_allowed
            assert view.private_recipients == ()
            return PassDecision()
        recipient = view.private_recipients[0] if channel == Channel.PRIVATE else None
        return MessageDecision("abc" if view.round_index == 0 else "d", recipient)

    state = asyncio.run(run_session(config, generate_schedule(0, 2), decide))
    assert state.phase == Phase.COMPLETE
    assert len(state.messages) == 6
    assert state.budgets == dict.fromkeys(PLAYER_IDS, 0)
    for hand in range(2):
        for player in PLAYER_IDS:
            rounds = [
                v
                for v in seen
                if v.hand_index == hand and v.player_id == player and v.phase == Phase.COMMUNICATION
            ]
            assert [v.remaining_message_chars for v in rounds] == [4, 1, 0]
            assert [v.max_message_chars for v in rounds] == [3, 1, 0]
            assert rounds[0].messages == ()
            assert all(m.round_index == 0 for m in rounds[1].messages)
    for player, history in state.histories.items():
        for memory in history:
            assert all(
                m.recipient is None or player in (m.sender, m.recipient) for m in memory.messages
            )


def test_both_private_partners_are_available_to_every_player() -> None:
    config = SessionConfig(hands=3, channel=Channel.PRIVATE)

    async def decide(view: PlayerView) -> Decision:
        if view.phase == Phase.BETTING:
            return await passive_decider(view)
        assert set(view.private_recipients) == set(PLAYER_IDS) - {view.player_id}
        assert view.round_index is not None
        return MessageDecision("hello", view.private_recipients[view.round_index])

    state = asyncio.run(run_session(config, generate_schedule(0, 3), decide))
    assert state.phase == Phase.COMPLETE
    assert {(m.sender, m.recipient) for m in state.messages} == {
        (sender, recipient)
        for sender in PLAYER_IDS
        for recipient in PLAYER_IDS
        if sender != recipient
    }


@pytest.mark.parametrize("finish_order", [("A", "B", "C"), ("C", "B", "A")])
def test_delivery_waits_for_every_decision_and_ignores_completion_order(
    finish_order: tuple[str, ...],
) -> None:
    async def scenario() -> None:
        config = SessionConfig(hands=1, channel=Channel.PUBLIC)
        gates = {
            (round_index, player): asyncio.Event()
            for round_index in range(2)
            for player in PLAYER_IDS
        }
        seen: list[PlayerView] = []

        async def decide(view: PlayerView) -> Decision:
            if view.phase == Phase.BETTING:
                return await passive_decider(view)
            assert view.round_index is not None
            position = finish_order.index(view.player_id)
            if position:
                await gates[(view.round_index, finish_order[position - 1])].wait()
            seen.append(view)
            assert all(m.round_index < view.round_index for m in view.messages)
            if view.round_index == 1:
                assert [m.sender for m in view.messages] == ["A", "B", "C"]
            gates[(view.round_index, view.player_id)].set()
            return MessageDecision(f"{view.player_id}:{view.round_index}")

        state = await run_session(config, generate_schedule(0, 1), decide)
        assert state.phase == Phase.COMPLETE
        assert [v.player_id for v in seen] == list(finish_order) * 2
        assert [m.sender for m in state.messages] == ["A", "B", "C"] * 2

    asyncio.run(scenario())


def test_unicode_budget_counts_code_points_and_charges_broadcast_once() -> None:
    async def decide(view: PlayerView) -> Decision:
        if view.phase == Phase.COMMUNICATION:
            return MessageDecision("🂡")
        return BetDecision(Action.CHECK)

    config = SessionConfig(
        hands=1, channel=Channel.PUBLIC, max_message_chars=1, message_budget_chars=2
    )
    state = asyncio.run(run_session(config, generate_schedule(0, 1), decide))
    assert state.phase == Phase.COMPLETE
    assert state.budgets == dict.fromkeys(PLAYER_IDS, 0)
    assert all(len(state.histories[p][0].messages) == 6 for p in PLAYER_IDS)


@pytest.mark.parametrize("channel", list(Channel))
@pytest.mark.parametrize("memory_hands", [0, 1, 10])
def test_seeded_agents_are_repeatable_and_sessions_reset(
    channel: Channel, memory_hands: int
) -> None:
    config = SessionConfig(hands=6, channel=channel, memory_hands=memory_hands)
    schedule = generate_schedule(42, 6)
    decide = seeded_random_decider(19)
    first = asyncio.run(run_session(config, schedule, decide))
    second = asyncio.run(run_session(config, schedule, decide))
    assert first == second
    assert first.phase == Phase.COMPLETE
    assert all(len(h) == min(memory_hands, 6) for h in first.histories.values())
    assert sum(first.rewards.values()) == 0
    first.rewards["A"] = 999
    first.histories["B"] = ()
    assert second.rewards["A"] != 999
    if memory_hands:
        assert second.histories["B"]


@pytest.mark.parametrize("channel", [Channel.PUBLIC, Channel.PRIVATE])
def test_zero_budget_allows_only_passes(channel: Channel) -> None:
    config = SessionConfig(hands=1, channel=channel, message_budget_chars=0)
    state = asyncio.run(run_session(config, generate_schedule(0, 1), seeded_random_decider(0)))
    assert state.phase == Phase.COMPLETE
    assert not state.messages


@pytest.mark.parametrize(
    "updates",
    [
        {"hands": 0},
        {"hands": True},
        {"hands": 2.5},
        {"channel": "private"},
        {"communication_rounds": 0},
        {"max_message_chars": 0},
        {"message_budget_chars": -1},
        {"memory_hands": -1},
        {"memory_hands": False},
        {"decision_timeout_seconds": 0},
        {"decision_timeout_seconds": float("inf")},
        {"decision_timeout_seconds": float("nan")},
        {"decision_timeout_seconds": 10**400},
        {"decision_timeout_seconds": True},
        {"decision_timeout_seconds": "30"},
    ],
)
def test_invalid_session_configuration(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(SessionConfig(), **updates)  # type: ignore[arg-type]  # Exercise invalid runtime inputs.


def test_unknown_config_fields_and_schedule_mismatch_fail_before_calling_agent() -> None:
    with pytest.raises(TypeError):
        replace(SessionConfig(), unexpected=True)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="Schedule length"):
        asyncio.run(run_session(SessionConfig(hands=2), generate_schedule(0, 1), passive_decider))
