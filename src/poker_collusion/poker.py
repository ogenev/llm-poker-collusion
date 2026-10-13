"""Small OpenSpiel adapter; only PokerView is suitable for a player decision."""

from __future__ import annotations

import json
import random
from functools import lru_cache
from typing import cast

import pyspiel

from poker_collusion.records import (
    CARD_LABELS,
    Action,
    Deal,
    DealSchedule,
    PokerView,
    PublicAction,
    RevealedCard,
    read_record,
    require_int,
    validate_deal,
)


@lru_cache(maxsize=1)
def _game() -> pyspiel.Game:
    return pyspiel.load_game("kuhn_poker(players=3)")


def generate_schedule(seed: int, hands: int, initial_rotation: int = 0) -> DealSchedule:
    """Sample from the full deck independently per hand, without touching global RNG."""
    require_int(seed, "Seed")
    if require_int(hands, "Hands") < 1:
        raise ValueError("Hands must be positive")
    rng = random.Random(seed)
    return DealSchedule(
        seed=seed,
        initial_rotation=initial_rotation,
        deals=tuple(validate_deal(rng.sample(range(4), 3)) for _ in range(hands)),
    )


class PokerHand:
    """A fully dealt game, owned only by trusted experiment code.

    Seats are 0..2; the session layer maps these to persistent player identities.
    Hidden cards and state are intentionally excluded from repr and player views.
    """

    def __init__(self, deal: Deal) -> None:
        self._deal = validate_deal(deal)
        self._state = _game().new_initial_state()
        for card in self._deal:
            self._state.apply_action(card)

    @property
    def terminal(self) -> bool:
        return bool(self._state.is_terminal())

    @property
    def current_player(self) -> int | None:
        return None if self.terminal else int(self._state.current_player())

    @property
    def history(self) -> tuple[PublicAction, ...]:
        moves: list[PublicAction] = []
        bet_open = False
        for index, code in enumerate(self._state.history()[3:]):
            if bet_open:
                action = Action.CALL if code == 1 else Action.FOLD
            else:
                action = Action.BET if code == 1 else Action.CHECK
            moves.append(PublicAction(seat=index % 3, action=action))
            bet_open = bet_open or action == Action.BET
        return tuple(moves)

    @property
    def legal_actions(self) -> tuple[Action, ...]:
        if self.terminal:
            return ()
        if any(move.action == Action.BET for move in self.history):
            return (Action.FOLD, Action.CALL)
        return (Action.CHECK, Action.BET)

    @property
    def contributions(self) -> tuple[int, int, int]:
        chips = [1, 1, 1]
        for move in self.history:
            if move.action in (Action.BET, Action.CALL):
                chips[move.seat] += 1
        return (chips[0], chips[1], chips[2])

    @property
    def pot(self) -> int:
        return sum(self.contributions)

    def apply(self, action: Action) -> None:
        """Apply one named legal action by the current seat, or leave state unchanged."""
        if not isinstance(action, Action) or action not in self.legal_actions:
            raise ValueError(f"Illegal action: {action!r}")
        self._state.apply_action(1 if action in (Action.BET, Action.CALL) else 0)

    def returns(self) -> tuple[int, int, int]:
        """Full net rewards, for trusted audit/analysis only; require settlement."""
        if not self.terminal:
            raise ValueError("Rewards are only available after settlement")
        values = self._state.returns()
        return (int(values[0]), int(values[1]), int(values[2]))

    def view(self, seat: int) -> PokerView:
        if require_int(seat, "Seat") not in range(3):
            raise ValueError("Seat must be 0, 1, or 2")
        winner = None
        revealed: tuple[RevealedCard, ...] = ()
        own_reward = None
        if self.terminal:
            rewards = self.returns()
            winner = max(range(3), key=lambda player: rewards[player])
            own_reward = rewards[seat]
            folded = {move.seat for move in self.history if move.action == Action.FOLD}
            active = [player for player in range(3) if player not in folded]
            if len(active) > 1:
                revealed = tuple(
                    RevealedCard(player, CARD_LABELS[self._deal[player]]) for player in active
                )
        return PokerView(
            seat=seat,
            own_card=CARD_LABELS[self._deal[seat]],
            current_player=self.current_player,
            legal_actions=self.legal_actions if self.current_player == seat else (),
            history=self.history,
            contributions=self.contributions,
            pot=self.pot,
            terminal=self.terminal,
            winner=winner,
            revealed_cards=revealed,
            own_reward=own_reward,
        )

    def clone(self) -> PokerHand:
        clone = PokerHand(self._deal)
        clone._state = self._state.clone()
        return clone

    def to_json(self) -> str:
        """Serialize the hidden deal and accepted actions; never expose to players."""
        return json.dumps(
            {
                "kind": "poker_hand",
                "version": 1,
                "deal": self._deal,
                "actions": [move.action.value for move in self.history],
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, payload: str) -> PokerHand:
        data = read_record(payload, "poker_hand", {"deal", "actions"})
        actions = data["actions"]
        if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
            raise ValueError("Actions must be a list of named decisions")
        hand = cls(validate_deal(data["deal"]))
        for action in cast(list[str], actions):
            hand.apply(Action(action))
        return hand
