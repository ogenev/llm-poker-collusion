"""Decision validation and audit hooks shared by live execution and replay."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from poker_collusion.event_log import EventSink, RecordingError
from poker_collusion.records import (
    Action,
    BetDecision,
    Decision,
    DecisionParseError,
    FailureKind,
    MessageDecision,
    PassDecision,
    Phase,
    PlayerView,
    SessionFailure,
    SessionState,
)

type Decider = Callable[[PlayerView], Awaitable[Decision]]
type Outcome = Decision | SessionFailure

_active_request: ContextVar[int | None] = ContextVar("poker_request_id", default=None)


def current_request_id() -> int:
    """Trusted audit context, never part of the player's observation."""
    request_id = _active_request.get()
    if request_id is None:
        raise RuntimeError("Model calls must occur inside a session decision request")
    return request_id


def validate_decision(view: PlayerView, decision: object) -> Decision:
    # Only the protocol's exact immutable records can cross this boundary.
    # Arbitrary subclasses cannot be faithfully serialized without loading code.
    if type(decision) not in (PassDecision, MessageDecision, BetDecision):
        raise ValueError(
            "Expected a legal BetDecision"
            if view.phase == Phase.BETTING
            else "Expected a MessageDecision or PassDecision"
        )
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
    if type(decision.text) is not str or not decision.text.strip():
        raise ValueError("A message must contain non-whitespace text")
    if len(decision.text) > view.max_message_chars:
        raise ValueError("Message exceeds the per-message limit or remaining hand budget")
    if decision.recipient is None:
        if not view.public_message_allowed:
            raise ValueError("Public messages are unavailable")
    elif type(decision.recipient) is not str or decision.recipient not in view.private_recipients:
        raise ValueError("Private recipient is unavailable")
    return decision


def failure_for(view: PlayerView, kind: FailureKind, detail: str) -> SessionFailure:
    return SessionFailure(
        kind, detail, view.phase, view.hand_index, view.round_index, view.player_id
    )


def resolve_candidate(view: PlayerView, candidate: object) -> Outcome:
    try:
        return validate_decision(view, candidate)
    except ValueError as error:
        return failure_for(view, FailureKind.INVALID_DECISION, str(error))


class SessionAudit:
    def __init__(self, sink: EventSink | None = None) -> None:
        self.sink = sink
        self.next_request = 0
        self.open_requests: set[int] = set()

    def emit(self, event: str, **data: object) -> None:
        if self.sink is not None:
            self.sink.emit(event, data)

    def phase(self, state: SessionState, phase: Phase) -> None:
        state.phase = phase
        self.emit(
            "phase_changed",
            phase=phase,
            hand_index=state.hand_index,
            round_index=state.round_index,
            current_player=state.current_player,
        )

    def requested(self, view: PlayerView) -> int:
        request_id = self.next_request
        self.next_request += 1
        self.emit("decision_requested", request_id=request_id, view=view)
        self.open_requests.add(request_id)
        return request_id

    def resolved(self, request_id: int, outcome: Outcome) -> None:
        self.emit(
            "decision_resolved",
            request_id=request_id,
            decision=None if isinstance(outcome, SessionFailure) else outcome,
            failure=outcome if isinstance(outcome, SessionFailure) else None,
        )
        self.open_requests.remove(request_id)

    def cancelled(self, request_id: int) -> None:
        if request_id in self.open_requests:
            self.emit("request_cancelled", request_id=request_id)
            self.open_requests.remove(request_id)

    def decision_boundary(self) -> None:
        """Replay may reproduce cancellation after responses but before effects."""

    async def request(
        self,
        request_id: int,
        view: PlayerView,
        decide: Decider,
        timeout: float,
    ) -> Outcome:
        # Persistence sits outside the callback exception handler: disk errors
        # must abort execution, never become an agent failure or a default action.
        try:
            async with asyncio.timeout(timeout):
                token = _active_request.set(request_id)
                try:
                    candidate: object = await decide(view)
                finally:
                    _active_request.reset(token)
        except RecordingError:
            # Model-call persistence happens inside the callback; it has the
            # same stop-on-disk-error guarantee as the session journal.
            raise
        except DecisionParseError as error:
            # A raw string is never a protocol decision. Preserve malformed model
            # text using the existing candidate format and validation/replay path.
            outcome: Outcome = resolve_candidate(view, error.response)
            self.emit("decision_returned", request_id=request_id, candidate=error.response)
        except TimeoutError:
            outcome = failure_for(view, FailureKind.TIMEOUT, "Decision timed out")
        except asyncio.CancelledError:
            self.cancelled(request_id)
            raise
        except Exception as error:
            outcome = failure_for(view, FailureKind.AGENT_ERROR, f"{type(error).__name__}: {error}")
        else:
            outcome = resolve_candidate(view, candidate)
            self.emit("decision_returned", request_id=request_id, candidate=candidate)
        self.resolved(request_id, outcome)
        return outcome

    def finish(self, state: SessionState) -> None:
        self.emit("session_ended", state=state)
