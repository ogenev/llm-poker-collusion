"""Game records. Audit-only schedules must never be included in player views."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

CARD_LABELS = ("J", "Q", "K", "A")
PLAYER_IDS = ("A", "B", "C")
type Deal = tuple[int, int, int]
type Seats = tuple[str, str, str]


class Action(StrEnum):
    CHECK = "check"
    BET = "bet"
    CALL = "call"
    FOLD = "fold"


@dataclass(frozen=True, slots=True)
class PublicAction:
    seat: int
    action: Action


@dataclass(frozen=True, slots=True)
class RevealedCard:
    seat: int
    card: str


@dataclass(frozen=True, slots=True)
class PokerView:
    """Allowlisted poker observation; contains no other player's private state."""

    seat: int
    own_card: str
    current_player: int | None
    legal_actions: tuple[Action, ...]
    history: tuple[PublicAction, ...]
    contributions: tuple[int, int, int]
    pot: int
    terminal: bool
    winner: int | None
    revealed_cards: tuple[RevealedCard, ...]
    own_reward: int | None


def require_int(value: object, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    return value


def validate_deal(value: object) -> Deal:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("A deal must contain exactly three cards")
    cards = tuple(require_int(card, "Card") for card in value)
    if any(card not in range(4) for card in cards) or len(set(cards)) != 3:
        raise ValueError("Cards must be distinct ranks in 0..3")
    return cast(Deal, cards)


def read_record(payload: str, kind: str, fields: set[str]) -> dict[str, object]:
    """Reject unknown versions/fields before replaying data into the native engine."""
    data: object = json.loads(payload)
    if not isinstance(data, dict) or set(data) != fields | {"kind", "version"}:
        raise ValueError(f"Invalid fields for {kind}")
    if data["kind"] != kind or type(data["version"]) is not int or data["version"] != 1:
        raise ValueError(f"Unsupported {kind} schema")
    return cast(dict[str, object], data)


@dataclass(frozen=True, slots=True)
class DealSchedule:
    """Trusted input shared across conditions; deals are indexed by acting seat."""

    seed: int
    initial_rotation: int
    deals: tuple[Deal, ...]

    def __post_init__(self) -> None:
        require_int(self.seed, "Seed")
        if require_int(self.initial_rotation, "Initial rotation") not in range(3):
            raise ValueError("Initial rotation must be 0, 1, or 2")
        if not isinstance(self.deals, tuple) or not self.deals:
            raise ValueError("Schedule must contain a nonempty tuple of deals")
        for deal in self.deals:
            if not isinstance(deal, tuple):
                raise ValueError("Schedule deals must be immutable tuples")
            validate_deal(deal)

    def seats_for_hand(self, hand_index: int) -> Seats:
        if require_int(hand_index, "Hand index") not in range(len(self.deals)):
            raise ValueError("Hand index is outside the saved schedule")
        offset = (self.initial_rotation + hand_index) % 3
        return cast(Seats, PLAYER_IDS[offset:] + PLAYER_IDS[:offset])

    def to_json(self) -> str:
        return json.dumps(
            {
                "kind": "deal_schedule",
                "version": 1,
                "seed": self.seed,
                "initial_rotation": self.initial_rotation,
                "deals": self.deals,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, payload: str) -> DealSchedule:
        data = read_record(payload, "deal_schedule", {"seed", "initial_rotation", "deals"})
        deals = data["deals"]
        if not isinstance(deals, list):
            raise ValueError("Schedule deals must be a list")
        return cls(
            seed=require_int(data["seed"], "Seed"),
            initial_rotation=require_int(data["initial_rotation"], "Initial rotation"),
            deals=tuple(validate_deal(deal) for deal in deals),
        )
