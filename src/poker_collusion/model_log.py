"""Durable model-call evidence, separate from the deterministic game journal."""

import json
from pathlib import Path

from poker_collusion.durable_jsonl import DurableJsonl, RecordingError
from poker_collusion.event_log import Event, SessionLog, read_log
from poker_collusion.model_adapter import ModelConfig, _read_object
from poker_collusion.serialization import canonical, digest

MODEL_EVENTS = {"model_audit_started", "call_started", "call_finished", "model_audit_ended"}


class ModelJournal(DurableJsonl):
    def __init__(self, path: Path, session_id: str) -> None:
        super().__init__(path)
        self.session_id = session_id
        self._ended = False

    def emit(self, event: str, **data: object) -> None:
        if self._ended:
            raise RecordingError("Model journal is finished")
        if event not in MODEL_EVENTS or (self.count == 0) != (event == "model_audit_started"):
            raise ValueError("Expected one model_audit_started followed by known model events")
        self.write(
            {
                "kind": "model_event",
                "version": 1,
                "session_id": self.session_id,
                "sequence": self.count,
                "event": event,
                "data": data,
            }
        )
        self._ended = event == "model_audit_ended"


def read_model_log(path: str | Path) -> SessionLog:
    """Inspect committed records; a missing footer or torn tail is incomplete."""
    events: list[Event] = []
    requests: set[int] = set()
    finished: set[int] = set()
    session_id: str | None = None
    status = "incomplete"
    trailing = 0
    with Path(path).open("rb") as source:
        for line in source:
            if status != "incomplete":
                raise ValueError("Data follows the model audit footer")
            if not line.endswith(b"\n"):
                trailing = len(line)
                break
            row = _read_object(line.decode("utf-8"))
            if (
                set(row) != {"kind", "version", "session_id", "sequence", "event", "data"}
                or row["kind"] != "model_event"
                or type(row["version"]) is not int
                or row["version"] != 1
                or type(row["sequence"]) is not int
                or row["sequence"] != len(events)
            ):
                raise ValueError("Invalid model event envelope or version")
            identifier = row["session_id"]
            if not isinstance(identifier, str) or not identifier:
                raise ValueError("Invalid model audit session identifier")
            if not events:
                session_id = identifier
            if identifier != session_id:
                raise ValueError("Mixed model audit sessions")
            name, data = row["event"], row["data"]
            if not isinstance(name, str) or name not in MODEL_EVENTS or not isinstance(data, dict):
                raise ValueError("Unknown model event or invalid payload")
            if (not events) != (name == "model_audit_started"):
                raise ValueError("Expected exactly one initial model audit record")
            if name == "model_audit_started":
                config = ModelConfig.from_json(canonical(data.get("model_config")))
                if data.get("model_config_sha256") != config.sha256:
                    raise ValueError("Model configuration hash mismatch")
            elif name in {"call_started", "call_finished"}:
                request = data.get("request_id")
                if type(request) is not int or request < 0:
                    raise ValueError("Invalid model request identifier")
                if data.get("span_id") != f"{session_id}-request-{request}":
                    raise ValueError("Invalid model request span")
                if name == "call_started":
                    if request in requests:
                        raise ValueError("Duplicate model request")
                    prompt = data.get("prompt")
                    if (
                        not isinstance(prompt, dict)
                        or set(prompt) != {"system", "user"}
                        or not all(isinstance(value, str) for value in prompt.values())
                    ):
                        raise ValueError("Invalid model prompt")
                    if data.get("prompt_sha256") != digest(prompt):
                        raise ValueError("Prompt hash mismatch")
                    if data.get("requested_model") != config.model:
                        raise ValueError("Requested model differs from configuration")
                    requests.add(request)
                else:
                    if request not in requests or request in finished:
                        raise ValueError("Unexpected model response")
                    if data.get("status") not in ("returned", "error", "cancelled"):
                        raise ValueError("Invalid model response status")
                    if not isinstance(data.get("model_events"), list) or (
                        data["status"] == "returned" and not isinstance(data.get("output"), dict)
                    ):
                        raise ValueError("Missing model response evidence")
                    finished.add(request)
            else:
                if requests != finished:
                    raise ValueError("Unfinished model calls in terminal audit")
                if data.get("status") not in ("complete", "failed", "interrupted"):
                    raise ValueError("Invalid model audit status")
                status = data["status"]
            events.append(Event(len(events), name, data))
    return SessionLog(session_id, tuple(events), status, trailing)


def verify_model_links(model_path: str | Path, session_path: str | Path) -> SessionLog:
    """Verify IDs, observations, and terminal status across the two journals.

    This checks artifact linkage. Use replay_session separately to verify game
    effects; it deliberately does not depend on provider payload formats.
    """
    audit, game = read_model_log(model_path), read_log(session_path)
    if audit.status == "incomplete" or game.status == "incomplete":
        raise ValueError("Both journals require committed terminal records")
    if audit.session_id != game.session_id or audit.status != game.status:
        raise ValueError("Session identifiers or statuses differ between journals")
    header = audit.events[0].data
    if (
        header.get("session_config_sha256") != game.events[0].data["config_sha256"]
        or header.get("schedule_sha256") != game.events[0].data["schedule_sha256"]
    ):
        raise ValueError("Model audit references different session inputs")
    terminal = game.events[-1].data["state"]
    assert isinstance(terminal, dict)  # Checked by read_log.
    if any(
        audit.events[-1].data.get(field) != terminal.get(field)
        for field in ("completed_hands", "rewards", "failure")
    ):
        raise ValueError("Terminal summaries differ between journals")
    requests = {
        e.data["request_id"]: e.data["view"] for e in game.events if e.event == "decision_requested"
    }
    calls = {e.data["request_id"]: e.data for e in audit.events if e.event == "call_started"}
    responses = {e.data["request_id"]: e.data for e in audit.events if e.event == "call_finished"}
    for request, call in calls.items():
        prompt = call.get("prompt")
        if request not in requests or not isinstance(prompt, dict):
            raise ValueError("Model call has no matching session request")
        if json.loads(prompt["user"]) != requests[request]:
            raise ValueError("Model prompt differs from permitted player view")
        if call.get("span_id") != responses[request].get("span_id"):
            raise ValueError("Model response span differs from its request")
    for event in game.events:
        if (
            event.event in {"decision_returned", "decision_resolved"}
            and event.data["request_id"] not in calls
        ):
            raise ValueError("Session decision has no model-call evidence")
    return audit
