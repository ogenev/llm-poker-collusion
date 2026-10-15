"""Offline verification of a complete Inspect run and its linked game evidence."""

import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalSample, read_eval_log_async
from inspect_ai.model import ModelUsage

from poker_collusion.event_log import read_log
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import _read_object, parse_response
from poker_collusion.model_log import verify_model_links
from poker_collusion.poker import generate_schedule
from poker_collusion.records import Channel
from poker_collusion.replay import replay_session
from poker_collusion.serialization import canonical, config_record, decode_candidate, digest


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def _token_counts(usage: ModelUsage) -> dict[str, int]:
    # Inspect separates cache reads/writes from uncached input. Reasoning is
    # already included in output_tokens. Missing optional counts mean zero.
    return {
        "input_tokens": usage.input_tokens,
        "input_tokens_cache_read": usage.input_tokens_cache_read or 0,
        "input_tokens_cache_write": usage.input_tokens_cache_write or 0,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": usage.reasoning_tokens or 0,
        "total_tokens": usage.total_tokens,
    }


def _manifest(directory: Path) -> tuple[dict[str, Any], dict[str, Any], ExperimentConfig]:
    lines = (directory / "run.jsonl").read_bytes().splitlines(keepends=True)
    _require(
        len(lines) == 2 and all(line.endswith(b"\n") for line in lines), "Incomplete run manifest"
    )
    start, end = (cast(dict[str, Any], _read_object(line.decode())) for line in lines)
    for row, event in ((start, "started"), (end, "ended")):
        _require(
            row.get("kind") == "experiment_run"
            and type(row.get("version")) is int
            and row["version"] == 1
            and row.get("event") == event,
            "Invalid run manifest envelope",
        )
    _require(bool(start.get("run_id")) and start["run_id"] == end.get("run_id"), "Run ID mismatch")
    config = ExperimentConfig.from_json(canonical(start.get("config")))
    _require(
        start.get("config_sha256") == digest(start["config"]), "Run configuration hash mismatch"
    )
    return start, end, config


def _check_call(
    started: dict[str, Any],
    finished: dict[str, Any],
    event: ModelEvent,
    config: ExperimentConfig,
) -> list[str]:
    issues = []
    if finished["status"] != "returned" or finished.get("response_error") or event.error:
        issues.append("Model call did not return a usable response")
    prompt = started["prompt"]
    if [(message.role, message.text) for message in event.input] != [
        ("system", prompt["system"]),
        ("user", prompt["user"]),
    ] or event.tools:
        issues.append("Inspect model input differs from the permitted prompt")
    if event.model != config.model.model or event.span_id != started["span_id"]:
        issues.append("Inspect model/span differs from the request")
    if event.output.model not in (config.model.model, config.model.model.partition("/")[2]):
        issues.append("Returned model identifier differs; resolve aliases before qualification")
    settings = event.config
    if (
        settings.max_tokens != config.model.max_tokens
        or settings.temperature != config.model.temperature
        or settings.max_connections != config.max_connections
        or settings.max_retries != 0
        or settings.cache is not False
        or event.cache is not None
        or event.retries not in (None, 0)
    ):
        issues.append("Generation settings, retries, or caching differ from configuration")
    if finished["status"] == "returned" and finished.get("output") != event.output.model_dump(
        mode="json"
    ):
        issues.append("Saved model output differs from Inspect output")
    if event.call is None or not event.call.request or not event.call.response:
        issues.append("Raw provider request/response payload is missing")
    usage = event.output.usage
    if usage is None or usage.total_tokens <= 0:
        issues.append("Token usage is missing or invalid")
    else:
        counts = _token_counts(usage)
        if (
            min(counts.values()) < 0
            or usage.total_tokens
            != usage.input_tokens
            + counts["input_tokens_cache_read"]
            + counts["input_tokens_cache_write"]
            + usage.output_tokens
            or counts["reasoning_tokens"] > usage.output_tokens
        ):
            issues.append("Token usage components are invalid or do not reconcile with the total")
    if config.cost_limit is not None and (
        usage is None
        or usage.total_cost is None
        or not math.isfinite(usage.total_cost)
        or usage.total_cost < 0
    ):
        issues.append("Metered cost is missing or invalid")
    return issues


