"""Independent path/payoff oracle for every deal and terminal betting sequence."""

import itertools
from dataclasses import dataclass

import pytest

from poker_collusion.poker import PokerHand
from poker_collusion.records import (
    CARD_LABELS,
    Action,
    Deal,
    PublicAction,
    RevealedCard,
    validate_deal,
)


@dataclass(frozen=True)
class Case:
    moves: tuple[PublicAction, ...]
    contributions: tuple[int, ...]
    active: tuple[int, ...]


def betting_cases() -> tuple[Case, ...]:
    # Construct the rulebook's 13 scenarios independently of engine transitions.
    cases = [Case(tuple(PublicAction(p, Action.CHECK) for p in range(3)), (1, 1, 1), (0, 1, 2))]
    for bettor in range(3):
        for calls in itertools.product((False, True), repeat=2):
            moves = [PublicAction(p, Action.CHECK) for p in range(bettor)]
            moves.append(PublicAction(bettor, Action.BET))
            chips = [1, 1, 1]
            chips[bettor] = 2
            active = [bettor]
            for distance, call in enumerate(calls, start=1):
                seat = (bettor + distance) % 3
                moves.append(PublicAction(seat, Action.CALL if call else Action.FOLD))
                if call:
                    chips[seat] = 2
                    active.append(seat)
            cases.append(Case(tuple(moves), tuple(chips), tuple(sorted(active))))
    assert len(cases) == 13
    return tuple(cases)


CASES = betting_cases()
DEALS = tuple(validate_deal(deal) for deal in itertools.permutations(range(4), 3))


@pytest.mark.parametrize("deal", DEALS)
@pytest.mark.parametrize("case", CASES)
def test_every_deal_and_terminal_path(deal: Deal, case: Case) -> None:
    hand = PokerHand(deal)
    for step, move in enumerate(case.moves):
        assert not hand.terminal
        assert hand.current_player == move.seat
        assert hand.history == case.moves[:step]
        bet_seen = any(m.action == Action.BET for m in case.moves[:step])
        expected_legal = (Action.FOLD, Action.CALL) if bet_seen else (Action.CHECK, Action.BET)
        assert hand.legal_actions == expected_legal
        expected_chips = tuple(
            1
            + sum(m.seat == p and m.action in (Action.BET, Action.CALL) for m in case.moves[:step])
            for p in range(3)
        )
        assert hand.contributions == expected_chips
        assert hand.pot == sum(expected_chips)
        saved = hand.to_json()
        restored = PokerHand.from_json(saved)
        copied = hand.clone()
        for seat in range(3):
            view = hand.view(seat)
            assert view.own_card == CARD_LABELS[deal[seat]]
            assert view.legal_actions == (expected_legal if seat == move.seat else ())
            assert view.revealed_cards == ()
            assert view.own_reward is None
            assert view.winner is None
            assert restored.view(seat) == copied.view(seat) == view
        restored.apply(move.action)
        copied.apply(move.action)
        assert hand.to_json() == saved  # Neither continuation can mutate its parent.
        hand.apply(move.action)
        assert hand.to_json() == restored.to_json() == copied.to_json()

    winner = max(case.active, key=lambda seat: deal[seat])
    expected_returns = tuple(
        (sum(case.contributions) if seat == winner else 0) - case.contributions[seat]
        for seat in range(3)
    )
    assert hand.terminal
    assert hand.current_player is None
    assert hand.history == case.moves
    assert hand.contributions == case.contributions
    assert hand.returns() == expected_returns
    assert sum(hand.returns()) == 0
    assert hand.legal_actions == ()
    expected_reveals = (
        tuple(RevealedCard(seat, CARD_LABELS[deal[seat]]) for seat in case.active)
        if len(case.active) > 1
        else ()
    )
    restored = PokerHand.from_json(hand.to_json())
    for seat in range(3):
        view = hand.view(seat)
        assert view.terminal
        assert view.winner == winner
        assert view.legal_actions == ()
        assert view.revealed_cards == expected_reveals
        assert view.own_reward == expected_returns[seat]
        assert restored.view(seat) == view
    for action in Action:
        with pytest.raises(ValueError, match="Illegal action"):
            hand.apply(action)


@pytest.mark.parametrize("deal", DEALS)
def test_paths_cover_the_entire_reachable_tree(deal: Deal) -> None:
    def leaves(hand: PokerHand) -> set[tuple[PublicAction, ...]]:
        if hand.terminal:
            return {hand.history}
        assert len(hand.history) < 5
        result = set()
        for action in hand.legal_actions:
            child = hand.clone()
            child.apply(action)
            result.update(leaves(child))
        return result

    assert leaves(PokerHand(deal)) == {case.moves for case in CASES}


@pytest.mark.parametrize("seat", range(3))
@pytest.mark.parametrize("own_card", range(4))
@pytest.mark.parametrize("case", CASES)
def test_hidden_cards_cannot_change_pre_settlement_views(
    seat: int, own_card: int, case: Case
) -> None:
    hands = [PokerHand(deal) for deal in DEALS if deal[seat] == own_card]
    assert len(hands) == 6
    for move in case.moves:
        reference = hands[0].view(seat)
        assert all(hand.view(seat) == reference for hand in hands)
        for hand in hands:
            hand.apply(move.action)


def test_folded_cards_are_hidden_at_showdown() -> None:
    hands = [PokerHand((rank, 2, 3)) for rank in (0, 1)]
    for hand in hands:
        for action in (Action.CHECK, Action.BET, Action.CALL, Action.FOLD):
            hand.apply(action)
    for seat in (1, 2):
        assert hands[0].view(seat) == hands[1].view(seat)
    assert hands[0].view(0).own_card != hands[1].view(0).own_card
    assert hands[0].view(0).revealed_cards == (RevealedCard(1, "K"), RevealedCard(2, "A"))


def test_winner_card_is_hidden_when_opponents_fold() -> None:
    hands = [PokerHand((rank, 1, 2)) for rank in (0, 3)]
    for hand in hands:
        for action in (Action.BET, Action.FOLD, Action.FOLD):
            hand.apply(action)
    for seat in (1, 2):
        assert hands[0].view(seat) == hands[1].view(seat)
        assert hands[0].view(seat).revealed_cards == ()


def test_clone_can_take_a_different_action() -> None:
    hand = PokerHand((0, 1, 3))
    branch = hand.clone()
    hand.apply(Action.CHECK)
    branch.apply(Action.BET)
    assert hand.legal_actions == (Action.CHECK, Action.BET)
    assert branch.legal_actions == (Action.FOLD, Action.CALL)
    assert hand.pot == 3
    assert branch.pot == 4
