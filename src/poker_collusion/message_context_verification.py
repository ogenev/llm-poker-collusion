"""Verify the separate diagnostic against frozen fixtures and saved Inspect evidence."""

import json
import math
from pathlib import Path
from typing import Any, cast

from inspect_ai.event import ModelEvent
from inspect_ai.log import read_eval_log_async
from inspect_ai.model import ModelUsage

from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.message_context import MessageContextConfig
from poker_collusion.model_adapter import parse_response
from poker_collusion.model_log import read_model_log
from poker_collusion.prompts import render_prompt
from poker_collusion.records import BetDecision
from poker_collusion.serialization import canonical, digest
from poker_collusion.verification import _check_call, _require, _token_counts


def _rows(path: Path) -> list[dict[str, Any]]:
    lines = path.read_bytes().splitlines(keepends=True)
    _require(
        bool(lines) and all(line.endswith(b"\n") for line in lines), "Torn/empty evidence file"
    )
    return [json.loads(line) for line in lines]


def _event_record(event: ModelEvent) -> dict[str, Any]:
    record = event.model_dump(mode="json")
    # Inspect deduplicates message IDs in .eval files. Retain their full content.
    record["input"] = [
        {key: value for key, value in message.items() if key != "id"} for message in record["input"]
    ]
    return {
        key: record[key]
        for key in (
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
        )
    }


