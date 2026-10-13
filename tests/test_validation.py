import json
from typing import cast

import pytest

from poker_collusion.poker import PokerHand
from poker_collusion.records import Action, Deal


@pytest.mark.parametrize(
    "deal", [(0, 0, 1), (-1, 1, 2), (0, 1, 4), (True, 1, 2), (0.0, 1, 2), (), (0, 1), "012"]
)
def test_bad_deal_is_rejected_before_entering_native_engine(deal: object) -> None:
    with pytest.raises(ValueError):
        PokerHand(cast(Deal, deal))


@pytest.mark.parametrize("seat", [-1, 3, True, "0", 0.0])
def test_invalid_seat_is_rejected(seat: object) -> None:
    with pytest.raises(ValueError):
        PokerHand((0, 1, 2)).view(cast(int, seat))


def test_illegal_decisions_leave_state_unchanged() -> None:
    hand = PokerHand((0, 1, 2))
    before = hand.to_json()
    for action in (Action.CALL, Action.FOLD, "check", 0, None):
        with pytest.raises(ValueError):
            hand.apply(cast(Action, action))
        assert hand.to_json() == before
    hand.apply(Action.BET)
    before = hand.to_json()
    for action in (Action.CHECK, Action.BET):
        with pytest.raises(ValueError):
            hand.apply(action)
        assert hand.to_json() == before


def test_rewards_require_settlement() -> None:
    with pytest.raises(ValueError, match="after settlement"):
        PokerHand((0, 1, 2)).returns()


@pytest.mark.parametrize(
    "updates",
    [
        {"version": 2},
        {"version": True},
        {"kind": "another_game"},
        {"extra": "field"},
        {"deal": [0, 0, 1]},
        {"deal": None},
        {"actions": "check"},
        {"actions": [0]},
        {"actions": ["raise"]},
        {"actions": ["call"]},
        {"actions": ["bet", "check"]},
        {"actions": ["check", "check", "check", "bet"]},
    ],
)
def test_invalid_snapshot_is_rejected(updates: dict[str, object]) -> None:
    data = json.loads(PokerHand((0, 1, 2)).to_json())
    data.update(updates)
    with pytest.raises(ValueError):
        PokerHand.from_json(json.dumps(data))


@pytest.mark.parametrize("payload", ["invalid json", "null", "[]", "{}"])
def test_malformed_snapshot_is_rejected(payload: str) -> None:
    with pytest.raises(ValueError):
        PokerHand.from_json(payload)
