import asyncio
from dataclasses import FrozenInstanceError, asdict

import pytest

from poker_collusion.poker import generate_schedule
from poker_collusion.records import (
    Action,
    BetDecision,
    Channel,
    DealSchedule,
    Decision,
    MessageDecision,
    PassDecision,
    Phase,
    PlayerView,
    SessionConfig,
)
from poker_collusion.session import passive_decider, run_session


def capture_private_session(send_secret: bool) -> list[PlayerView]:
    seen: list[PlayerView] = []

    async def decide(view: PlayerView) -> Decision:
        seen.append(view)
        if view.phase == Phase.COMMUNICATION:
            if send_secret and view.player_id == "A" and view.round_index == 0:
                return MessageDecision("private A to B", "B")
            return PassDecision()
        return await passive_decider(view)

    config = SessionConfig(hands=4, channel=Channel.PRIVATE, memory_hands=2)
    state = asyncio.run(run_session(config, generate_schedule(0, 4), decide))
    assert state.phase == Phase.COMPLETE
    return seen


def test_private_message_and_its_metadata_do_not_change_outsider_views() -> None:
    sent = capture_private_session(True)
    silent = capture_private_session(False)
    assert [v for v in sent if v.player_id == "C"] == [v for v in silent if v.player_id == "C"]
    for player in ("A", "B"):
        assert any(v.messages for v in sent if v.player_id == player)
        assert any(m.messages for v in sent if v.player_id == player for m in v.history)
    for view in sent:
        if view.player_id == "C":
            assert "private A to B" not in str(asdict(view))
    final = next(v for v in sent if v.hand_index == 3 and v.player_id == "B")
    assert [m.hand_index for m in final.history] == [1, 2]


@pytest.mark.parametrize("channel", list(Channel))
def test_other_cards_never_enter_pre_settlement_observations(channel: Channel) -> None:
    def capture(cards: tuple[int, int, int]) -> list[PlayerView]:
        seen: list[PlayerView] = []

        async def decide(view: PlayerView) -> Decision:
            if view.player_id == "A":
                seen.append(view)
            return await passive_decider(view)

        config = SessionConfig(hands=1, channel=channel)
        asyncio.run(run_session(config, DealSchedule(0, 0, (cards,)), decide))
        return seen

    assert capture((0, 1, 2)) == capture((0, 3, 1))


def test_folded_card_stays_out_of_other_players_memories() -> None:
    def capture(folded_card: int) -> list[PlayerView]:
        seen: list[PlayerView] = []

        async def decide(view: PlayerView) -> Decision:
            seen.append(view)
            if view.hand_index == 0:
                actions = (Action.CHECK, Action.BET, Action.CALL, Action.FOLD)
                return BetDecision(actions[len(view.poker.history)])
            return await passive_decider(view)

        schedule = DealSchedule(0, 0, ((folded_card, 2, 3), (0, 1, 3)))
        state = asyncio.run(run_session(SessionConfig(hands=2), schedule, decide))
        assert state.phase == Phase.COMPLETE
        return seen

    first, second = capture(0), capture(1)
    for player in ("B", "C"):
        assert [v for v in first if v.player_id == player] == [
            v for v in second if v.player_id == player
        ]
    own = next(v for v in first if v.hand_index == 1 and v.player_id == "A")
    assert own.history[0].poker.own_card == "J"
    assert [(r.seat, r.card) for r in own.history[0].poker.revealed_cards] == [(1, "K"), (2, "A")]


def test_views_are_immutable_and_exclude_audit_state() -> None:
    async def decide(view: PlayerView) -> Decision:
        for name in (
            "config",
            "schedule",
            "seed",
            "rewards",
            "histories",
            "pending_messages",
            "poker_snapshot",
            "budgets",
            "failure",
        ):
            assert not hasattr(view, name)
        assert not hasattr(view.poker, "_state")
        mutations: list[tuple[object, str, object]] = [
            (view, "own_total_reward", 1000),
            (view.poker, "own_card", "A"),
        ]
        for memory in view.history:
            assert memory.seats[memory.poker.seat] == view.player_id
            mutations.append((memory.poker, "own_reward", 1000))
        for record, attribute, value in mutations:
            with pytest.raises(FrozenInstanceError):
                setattr(record, attribute, value)
        return await passive_decider(view)

    config = SessionConfig(hands=2, channel=Channel.PRIVATE)
    state = asyncio.run(run_session(config, generate_schedule(0, 2), decide))
    assert state.phase == Phase.COMPLETE


def test_memory_zero_removes_old_messages_but_keeps_cumulative_own_reward() -> None:
    seen: list[PlayerView] = []

    async def decide(view: PlayerView) -> Decision:
        seen.append(view)
        assert view.history == ()
        if view.phase == Phase.COMMUNICATION:
            return MessageDecision("hello")
        return await passive_decider(view)

    config = SessionConfig(hands=2, channel=Channel.PUBLIC, memory_hands=0)
    schedule = DealSchedule(0, 0, ((0, 1, 3), (0, 1, 3)))
    state = asyncio.run(run_session(config, schedule, decide))
    assert state.phase == Phase.COMPLETE
    assert all(not h for h in state.histories.values())
    second = [
        v
        for v in seen
        if v.hand_index == 1 and v.phase == Phase.COMMUNICATION and v.round_index == 0
    ]
    assert len(second) == 3
    assert all(v.messages == () for v in second)
    assert {v.player_id: v.own_total_reward for v in second} == {"A": -1, "B": -1, "C": 2}
