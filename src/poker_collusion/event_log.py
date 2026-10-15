"""Append-only, fsync-backed session journals and strict prefix inspection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self
from uuid import uuid4

from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.durable_jsonl import RecordingError as RecordingError
from poker_collusion.records import DealSchedule, Phase
from poker_collusion.serialization import canonical, digest, event_payload, read_config

EVENT_TYPES = {
    "session_started",
    "phase_changed",
    "hand_dealt",
    "decision_requested",
    "decision_returned",
    "decision_resolved",
    "request_cancelled",
    "messages_pending",
    "messages_delivered",
    "action_applied",
    "rewards_settled",
    "memory_updated",
    "session_failed",
    "session_interrupted",
    "session_ended",
}
TERMINAL_PHASES = {Phase.COMPLETE, Phase.FAILED, Phase.INTERRUPTED}


class EventSink(Protocol):
    """Consume each event synchronously, capturing mutable state before returning.

    Payloads contain protocol dataclasses and live state mappings. A sink must
    serialize or copy them now, rather than retain references for later use.
    """

    def emit(self, event: str, data: dict[str, object]) -> None: ...


class JsonlRecorder:
    """One exclusive file per attempt, including reruns. Use as a context manager.

    The full audit contains hidden cards and private messages. Files are created
    with mode 0600. Each line is flushed and fsynced before emit returns.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
        matched_block_id: str | None = None,
    ) -> None:
        self.session_id = session_id if session_id is not None else uuid4().hex
        for value in (self.session_id, run_id, matched_block_id):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError("Audit identifiers must be nonempty strings")
        self.metadata = {"run_id": run_id, "matched_block_id": matched_block_id}
        self.path = Path(path)
        self._writer = DurableJsonl(path)
        self._finished = False

    def emit(self, event: str, data: dict[str, object]) -> None:
        if self._finished:
            raise RecordingError("Recorder is closed, finished, or failed")
        if event not in EVENT_TYPES or (self._writer.count == 0) != (event == "session_started"):
            raise ValueError("Expected one session_started event followed by known events")
        envelope = {
            "kind": "session_event",
            "version": 1,
            "session_id": self.session_id,
            "sequence": self._writer.count,
            "event": event,
            "data": event_payload(event, data),
            "metadata": self.metadata,
        }
        self._writer.write(envelope)
        self._finished = event == "session_ended"

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._writer.__exit__(exc_type, exc, traceback)


@dataclass(frozen=True)
class Event:
    sequence: int
    event: str
    data: dict[str, object]


@dataclass(frozen=True)
class SessionLog:
    session_id: str | None
    events: tuple[Event, ...]
    status: str  # complete, failed, interrupted, or incomplete (no committed footer)
    trailing_bytes: int = 0


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    raise ValueError(f"Non-finite JSON number: {value}")


def read_log(path: str | Path) -> SessionLog:
    """Read committed newline-terminated records; never repair or alter the source.

    A torn final line is retained as a byte count, not interpreted as an event.
    Malformed committed lines, gaps, duplicate results, and unknown schemas fail.
    Replay additionally verifies the session's semantics through the runner.
    """
    events: list[Event] = []
    session_id = None
    metadata = None
    status = "incomplete"
    trailing_bytes = 0
    requests: dict[int, str] = {}
    with Path(path).open("rb") as source:
        for line in source:
            if status != "incomplete":
                raise ValueError("Data follows the terminal session record")
            if not line.endswith(b"\n"):
                trailing_bytes = len(line)
                break
            try:
                row = json.loads(
                    line, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
                )
                if not isinstance(row, dict) or set(row) != {
                    "kind",
                    "version",
                    "session_id",
                    "sequence",
                    "event",
                    "data",
                    "metadata",
                }:
                    raise ValueError("Invalid event envelope")
                if (
                    row["kind"] != "session_event"
                    or type(row["version"]) is not int
                    or row["version"] != 1
                ):
                    raise ValueError("Unsupported event schema")
                if type(row["sequence"]) is not int or row["sequence"] != len(events):
                    raise ValueError("Noncontiguous event sequence")
                if not isinstance(row["session_id"], str) or not row["session_id"].strip():
                    raise ValueError("Invalid session identifier")
                if not events:
                    session_id, metadata = row["session_id"], row["metadata"]
                    if not isinstance(metadata, dict) or set(metadata) != {
                        "run_id",
                        "matched_block_id",
                    }:
                        raise ValueError("Invalid audit metadata")
                    if any(
                        v is not None and (not isinstance(v, str) or not v.strip())
                        for v in metadata.values()
                    ):
                        raise ValueError("Invalid audit identifiers")
                if row["session_id"] != session_id or row["metadata"] != metadata:
                    raise ValueError("Mixed session identifiers or metadata")
                name, data = row["event"], row["data"]
                if (
                    not isinstance(name, str)
                    or name not in EVENT_TYPES
                    or not isinstance(data, dict)
                ):
                    raise ValueError("Unknown event or invalid event data")
                if (not events) != (name == "session_started"):
                    raise ValueError("Expected exactly one initial session record")
                if not events:
                    _check_start(data)
                _check_request(name, data, requests)
                if name == "session_ended":
                    if any(stage != "done" for stage in requests.values()):
                        raise ValueError("Unfinished requests in terminal session")
                    state = data["state"]
                    if (
                        not isinstance(state, dict)
                        or state.get("kind") != "session_state"
                        or type(state.get("version")) is not int
                        or state["version"] != 1
                    ):
                        raise ValueError("Unsupported session state schema")
                    phase = state.get("phase")
                    if not isinstance(phase, str) or phase not in TERMINAL_PHASES:
                        raise ValueError("Invalid terminal phase")
                    status = phase
                events.append(Event(len(events), name, data))
            except (KeyError, TypeError, UnicodeError, ValueError) as error:
                raise ValueError(f"Invalid journal line {len(events) + 1}: {error}") from error
    return SessionLog(session_id, tuple(events), status, trailing_bytes)


def _check_start(data: dict[str, object]) -> None:
    if set(data) != {"protocol_version", "config", "schedule", "config_sha256", "schedule_sha256"}:
        raise ValueError("Invalid initial session fields")
    if type(data["protocol_version"]) is not int or data["protocol_version"] != 1:
        raise ValueError("Unsupported session protocol")
    config = read_config(data["config"])
    schedule = DealSchedule.from_json(canonical(data["schedule"]))
    if config.hands != len(schedule.deals):
        raise ValueError("Schedule length differs from configuration")
    if data["config_sha256"] != digest(data["config"]) or data["schedule_sha256"] != digest(
        data["schedule"]
    ):
        raise ValueError("Configuration or schedule hash mismatch")


def _check_request(name: str, data: dict[str, object], requests: dict[int, str]) -> None:
    if name not in {
        "decision_requested",
        "decision_returned",
        "decision_resolved",
        "request_cancelled",
    }:
        if any(stage != "done" for stage in requests.values()):
            raise ValueError("Engine effect before all requests have finished")
        return
    request_id = data.get("request_id")
    if type(request_id) is not int:
        raise ValueError("Invalid request identifier")
    if name == "decision_requested":
        if request_id != len(requests):
            raise ValueError("Duplicate or noncontiguous request identifier")
        requests[request_id] = "requested"
    elif name == "decision_returned":
        if requests.get(request_id) != "requested":
            raise ValueError("Unexpected returned decision")
        requests[request_id] = "returned"
    else:
        if requests.get(request_id) not in ("requested", "returned"):
            raise ValueError("Unexpected request resolution")
        requests[request_id] = "done"
