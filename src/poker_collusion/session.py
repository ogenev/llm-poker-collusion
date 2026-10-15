"""Repeated hands with private observations and barrier-delivered communication."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import replace

from poker_collusion.poker import PokerHand
from poker_collusion.records import (
    PLAYER_IDS,
    Action,
    BetDecision,
    Channel,
    DealSchedule,
    Decision,
    FailureKind,
    HandMemory,
    Message,
    MessageDecision,
    PassDecision,
    Phase,
    PlayerView,
    SessionConfig,
    SessionFailure,
    SessionState,
    require_int,
)

type Decider = Callable[[PlayerView], Awaitable[Decision]]


class SessionInterrupted(asyncio.CancelledError):
    """Cancellation remains cancellation, while retaining the partial audit state."""

    def __init__(self, state: SessionState) -> None:
        super().__init__("Session interrupted")
        self.state = state


def _visible_messages(messages: tuple[Message, ...], player: str) -> tuple[Message, ...]:
    return tuple(m for m in messages if m.recipient is None or player in (m.sender, m.recipient))


def _view(state: SessionState, hand: PokerHand, player: str) -> PlayerView:
    poker = hand.view(state.seats.index(player))
    communicating = state.phase == Phase.COMMUNICATION
    if communicating:
        poker = replace(poker, current_player=None, legal_actions=())
    remaining = state.budgets[player]
    can_send = communicating and remaining > 0
    return PlayerView(
        player_id=player,
        seats=state.seats,
        hand_index=state.hand_index,
        total_hands=state.config.hands,
        phase=state.phase,
        round_index=state.round_index,
        communication_rounds=(
            state.config.communication_rounds if state.config.channel != Channel.NONE else 0
        ),
        poker=poker,
        messages=_visible_messages(state.messages, player),
        history=state.histories[player],
        own_total_reward=state.rewards[player],
        public_message_allowed=can_send and state.config.channel == Channel.PUBLIC,
        private_recipients=(
            tuple(p for p in PLAYER_IDS if p != player)
            if can_send and state.config.channel == Channel.PRIVATE
            else ()
        ),
        max_message_chars=min(state.config.max_message_chars, remaining) if can_send else 0,
        remaining_message_chars=remaining,
    )


def _validate(view: PlayerView, decision: object) -> Decision:
    if view.phase == Phase.BETTING:
        if (
            not isinstance(decision, BetDecision)
            or not isinstance(decision.action, Action)
            or decision.action not in view.poker.legal_actions
        ):
            raise ValueError("Expected a legal BetDecision")
        return decision
    if isinstance(decision, PassDecision):
        return decision
    if not isinstance(decision, MessageDecision):
        raise ValueError("Expected a MessageDecision or PassDecision")
    if not isinstance(decision.text, str) or not decision.text.strip():
        raise ValueError("A message must contain non-whitespace text")
    if len(decision.text) > view.max_message_chars:
        raise ValueError("Message exceeds the per-message limit or remaining hand budget")
    if decision.recipient is None:
        if not view.public_message_allowed:
            raise ValueError("Public messages are unavailable")
    elif (
        not isinstance(decision.recipient, str) or decision.recipient not in view.private_recipients
    ):
        raise ValueError("Private recipient is unavailable")
    return decision


async def _request(view: PlayerView, decide: Decider, timeout: float) -> Decision | SessionFailure:
    try:
        async with asyncio.timeout(timeout):
            candidate: object = await decide(view)
    except TimeoutError:
        kind, detail = FailureKind.TIMEOUT, "Decision timed out"
    except Exception as error:
        kind, detail = FailureKind.AGENT_ERROR, f"{type(error).__name__}: {error}"
    else:
        try:
            return _validate(view, candidate)
        except ValueError as error:
            kind, detail = FailureKind.INVALID_DECISION, str(error)
    return SessionFailure(
        kind, detail, view.phase, view.hand_index, view.round_index, view.player_id
    )


async def _communicate(state: SessionState, hand: PokerHand, decide: Decider) -> bool:
    state.phase = Phase.COMMUNICATION
    for round_index in range(state.config.communication_rounds):
        state.round_index = round_index
        # Freeze all observations before invoking any decision function.
        views = tuple(_view(state, hand, player) for player in PLAYER_IDS)
        tasks = [
            asyncio.create_task(_request(view, decide, state.config.decision_timeout_seconds))
            for view in views
        ]
        try:
            decisions = await asyncio.gather(*tasks)
        finally:
            # gather alone does not cancel siblings when one callback cancels itself.
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        pending = []
        for view, decision in zip(views, decisions, strict=True):
            if isinstance(decision, SessionFailure):
                if state.failure is None:
                    state.failure = decision
            elif isinstance(decision, MessageDecision):
                pending.append(
                    Message(view.player_id, decision.recipient, decision.text, round_index)
                )
        state.pending_messages = tuple(pending)
        if state.failure is not None:
            state.phase = Phase.FAILED
            return False
        # Charge and deliver only after the whole round has validated. Passes are private.
        for message in state.pending_messages:
            state.budgets[message.sender] -= len(message.text)
        state.messages += state.pending_messages
        state.pending_messages = ()
    state.round_index = None
    return True


async def _bet(state: SessionState, hand: PokerHand, decide: Decider) -> bool:
    state.phase = Phase.BETTING
    while not hand.terminal:
        seat = hand.current_player
        assert seat is not None
        state.current_player = state.seats[seat]
        decision = await _request(
            _view(state, hand, state.current_player), decide, state.config.decision_timeout_seconds
        )
        if isinstance(decision, SessionFailure):
            state.failure = decision
            state.phase = Phase.FAILED
            return False
        assert isinstance(decision, BetDecision)
        hand.apply(decision.action)
        state.poker_snapshot = hand.to_json()
    state.current_player = None
    return True


def _settle(state: SessionState, hand: PokerHand) -> None:
    state.phase = Phase.SETTLEMENT
    for seat, reward in enumerate(hand.returns()):
        state.rewards[state.seats[seat]] += reward
    state.phase = Phase.MEMORY_UPDATE
    for seat, player in enumerate(state.seats):
        memory = HandMemory(
            state.hand_index,
            state.seats,
            hand.view(seat),
            _visible_messages(state.messages, player),
        )
        state.histories[player] = (
            (state.histories[player] + (memory,))[-state.config.memory_hands :]
            if state.config.memory_hands
            else ()
        )
    state.completed_hands += 1


async def run_session(
    config: SessionConfig, schedule: DealSchedule, decide: Decider
) -> SessionState:
    """Run a fresh session; return completed/failed state, propagate cancellation.

    A schedule must match config.hands exactly. All persistent player memory is
    supplied in PlayerView; callers must use stateless or newly reset deciders.
    This runner performs no transport retries, model calls, or disk persistence.
    """
    if len(schedule.deals) != config.hands:
        raise ValueError("Schedule length must equal the configured hand count")
    state = SessionState(config, schedule)
    try:
        for hand_index, deal in enumerate(schedule.deals):
            state.phase = Phase.DEAL
            state.hand_index = hand_index
            state.round_index = None
            state.seats = schedule.seats_for_hand(hand_index)
            state.messages = ()
            state.pending_messages = ()
            budget = config.message_budget_chars if config.channel != Channel.NONE else 0
            state.budgets = dict.fromkeys(PLAYER_IDS, budget)
            hand = PokerHand(deal)
            state.poker_snapshot = hand.to_json()
            if config.channel != Channel.NONE and not await _communicate(state, hand, decide):
                return state
            if not await _bet(state, hand, decide):
                return state
            _settle(state, hand)
    except asyncio.CancelledError as error:
        state.failure = SessionFailure(
            FailureKind.INTERRUPTED,
            "Session cancelled",
            state.phase,
            state.hand_index,
            state.round_index,
            state.current_player,
        )
        state.phase = Phase.INTERRUPTED
        raise SessionInterrupted(state) from error
    state.phase = Phase.COMPLETE
    return state


async def passive_decider(view: PlayerView) -> Decision:
    """Scripted smoke-test policy: decline messages, check when possible, otherwise call."""
    if view.phase == Phase.COMMUNICATION:
        return PassDecision()
    return BetDecision(Action.CHECK if Action.CHECK in view.poker.legal_actions else Action.CALL)


def seeded_random_decider(seed: int) -> Decider:
    """A test policy with no mutable memory or hidden RNG cursor across decisions."""
    require_int(seed, "Agent seed")

    async def decide(view: PlayerView) -> Decision:
        rng = random.Random(
            f"{seed}:{view.player_id}:{view.hand_index}:{view.phase}:"
            f"{view.round_index}:{len(view.poker.history)}"
        )
        if view.phase == Phase.BETTING:
            return BetDecision(rng.choice(view.poker.legal_actions))
        text = f"Hello from {view.player_id}."
        if len(text) > view.max_message_chars or rng.choice((False, True)):
            return PassDecision()
        if view.public_message_allowed:
            return MessageDecision(text)
        if view.private_recipients:
            return MessageDecision(text, rng.choice(view.private_recipients))
        return PassDecision()

    return decide
