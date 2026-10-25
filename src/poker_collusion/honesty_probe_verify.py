"""Verify probe evidence against fixed inputs and raw provider records, without generation."""

import json
import math
from pathlib import Path
from typing import Any, cast

from inspect_ai.event import ModelEvent
from inspect_ai.log import read_eval_log_async
from inspect_ai.model import ModelCost, ModelInfo, ModelUsage, set_model_info

from poker_collusion.experiment import provenance
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.honesty_probe import (
    INPUT_RESERVE,
    HonestyConfig,
    decision_record,
    honesty_plan,
    honesty_trials,
)
from poker_collusion.message_context_verification import _event_record, _rows
from poker_collusion.model_adapter import parse_response
from poker_collusion.model_log import read_model_log
from poker_collusion.prompts import render_prompt
from poker_collusion.serialization import canonical, digest
from poker_collusion.session_audit import validate_decision
from poker_collusion.verification import _check_call, _require, _token_counts


async def verify_honesty(directory: Path) -> dict[str, Any]:
    manifest = _rows(directory / "run.jsonl")
    _require(len(manifest) == 2, "Incomplete run manifest; preserve partial attempt")
    start, end = manifest
    _require(
        start.get("kind") == "honesty_probe_run"
        and start.get("version") == 1
        and start.get("event") == "started"
        and end.get("event") == "ended",
        "Unexpected run manifest",
    )
    config = HonestyConfig.from_json(canonical(start["effective_config"]))
    requested = HonestyConfig.from_json(canonical(start["requested_config"]))
    requested_data = json.loads(requested.to_json())
    mock = config.model.model.startswith("mockllm/")
    if mock:
        set_model_info(
            "mockllm/model",
            ModelInfo(cost=ModelCost(input=0, output=0, input_cache_read=0, input_cache_write=0)),
        )
        requested_data["model"]["settings"]["model"] = config.model.model
    _require(
        requested_data == json.loads(config.to_json()) and mock == start["mock"],
        "Requested/effective model settings differ",
    )
    trials = honesty_trials(config)
    _require(start["trials"] == json.loads(canonical(trials)), "Frozen trials changed")
    plan = honesty_plan(config)
    _require(start["plan"] == json.loads(canonical(plan)), "Plan/pricing changed")
    summary_rows = _rows(directory / "summary.json")
    _require(len(summary_rows) == 1, "Expected exactly one summary")
    summary = summary_rows[0]
    gate = start.get("previous_stage_gate")
    if config.stage == "screen":
        _require(gate is None, "Screen must not consume a previous stage")
    else:
        _require(
            isinstance(gate, dict)
            and gate.get("passed") is True
            and gate.get("stage") == "screen"
            and gate.get("calls") == 12
            and gate.get("mock") == mock
            and gate.get("sources_sha256") == plan["sources_sha256"]
            and len(gate.get("previous_manifest_sha256", "")) == 64
            and len(gate.get("previous_summary_sha256", "")) == 64,
            "Invalid stage-one evidence gate; joint scoring also rechecks its exact content",
        )
    if not mock:
        _require(bool(start.get("authorization")), "Missing paid authorization record")
    _require(
        summary.get("kind") == "honesty_probe_summary" and summary.get("version") == 1,
        "Unexpected summary kind/version",
    )
    _require(
        summary["result"] == "complete" and end["result"] == "complete",
        "Incomplete probe attempt is not a continuation gate",
    )
    _require(
        summary["run_id"] == start["run_id"]
        and summary["mock"] == mock
        and summary["stage"] == config.stage,
        "Summary identity differs",
    )
    audit = read_model_log(directory / "model.jsonl")
    _require(audit.status == "complete" and audit.session_id == start["run_id"], "Incomplete audit")
    header = audit.events[0].data
    _require(
        header.get("purpose") == "honesty_probe"
        and header.get("model_config_sha256") == config.model.sha256
        and header.get("sources_sha256") == plan["sources_sha256"]
        and header.get("trials_sha256") == plan["trials_sha256"],
        "Audit provenance differs",
    )
    rows = _rows(directory / "results.jsonl")
    _require(
        len(rows) == 2 * len(trials) + 1 and rows[-1] == {"event": "ended", "stop_reason": None},
        "Incomplete/extra results",
    )
    paths = sorted((directory / "inspect").glob("*.eval"))
    _require(len(paths) == len(summary["inspect_logs"]) == 1, "Expected one Inspect log")
    _require(paths[0].name == Path(summary["inspect_logs"][0]).name, "Inspect path differs")
    log = await read_eval_log_async(str(paths[0]), resolve_attachments="full")
    _require(
        log.status == "success"
        and log.eval.model == config.model.model
        and len(log.samples or []) == 1,
        "Unexpected Inspect status/model/samples",
    )
    sample = (log.samples or [])[0]
    _require(
        sample.error is None and sample.id == f"honesty-{config.stage}" and sample.epoch == 1,
        "Unexpected sample/epoch",
    )
    events = [e for e in sample.events if isinstance(e, ModelEvent)]
    starts = [e.data for e in audit.events if e.event == "call_started"]
    finishes = [e.data for e in audit.events if e.event == "call_finished"]
    _require(len(starts) == len(finishes) == len(events) == len(trials), "Call coverage differs")
    check_config = ExperimentConfig(
        model=config.model, max_connections=1, cost_limit=config.cost_limit
    )
    usage_total = ModelUsage()
    costs: list[float] = []
    probes = []
    issues: list[str] = []
    for index, (trial, began, finished, event) in enumerate(
        zip(trials, starts, finishes, events, strict=True)
    ):
        before, result = rows[2 * index : 2 * index + 2]
        identity = {
            "trial_id": trial.trial_id,
            "source_id": trial.source_id,
            "condition": trial.condition,
            "repetition": trial.repetition,
            "request_id": index,
        }
        _require(before == {"event": "probe_started", **identity}, "Trial order/identity differs")
        _require(
            all(result[k] == v for k, v in identity.items())
            and result["event"] == "probe_finished"
            and result["status"] == "usable",
            "Unexpected response record",
        )
        _require(began["request_id"] == finished["request_id"] == index, "Call identity differs")
        prompt = render_prompt(trial.view, response_format=config.model.response_format)
        _require(began["prompt"] == json.loads(canonical(prompt)), "Probe input differs")
        captured = finished["model_events"]
        _require(
            isinstance(captured, list) and len(captured) == 1, "Captured event missing/duplicated"
        )
        assert isinstance(captured, list)
        _require(
            _event_record(ModelEvent.model_validate(captured[0])) == _event_record(event),
            "Inspect/provider evidence differs",
        )
        found = _check_call(began, finished, event, check_config)
        if mock:
            found = [x for x in found if x != "Raw provider request/response payload is missing"]
        elif event.call is not None:
            raw = event.call.request
            _require(
                raw.get("model") == "gpt-6-luna"
                and raw.get("reasoning_effort") == "medium"
                and raw.get("max_completion_tokens") == 4096
                and raw.get("n") == 1
                and "temperature" not in raw
                and not raw.get("tools"),
                "Raw settings differ",
            )
            _require(
                raw.get("messages")
                == [
                    {"role": "developer", "content": prompt.system},
                    {"role": "user", "content": prompt.user},
                ],
                "Raw provider input differs",
            )
            response = cast(dict[str, Any], event.call.response or {})
            choices = response.get("choices", [])
            _require(
                response.get("model") == event.output.model
                and len(choices) == 1
                and choices[0].get("message", {}).get("content") == event.output.completion,
                "Raw provider response differs",
            )
            raw_usage = response.get("usage", {})
            _require(event.output.usage is not None, "Provider usage missing")
            assert event.output.usage is not None
            _require(
                raw_usage.get("total_tokens") == event.output.usage.total_tokens
                and raw_usage.get("completion_tokens") == event.output.usage.output_tokens
                and raw_usage.get("prompt_tokens")
                == event.output.usage.total_tokens - event.output.usage.output_tokens,
                "Raw provider usage differs",
            )
        issues.extend(f"{trial.trial_id}: {x}" for x in found)
        decision = parse_response(
            event.output.completion, response_format=config.model.response_format
        )
        validate_decision(trial.view, decision)
        _require(
            result["decision"] == decision_record(decision)
            and result["failure"] is None
            and not result["evidence_issues"],
            "Decision/evidence differs",
        )
        usage = event.output.usage
        _require(usage is not None, "Usage missing")
        assert usage is not None
        _require(
            result["usage"] == usage.model_dump(mode="json") and usage.total_cost is not None,
            "Saved usage differs",
        )
        _require(
            0 < usage.total_tokens
            and 0 <= usage.total_tokens - usage.output_tokens <= INPUT_RESERVE
            and 0 <= (usage.reasoning_tokens or 0) <= usage.output_tokens <= 4096,
            "Token reservation/output cap exceeded",
        )
        _require(
            usage.total_tokens
            == sum(
                (
                    usage.input_tokens,
                    usage.input_tokens_cache_read or 0,
                    usage.input_tokens_cache_write or 0,
                    usage.output_tokens,
                )
            ),
            "Token components differ",
        )
        rates = plan["pricing_per_million_tokens"]
        cost = (
            usage.input_tokens * rates["input"]
            + usage.output_tokens * rates["output"]
            + (usage.input_tokens_cache_read or 0) * rates["input_cache_read"]
            + (usage.input_tokens_cache_write or 0) * rates["input_cache_write"]
        ) / 1e6
        _require(math.isclose(cost, usage.total_cost or 0, abs_tol=1e-12), "Pricing differs")
        # Reproduce the reservation gate immediately before each call.
        _require(
            usage_total.total_tokens + plan["tokens_reserved_per_call"] <= config.token_limit
            and math.fsum(costs) + plan["cost_reserved_per_call"] <= config.cost_limit,
            "Call started without reserved budget",
        )
        usage_total += usage
        costs.append(cost)
        probes.append(result)
    _require(
        summary["probes"] == probes
        and not summary["errors"]
        and summary["planned_calls"]
        == summary["attempted_calls"]
        == summary["usable_responses"]
        == summary["usage_recorded_calls"]
        == len(trials)
        and summary["unknown_usage_requests"] == 0
        and summary["unknown_cost_requests"] == 0
        and summary["total_tokens"] == usage_total.total_tokens <= config.token_limit
        and math.isclose(summary["metered_cost"], math.fsum(costs), abs_tol=1e-12)
        and summary["metered_cost"] <= config.cost_limit,
        "Summary/budget does not reconcile",
    )
    _require(
        set(sample.model_usage) == {config.model.model}
        and _token_counts(sample.model_usage[config.model.model]) == _token_counts(usage_total),
        "Inspect aggregate usage differs",
    )
    _require(
        summary["human_annotations"] == 0
        and summary["human_primary_estimate"] is None
        and summary["coalition_inference"] is None,
        "Invented scientific/human label",
    )
    return {
        "passed": not issues,
        "mock": mock,
        "stage": config.stage,
        "calls": len(trials),
        "run_id": start["run_id"],
        "issues": issues,
        "known_cost": math.fsum(costs),
        **_token_counts(usage_total),
        "sources_sha256": plan["sources_sha256"],
        "trials_sha256": plan["trials_sha256"],
        "human_annotations": 0,
        "paid_verification_calls": 0,
        "scope": (
            "Execution/input/usage integrity only; truthful behavior is not an execution gate."
        ),
    }


async def completion_gate(directory: Path, config: HonestyConfig) -> dict[str, Any]:
    checked = await verify_honesty(directory)
    start = _rows(directory / "run.jsonl")[0]
    old = HonestyConfig.from_json(canonical(start["effective_config"]))
    _require(
        checked["passed"] and old.stage == "screen" and old.model == config.model,
        "Successful matching screen required",
    )
    _require(start["provenance"] == provenance(), "Runtime changed since stage one")
    return {
        **checked,
        "previous_run": str(directory),
        "previous_manifest_sha256": digest(_rows(directory / "run.jsonl")),
        "previous_summary_sha256": digest(_rows(directory / "summary.json")),
    }
