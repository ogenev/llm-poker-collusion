"""Game records. Audit-only schedules must never be included in player views."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
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


class Channel(StrEnum):
    NONE = "none"
    PUBLIC = "public"
    PRIVATE = "private"


class Phase(StrEnum):
    DEAL = "deal"
    COMMUNICATION = "communication"
    BETTING = "betting"
    SETTLEMENT = "settlement"
    MEMORY_UPDATE = "memory_update"
    COMPLETE = "complete"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class SessionConfig:
    """Pilot defaults, to be frozen separately before research evaluation."""

    hands: int = 30
    channel: Channel = Channel.NONE
    communication_rounds: int = 2
    max_message_chars: int = 500
    message_budget_chars: int = 1000
    memory_hands: int = 10
    decision_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.channel, Channel):
            raise ValueError("Channel must be a Channel enum value")
        for name in ("hands", "communication_rounds", "max_message_chars"):
            if require_int(getattr(self, name), name) < 1:
                raise ValueError(f"{name} must be positive")
        for name in ("message_budget_chars", "memory_hands"):
            if require_int(getattr(self, name), name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        timeout = self.decision_timeout_seconds
        try:
            valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
        except OverflowError:
            valid_timeout = False
        if not valid_timeout:
            raise ValueError("decision_timeout_seconds must be finite and positive")


@dataclass(frozen=True, slots=True)
class PassDecision:
    """Decline this communication opportunity; not a betting action."""


@dataclass(frozen=True, slots=True)
class MessageDecision:
    text: str
    recipient: str | None = None  # None denotes a public broadcast.


@dataclass(frozen=True, slots=True)
class BetDecision:
    action: Action


type Decision = PassDecision | MessageDecision | BetDecision


class DecisionParseError(ValueError):
    """An adapter could not decode text; retain it as an invalid audit candidate."""

    def __init__(self, response: str, detail: str) -> None:
        if type(response) is not str:
            raise TypeError("An unparsed response must be a built-in string")
        super().__init__(detail)
        self.response = response


@dataclass(frozen=True, slots=True)
class Message:
    sender: str
    recipient: str | None
    text: str
    round_index: int


@dataclass(frozen=True, slots=True)
class HandMemory:
    hand_index: int
    seats: Seats
    poker: PokerView
    messages: tuple[Message, ...]


@dataclass(frozen=True, slots=True)
class PlayerView:
    """Only this immutable projection crosses the decision-function boundary."""

    player_id: str
    seats: Seats
    hand_index: int
    total_hands: int
    phase: Phase
    round_index: int | None
    communication_rounds: int
    poker: PokerView
    messages: tuple[Message, ...]
    history: tuple[HandMemory, ...]
    own_total_reward: int
    public_message_allowed: bool
    private_recipients: tuple[str, ...]
    max_message_chars: int
    remaining_message_chars: int


class FailureKind(StrEnum):
    INVALID_DECISION = "invalid_decision"
    AGENT_ERROR = "agent_error"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class SessionFailure:
    kind: FailureKind
    detail: str
    phase: Phase
    hand_index: int
    round_index: int | None
    player_id: str | None


@dataclass(slots=True)
class SessionState:
    """Trusted in-memory result/state, never a model input or a recovery checkpoint.

    Poker snapshots, pending messages, budgets, and all players' histories are
    private audit data. The full deal schedule replaces a runtime dealing RNG.
    Decision functions must not keep hidden conversation memory.
    """

    config: SessionConfig
    schedule: DealSchedule
    phase: Phase = Phase.DEAL
    hand_index: int = 0
    round_index: int | None = None
    current_player: str | None = None
    seats: Seats = ("A", "B", "C")
    poker_snapshot: str | None = None
    completed_hands: int = 0
    rewards: dict[str, int] = field(default_factory=lambda: dict.fromkeys(PLAYER_IDS, 0))
    histories: dict[str, tuple[HandMemory, ...]] = field(
        default_factory=lambda: dict.fromkeys(PLAYER_IDS, ())
    )
    messages: tuple[Message, ...] = ()
    pending_messages: tuple[Message, ...] = ()
    budgets: dict[str, int] = field(default_factory=dict)
    failure: SessionFailure | None = None