async def _session_report(
    directory: Path,
    sample: EvalSample,
    config: ExperimentConfig,
    run_id: str,
    block: int,
    channel: Channel,
) -> dict[str, Any]:
    session_id = sample.metadata.get("session_id")
    _require(
        isinstance(session_id, str)
        and session_id not in (".", "..")
        and Path(session_id).name == session_id,
        "Invalid session ID",
    )
    assert isinstance(session_id, str)
    root = directory / "sessions" / session_id
    model_path, game_path = root / "model.jsonl", root / "session.jsonl"
    audit = verify_model_links(model_path, game_path)
    game = read_log(game_path)
    state = await replay_session(game_path)
    header = audit.events[0].data
    _require(
        audit.session_id == session_id
        and header.get("run_id") == run_id == sample.metadata.get("run_id")
        and header.get("inspect_sample_id") == sample.id
        and header.get("inspect_epoch") == sample.epoch == 1
        and header.get("matched_block_id")
        == sample.metadata.get("matched_block_id")
        == f"{run_id}-block-{block}"
        and sample.metadata.get("channel") == channel.value,
        "Sample and model audit identifiers differ",
    )
    schedule = json.loads(
        generate_schedule(config.seeds[block], config.session.hands, block % 3).to_json()
    )
    _require(
        header.get("model_config_sha256") == config.model.sha256
        and game.events[0].data["config"] == config_record(replace(config.session, channel=channel))
        and game.events[0].data["schedule"] == schedule,
        "Session differs from the planned matched block",
    )
    issues = []
    if sample.error is not None or audit.status != "complete":
        issues.append("Session did not complete successfully")
    _require(
        sample.metadata.get("session_status") == audit.status,
        "Inspect session status differs from journals",
    )
    starts = {
        e.data["request_id"]: cast(dict[str, Any], e.data)
        for e in audit.events
        if e.event == "call_started"
    }
    finishes = [cast(dict[str, Any], e.data) for e in audit.events if e.event == "call_finished"]
    candidates = {
        e.data["request_id"]: e.data["candidate"]
        for e in game.events
        if e.event == "decision_returned"
    }
    model_events = [event for event in sample.events if isinstance(event, ModelEvent)]
    by_uuid = {event.uuid: event for event in model_events}
    seen: set[str] = set()
    raw_payloads = 0
    total_usage = ModelUsage()
    usage_by_model: dict[str, ModelUsage] = {}
    costs: list[float] = []
    models: set[str] = set()
    for call in finishes:
        request = call["request_id"]
        recorded = call["model_events"]
        if len(recorded) != 1:
            issues.append(f"Request {request}: expected one Inspect model event")
            continue
        captured = ModelEvent.model_validate(recorded[0])
        event = by_uuid.get(captured.uuid)
        _require(
            event is not None and isinstance(captured.uuid, str) and captured.uuid not in seen,
            "Missing or duplicate Inspect event link",
        )
        assert event is not None and isinstance(event.uuid, str)
        seen.add(event.uuid)
        # Compare serialized evidence, excluding Inspect's transient private
        # Pydantic attributes and event completion timing.
        captured_data = captured.model_dump(mode="json")
        event_data = event.model_dump(mode="json")
        # Inspect pools repeated messages when writing .eval files and may
        # substitute message IDs. Compare every serialized field except that ID.
        for data in (captured_data, event_data):
            data["input"] = [
                {key: value for key, value in message.items() if key != "id"}
                for message in data["input"]
            ]
        for field in (
            "span_id",
            "model",
            "input",
            "tools",
            "config",
            "output",
            "call",
            "cache",
            "retries",
            "error",
        ):
            _require(
                captured_data[field] == event_data[field],
                f"Inspect {field} differs from model journal",
            )
        issues.extend(
            f"Request {request}: {issue}"
            for issue in _check_call(starts[request], call, event, config)
        )
        if call["status"] == "returned" and call.get("response_error") is None:
            try:
                decision = parse_response(event.output.completion)
            except ValueError:
                issues.append(f"Request {request}: malformed response")
            else:
                _require(
                    request in candidates and decode_candidate(candidates[request]) == decision,
                    "Raw output differs from session decision",
                )
        if event.call is not None and event.call.request and event.call.response:
            raw_payloads += 1
        models.add(event.output.model)
        usage = event.output.usage
        if usage is not None:
            total_usage += usage
            usage_by_model[event.model] = usage_by_model.get(event.model, ModelUsage()) + usage
            if usage.total_cost is not None:
                costs.append(usage.total_cost)
    _require(len(seen) == len(model_events) == len(by_uuid), "Unlinked Inspect model calls")
    _require(
        {model: _token_counts(usage) for model, usage in usage_by_model.items()}
        == {model: _token_counts(usage) for model, usage in sample.model_usage.items()},
        "Inspect usage differs from model events",
    )
    return {
        "sample_id": sample.id,
        "session_id": session_id,
        "channel": channel.value,
        "status": audit.status,
        "completed_hands": state.completed_hands,
        "calls": len(finishes),
        "raw_payloads": raw_payloads,
        "returned_models": sorted(models),
        **_token_counts(total_usage),
        "call_seconds": sum(call["elapsed_seconds"] for call in finishes),
        "cost": sum(costs) if len(costs) == len(finishes) else None,
        "issues": issues,
    }