async def verify_context(
    directory: Path, *, config_type: type[MessageContextConfig] = MessageContextConfig
) -> dict[str, Any]:
    """No generation. Incomplete/corrupt evidence raises; a wrong answer cannot pass."""
    manifest = _rows(directory / "run.jsonl")
    _require(len(manifest) == 2, "Incomplete run manifest")
    start, end = manifest
    _require(
        start.get("kind") == f"{config_type.purpose}_run"
        and start.get("version") == 1
        and start.get("event") == "started"
        and end.get("event") == "ended"
        and end.get("summary") == "summary.json",
        "Invalid diagnostic manifest",
    )
    config = config_type.from_json(canonical(start["effective_config"]))
    requested = config_type.from_json(canonical(start["requested_config"]))
    mock = config.model.model.startswith("mockllm/")
    _require(start["mock"] == mock, "Mock flag differs from effective model")
    effective_data, requested_data = json.loads(config.to_json()), json.loads(requested.to_json())
    if mock:
        requested_data["model"]["settings"]["model"] = config.model.model
    _require(effective_data == requested_data, "Requested/effective settings differ")
    cases = config.cases()
    expected = [(rep, case) for rep in range(1, config.repetitions + 1) for case in cases]
    _require(start["cases"] == json.loads(canonical(cases)), "Frozen fixtures differ")
    plan = start["plan"]
    _require(
        plan["cases_sha256"] == digest(cases)
        and plan["config_sha256"] == digest(effective_data)
        and plan["maximum_decision_calls"] == len(expected),
        "Plan hash or workload differs",
    )
    summary_rows = _rows(directory / "summary.json")
    _require(len(summary_rows) == 1, "Expected one summary")
    summary = summary_rows[0]
    _require(
        summary["kind"] == f"{config.purpose}_summary"
        and summary["version"] == 1
        and summary["run_id"] == start["run_id"]
        and summary["mock"] == mock,
        "Summary identity differs",
    )
    audit = read_model_log(directory / "model.jsonl")
    _require(audit.status == "complete" and audit.session_id == start["run_id"], "Incomplete audit")
    header = audit.events[0].data
    _require(
        header.get("purpose") == config.purpose
        and header.get("model_config_sha256") == config.model.sha256
        and header.get("cases_sha256") == digest(cases),
        "Audit settings or fixture hash differ",
    )
    rows = _rows(directory / "results.jsonl")
    _require(
        len(rows) == 2 * len(expected) + 1 and rows[-1] == {"event": "ended", "incomplete": False},
        "Incomplete or extra probe results",
    )
    paths = sorted((directory / "inspect").glob("*.eval"))
    _require(len(paths) == 1 and len(summary["inspect_logs"]) == 1, "Expected one Inspect log")
    _require(paths[0].name == Path(summary["inspect_logs"][0]).name, "Inspect filename differs")
    log = await read_eval_log_async(str(paths[0]), resolve_attachments="full")
    _require(
        log.status == "success"
        and log.eval.model == config.model.model
        and len(log.samples or []) == 1,
        "Unsuccessful or unexpected Inspect evaluation",
    )
    sample = (log.samples or [])[0]
    _require(
        sample.error is None and sample.id == config.sample_id and sample.epoch == 1,
        "Unexpected/failed Inspect sample",
    )
    events = [event for event in sample.events if isinstance(event, ModelEvent)]
    starts = [event.data for event in audit.events if event.event == "call_started"]
    finishes = [event.data for event in audit.events if event.event == "call_finished"]
    _require(len(starts) == len(finishes) == len(events) == len(expected), "Call coverage differs")
    checker_config = ExperimentConfig(
        model=config.model, max_connections=1, cost_limit=config.cost_limit
    )
    issues: list[str] = []
    total_usage = ModelUsage()
    passed = 0
    costs = []
    probes = []
    for index, ((rep, case), began, ended, event) in enumerate(
        zip(expected, starts, finishes, events, strict=True)
    ):
        probe_start, probe = rows[2 * index : 2 * index + 2]
        _require(
            probe_start["event"] == "probe_started" and probe["event"] == "probe_finished",
            "Probe event order differs",
        )
        identity = {
            "case_id": case.case_id,
            "context": case.context,
            "repetition": rep,
            "expected_action": case.expected_action,
        }
        for key, value in identity.items():
            _require(probe_start[key] == probe[key] == value, "Probe fixture or order differs")
        _require(
            probe_start["request_id"]
            == probe["request_id"]
            == began["request_id"]
            == ended["request_id"],
            "Probe/model link differs",
        )
        prompt = render_prompt(
            case.view, config.model.instruction, response_format=config.model.response_format
        )
        _require(began["prompt"] == json.loads(canonical(prompt)), "Input differs from fixture")
        captured = ended["model_events"]
        _require(isinstance(captured, list) and len(captured) == 1, "Expected one captured event")
        assert isinstance(captured, list)
        _require(
            _event_record(ModelEvent.model_validate(captured[0])) == _event_record(event),
            "Inspect event differs from model journal",
        )
        call_issues = _check_call(began, ended, event, checker_config)
        if mock:
            call_issues = [
                issue
                for issue in call_issues
                if issue != "Raw provider request/response payload is missing"
            ]
        elif event.call is not None:
            raw = event.call.request
            if (
                raw.get("reasoning_effort") != "medium"
                or raw.get("max_completion_tokens") != config.model.max_tokens
                or raw.get("model") != config.model.model.partition("/")[2]
                or "temperature" in raw
                or raw.get("tools")
                or raw.get("n") != 1
            ):
                call_issues.append("Raw provider settings differ")
            if raw.get("messages") != [
                {"role": "developer", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ]:
                call_issues.append("Raw provider input differs from fixture")
            response = cast(dict[str, Any], event.call.response or {})
            choices = response.get("choices", [])
            if (
                response.get("model") != event.output.model
                or len(choices) != 1
                or choices[0].get("message", {}).get("content") != event.output.completion
            ):
                call_issues.append("Raw provider output differs from Inspect")
        issues.extend(f"Request {began['request_id']}: {issue}" for issue in call_issues)
        usage = event.output.usage
        _require(
            usage is not None and probe["usage"] == usage.model_dump(mode="json"),
            "Probe usage differs from Inspect",
        )
        assert usage is not None
        if not mock and event.call is not None:
            raw_usage = cast(dict[str, Any], event.call.response or {}).get("usage", {})
            if (
                raw_usage.get("total_tokens") != usage.total_tokens
                or raw_usage.get("completion_tokens") != usage.output_tokens
                or raw_usage.get("prompt_tokens") != usage.total_tokens - usage.output_tokens
            ):
                issues.append(f"Request {began['request_id']}: raw provider usage differs")
        total_usage += usage
        _require(usage.total_cost is not None, "Cost missing")
        rates = plan["pricing_per_million_tokens"]
        cost = (
            usage.input_tokens * rates["input"]
            + usage.output_tokens * rates["output"]
            + (usage.input_tokens_cache_read or 0) * rates["input_cache_read"]
            + (usage.input_tokens_cache_write or 0) * rates["input_cache_write"]
        ) / 1_000_000
        _require(math.isclose(cost, usage.total_cost or 0, abs_tol=1e-12), "Pricing differs")
        costs.append(cost)
        action = None
        try:
            decision = parse_response(
                event.output.completion, response_format=config.model.response_format
            )
            if (
                isinstance(decision, BetDecision)
                and decision.action in case.view.poker.legal_actions
            ):
                action = decision.action
        except ValueError:
            pass
        correct = action == case.expected_action and ended.get("response_error") is None
        _require(
            probe["action"] == action and probe["status"] == ("pass" if correct else "fail"),
            "Recorded decision differs from response",
        )
        passed += int(correct)
        probes.append(probe)
    failed = len(expected) - passed
    result = "fail" if failed else "pass"
    _require(
        summary["probes"] == probes
        and summary["result"] == end["result"] == result
        and summary["passed"] == passed
        and summary["failed"] == failed
        and summary["incomplete"] == 0
        and not summary["errors"]
        and summary["planned_calls"]
        == summary["attempted_calls"]
        == summary["usage_recorded_calls"]
        == len(expected)
        and summary["total_tokens"] == total_usage.total_tokens
        and math.isclose(summary["metered_cost"], sum(costs), abs_tol=1e-12)
        and summary[config.live_pass_key] == (not failed and not mock),
        "Summary does not reconcile",
    )
    _require(
        set(sample.model_usage) == {config.model.model}
        and _token_counts(sample.model_usage[config.model.model]) == _token_counts(total_usage),
        "Inspect aggregate usage differs",
    )
    return {
        "passed": not issues and not failed,
        "mock": mock,
        config.live_pass_key: not issues and not failed and not mock,
        "run_id": start["run_id"],
        "calls": len(expected),
        "correct": passed,
        **_token_counts(total_usage),
        "cost": sum(costs),
        "issues": issues,
    }
