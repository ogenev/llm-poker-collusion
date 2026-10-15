"""Versioned audit serialization. Never deserialize executable Python objects."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields, is_dataclass
from typing import cast

from poker_collusion.records import (
    Action,
    BetDecision,
    Channel,
    DealSchedule,
    MessageDecision,
    PassDecision,
    SessionConfig,
    SessionState,
)


def canonical(value: object) -> str:
    def default(item: object) -> object:
        if is_dataclass(item) and not isinstance(item, type):
            return asdict(item)
        raise TypeError(f"Unsupported audit value: {type(item).__name__}")

    return json.dumps(
        value,
        default=default,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    )


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def object_record(value: object) -> dict[str, object]:
    return cast(dict[str, object], json.loads(canonical(value)))


def config_record(config: SessionConfig) -> dict[str, object]:
    return {"kind": "session_config", "version": 1, **asdict(config)}


def read_config(value: object) -> SessionConfig:
    if not isinstance(value, dict) or set(value) != {
        "kind",
        "version",
        *(field.name for field in fields(SessionConfig)),
    }:
        raise ValueError("Invalid session configuration fields")
    if (
        value["kind"] != "session_config"
        or type(value["version"]) is not int
        or value["version"] != 1
    ):
        raise ValueError("Unsupported session configuration schema")
    data = {key: item for key, item in value.items() if key not in ("kind", "version")}
    data["channel"] = Channel(data["channel"])
    return SessionConfig(**data)


def state_record(state: SessionState) -> dict[str, object]:
    return {"kind": "session_state", "version": 1, **asdict(state)}


def event_payload(event: str, data: dict[str, object]) -> dict[str, object]:
    """Prepare the wire representation only at a synchronous recording boundary."""
    if event == "session_started":
        config = config_record(cast(SessionConfig, data["config"]))
        schedule = {
            "kind": "deal_schedule",
            "version": 1,
            **asdict(cast(DealSchedule, data["schedule"])),
        }
        return {
            "protocol_version": 1,
            "config": config,
            "schedule": schedule,
            "config_sha256": digest(config),
            "schedule_sha256": digest(schedule),
        }
    if event == "session_ended":
        return {"state": state_record(cast(SessionState, data["state"]))}
    if event == "decision_returned":
        return {**data, "candidate": encode_candidate(data["candidate"])}
    if event == "decision_resolved" and data["decision"] is not None:
        return {**data, "decision": encode_candidate(data["decision"])}
    return data


@dataclass(frozen=True)
class OpaqueResponse:
    """Diagnostic substitute for an unsupported, necessarily invalid response."""

    class_name: str
    representation: str


def encode_candidate(value: object, ancestors: tuple[int, ...] = ()) -> dict[str, object]:
    """Preserve runtime types, including invalid enum strings and malformed fields.

    Valid decisions and ordinary Python/JSON containers round-trip exactly.
    Unsupported objects, cycles, and nesting beyond 16 levels retain diagnostics,
    never pickle payloads. Valid protocol decisions need at most two levels.
    """
    if type(value) is int:
        try:
            str(value)  # Honor Python's integer-to-string limit before JSON encoding.
        except ValueError:
            return _diagnostic(value)
    if value is None or type(value) in (bool, int, str):
        return {"type": type(value).__name__, "value": value}
    if type(value) is float:
        return {"type": "float", "value": repr(value)}
    if isinstance(value, Action):
        return {"type": "Action", "value": value.value}
    if len(ancestors) < 16 and id(value) not in ancestors:
        parents = (*ancestors, id(value))
        if type(value) in (PassDecision, MessageDecision, BetDecision):
            assert isinstance(value, (PassDecision, MessageDecision, BetDecision))
            return {
                "type": type(value).__name__,
                "fields": {
                    field.name: encode_candidate(getattr(value, field.name), parents)
                    for field in fields(value)
                },
            }
        if type(value) in (list, tuple):
            assert isinstance(value, (list, tuple))
            return {
                "type": type(value).__name__,
                "items": [encode_candidate(item, parents) for item in value],
            }
        if type(value) is dict:
            return {
                "type": "dict",
                "items": [
                    [encode_candidate(key, parents), encode_candidate(item, parents)]
                    for key, item in value.items()
                ],
            }
    return _diagnostic(value)


def _diagnostic(value: object) -> dict[str, object]:
    if isinstance(value, OpaqueResponse):
        name, representation = value.class_name, value.representation
    else:
        name = f"{type(value).__module__}.{type(value).__qualname__}"
        try:
            representation = repr(value)
        except Exception:
            representation = "<repr unavailable>"
    return {"type": "unsupported", "class": name, "repr": representation}


def decode_candidate(value: object) -> object:
    try:
        return _decode_candidate(value)
    except (AttributeError, KeyError, TypeError, ValueError, RecursionError) as error:
        raise ValueError("Invalid candidate record") from error


def _decode_candidate(value: object) -> object:
    if not isinstance(value, dict):
        raise ValueError("Invalid candidate record")
    kind = value.get("type")
    if kind in ("NoneType", "bool", "int", "str"):
        result = value["value"]
    elif kind == "float":
        result = float(value["value"])
    elif kind == "Action":
        result = Action(value["value"])
    elif kind in ("PassDecision", "MessageDecision", "BetDecision"):
        cls = {
            "PassDecision": PassDecision,
            "MessageDecision": MessageDecision,
            "BetDecision": BetDecision,
        }[kind]
        result = cls(**{key: decode_candidate(item) for key, item in value["fields"].items()})
    elif kind in ("list", "tuple"):
        items = [decode_candidate(item) for item in value["items"]]
        result = tuple(items) if kind == "tuple" else items
    elif kind == "dict":
        result = {decode_candidate(key): decode_candidate(item) for key, item in value["items"]}
    elif kind == "unsupported":
        result = OpaqueResponse(value["class"], value["repr"])
    else:
        raise ValueError("Unknown candidate type")
    if canonical(encode_candidate(result)) != canonical(value):
        raise ValueError("Invalid candidate fields or types")
    return result