async def verify_run(directory: Path) -> dict[str, Any]:
    """Verify saved artifacts without contacting a provider or rerunning decisions.

    Corrupt/missing evidence raises ValueError or OSError. Valid failed attempts
    remain in the report and make passed=False. This is a compatibility check,
    not a competence score or proof that a remote provider honored its contract.
    """
    start, end, config = _manifest(directory)
    references = end.get("inspect_logs")
    _require(
        isinstance(references, list) and len(references) == 1, "Expected one Inspect evaluation"
    )
    assert isinstance(references, list)
    reference = references[0]
    path = directory / "inspect" / Path(reference["location"]).name
    _require(
        set((directory / "inspect").glob("*.eval")) == {path},
        "Unexpected or missing Inspect log files",
    )
    log = await read_eval_log_async(str(path), resolve_attachments="full")
    metadata = log.eval.metadata or {}
    _require(
        log.eval.eval_id == reference["eval_id"]
        and log.status == reference["status"]
        and log.eval.model == config.model.model
        and metadata.get("run_id") == start["run_id"]
        and metadata.get("experiment_config") == start["config"],
        "Inspect evaluation differs from run manifest",
    )
    expected = {
        f"block-{block}-{channel.value}": (block, channel)
        for block in range(len(config.seeds))
        for channel in config.channels
    }
    samples = {sample.id: sample for sample in log.samples or []}
    _require(
        set(samples) == set(expected) and len(samples) == len(log.samples or []),
        "Missing, duplicate, or unexpected samples",
    )
    sessions = [
        await _session_report(directory, samples[key], config, start["run_id"], *values)
        for key, values in expected.items()
    ]
    _require(
        {path.name for path in (directory / "sessions").iterdir()}
        == {session["session_id"] for session in sessions},
        "Unexpected or missing session directories",
    )
    return {
        "kind": "run_verification",
        "version": 1,
        "run_id": start["run_id"],
        "model": config.model.model,
        "mock": config.model.model.startswith("mockllm/"),
        "passed": log.status == "success" and all(not session["issues"] for session in sessions),
        "inspect_status": log.status,
        "sessions": sessions,
        "scope": (
            "Game replay, artifact links, model inputs/settings, raw output parsing, and recorded "
            "usage; raw provider payload semantics require review."
        ),
    }
