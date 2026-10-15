"""Verify recorded sessions through the ordinary runner, without decision callbacks."""

from __future__ import annotations

import asyncio
from pathlib import Path

from poker_collusion.event_log import Event, SessionLog, read_log
from poker_collusion.records import (
    DealSchedule,
    Decision,
    FailureKind,
    PlayerView,
    SessionState,
)
from poker_collusion.serialization import canonical, decode_candidate, event_payload, read_config
from poker_collusion.session import SessionInterrupted, _run_session
from poker_collusion.session_audit import (
    Decider,
    Outcome,
    SessionAudit,
    failure_for,
    resolve_candidate,
)


class ReplayError(ValueError):
    """An event, observation, decision, or resulting state differs from the runner."""


class IncompleteLogError(ReplayError):
    """A durable prefix can be inspected, but is not a finished session trajectory."""


class _ReplayAudit(SessionAudit):
    def __init__(self, log: SessionLog) -> None:
        super().__init__()
        self.events = log.events
        self.cursor = 0
        self.changed = asyncio.Event()

    def peek(self) -> Event:
        if self.cursor >= len(self.events):
            raise ReplayError("Runner continued beyond the recorded trajectory")
        return self.events[self.cursor]

    def emit(self, event: str, **data: object) -> None:
        expected = self.peek()
        if event != expected.event or canonical(event_payload(event, data)) != canonical(
            expected.data
        ):
            raise ReplayError(
                f"Event {expected.sequence} differs: expected {expected.event}, got {event}"
            )
        self.cursor += 1
        self.changed.set()
        self.changed = asyncio.Event()

    def decision_boundary(self) -> None:
        if self.peek().event == "session_interrupted":
            raise asyncio.CancelledError()

    async def request(
        self,
        request_id: int,
        view: PlayerView,
        decide: Decider,
        timeout: float,
    ) -> Outcome:
        # Replay arrival order as well as barrier effects, without wall-clock
        # sleeps or invoking a model. All round views already exist at this point.
        while True:
            event = self.peek()
            if event.event not in {"decision_returned", "decision_resolved", "request_cancelled"}:
                raise ReplayError(f"Missing outcome for request {request_id}")
            if event.data.get("request_id") == request_id:
                break
            if event.data.get("request_id") not in self.open_requests:
                raise ReplayError("Outcome refers to an inactive request")
            await self.changed.wait()
        if event.event == "request_cancelled":
            self.cancelled(request_id)
            # Finish replaying other responses in the interrupted round before
            # gather's cancellation cleanup can cancel their replay tasks.
            while self.open_requests:
                await self.changed.wait()
            raise asyncio.CancelledError()
        if event.event == "decision_returned":
            candidate = decode_candidate(event.data["candidate"])
            self.emit("decision_returned", request_id=request_id, candidate=candidate)
            outcome = resolve_candidate(view, candidate)
        else:
            # Provider exceptions/timeouts have no returned decision. Their
            # external detail is evidence; phase/player coordinates are checked.
            failure = event.data.get("failure")
            if not isinstance(failure, dict) or not isinstance(failure.get("detail"), str):
                raise ReplayError("Invalid recorded callback failure")
            kind = FailureKind(failure["kind"])
            if kind not in (FailureKind.AGENT_ERROR, FailureKind.TIMEOUT):
                raise ReplayError("Invalid decision lacks its returned response")
            if kind == FailureKind.TIMEOUT and failure["detail"] != "Decision timed out":
                raise ReplayError("Invalid timeout detail")
            outcome = failure_for(view, kind, failure["detail"])
        self.resolved(request_id, outcome)
        return outcome


async def _no_decisions(view: PlayerView) -> Decision:
    raise AssertionError("Replay must never invoke a decision callable")


async def replay_session(path: str | Path) -> SessionState:
    """Replay and verify a complete, failed, or cleanly interrupted journal.

    Interrupted sessions return their reconstructed INTERRUPTED state. Missing
    footers/torn tails raise IncompleteLogError; read_log exposes their prefix.
    This API verifies history, observations, effects, and the terminal record.
    It does not resume a session or make fresh decisions.
    """
    log = read_log(path)
    if log.status == "incomplete":
        raise IncompleteLogError("Journal has no committed terminal record; inspect with read_log")
    initial = log.events[0].data
    config = read_config(initial["config"])
    schedule = DealSchedule.from_json(canonical(initial["schedule"]))
    audit = _ReplayAudit(log)
    try:
        try:
            state = await _run_session(config, schedule, _no_decisions, audit)
        except SessionInterrupted as error:
            state = error.state
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ReplayError):
            raise
        raise ReplayError(f"Invalid replay payload at event {audit.cursor}: {error}") from error
    if audit.cursor != len(log.events):
        raise ReplayError("Unconsumed events after session termination")
    return state
