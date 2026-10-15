"""Repeated hands with private observations and barrier-delivered communication."""

from __future__ import annotations

import asyncio
import random
from dataclasses import replace

from poker_collusion.event_log import EventSink
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
from poker_collusion.session_audit import Decider as Decider
from poker_collusion.session_audit import SessionAudit


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


async def _communicate(
    state: SessionState, hand: PokerHand, decide: Decider, audit: SessionAudit
) -> bool:
    audit.phase(state, Phase.COMMUNICATION)
    for round_index in range(state.config.communication_rounds):
        state.round_index = round_index
        # Freeze all observations before invoking any decision function.
        views = tuple(_view(state, hand, player) for player in PLAYER_IDS)
        requests = tuple(audit.requested(view) for view in views)
        tasks = [
            asyncio.create_task(
                audit.request(request, view, decide, state.config.decision_timeout_seconds)
            )
            for request, view in zip(requests, views, strict=True)
        ]
        try:
            decisions = await asyncio.gather(*tasks)
        finally:
            # gather alone does not cancel siblings when one callback cancels itself.
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            # A task cancelled before its coroutine starts cannot log itself.
            for request, task in zip(requests, tasks, strict=True):
                if task.cancelled():
                    audit.cancelled(request)
        audit.decision_boundary()
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
        audit.emit("messages_pending", messages=state.pending_messages)
        if state.failure is not None:
            audit.emit("session_failed", failure=state.failure)
            audit.phase(state, Phase.FAILED)
            return False
        # Charge and deliver only after the whole round has validated. Passes are private.
        for message in state.pending_messages:
            state.budgets[message.sender] -= len(message.text)
        state.messages += state.pending_messages
        audit.emit("messages_delivered", messages=state.pending_messages, budgets=state.budgets)
        state.pending_messages = ()
    state.round_index = None
    return True


async def _bet(state: SessionState, hand: PokerHand, decide: Decider, audit: SessionAudit) -> bool:
    audit.phase(state, Phase.BETTING)
    while not hand.terminal:
        seat = hand.current_player
        assert seat is not None
        state.current_player = state.seats[seat]
        view = _view(state, hand, state.current_player)
        decision = await audit.request(
            audit.requested(view), view, decide, state.config.decision_timeout_seconds
        )
        audit.decision_boundary()
        if isinstance(decision, SessionFailure):
            state.failure = decision
            audit.emit("session_failed", failure=state.failure)
            audit.phase(state, Phase.FAILED)
            return False
        assert isinstance(decision, BetDecision)
        hand.apply(decision.action)
        state.poker_snapshot = hand.to_json()
        audit.emit(
            "action_applied",
            player_id=state.current_player,
            action=decision.action,
            poker_snapshot=state.poker_snapshot,
        )
    state.current_player = None
    return True


def _settle(state: SessionState, hand: PokerHand, audit: SessionAudit) -> None:
    audit.phase(state, Phase.SETTLEMENT)
    for seat, reward in enumerate(hand.returns()):
        state.rewards[state.seats[seat]] += reward
    audit.emit("rewards_settled", returns=hand.returns(), rewards=state.rewards)
    audit.phase(state, Phase.MEMORY_UPDATE)
    memories = {}
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
        memories[player] = memory
    state.completed_hands += 1
    audit.emit(
        "memory_updated",
        memories=memories,
        histories=state.histories,
        completed_hands=state.completed_hands,
    )


async def run_session(
    config: SessionConfig,
    schedule: DealSchedule,
    decide: Decider,
    *,
    recorder: EventSink | None = None,
) -> SessionState:
    """Run a fresh session; return completed/failed state, propagate cancellation.

    A schedule must match config.hands exactly. All persistent player memory is
    supplied in PlayerView; callers must use stateless or newly reset deciders.
    Pass a JsonlRecorder for durable audit events. Persistence errors propagate
    and stop execution. This runner performs no transport retries or model calls.
    """
    return await _run_session(config, schedule, decide, SessionAudit(recorder))


async def _run_session(
    config: SessionConfig, schedule: DealSchedule, decide: Decider, audit: SessionAudit
) -> SessionState:
    if len(schedule.deals) != config.hands:
        raise ValueError("Schedule length must equal the configured hand count")
    state = SessionState(config, schedule)
    audit.emit("session_started", config=config, schedule=schedule)
    try:
        for hand_index, deal in enumerate(schedule.deals):
            state.hand_index = hand_index
            state.round_index = None
            audit.phase(state, Phase.DEAL)
            state.seats = schedule.seats_for_hand(hand_index)
            state.messages = ()
            state.pending_messages = ()
            budget = config.message_budget_chars if config.channel != Channel.NONE else 0
            state.budgets = dict.fromkeys(PLAYER_IDS, budget)
            hand = PokerHand(deal)
            state.poker_snapshot = hand.to_json()
            audit.emit(
                "hand_dealt",
                hand_index=hand_index,
                seats=state.seats,
                poker_snapshot=state.poker_snapshot,
                budgets=state.budgets,
            )
            if config.channel != Channel.NONE and not await _communicate(
                state, hand, decide, audit
            ):
                audit.finish(state)
                return state
            if not await _bet(state, hand, decide, audit):
                audit.finish(state)
                return state
            _settle(state, hand, audit)
    except asyncio.CancelledError as error:
        state.failure = SessionFailure(
            FailureKind.INTERRUPTED,
            "Session cancelled",
            state.phase,
            state.hand_index,
            state.round_index,
            state.current_player,
        )
        audit.emit("session_interrupted", failure=state.failure)
        audit.phase(state, Phase.INTERRUPTED)
        audit.finish(state)
        raise SessionInterrupted(state) from error
    audit.phase(state, Phase.COMPLETE)
    audit.finish(state)
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
