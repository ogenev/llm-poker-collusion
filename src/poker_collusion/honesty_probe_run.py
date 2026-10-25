"""One bounded stage, fresh calls per saved view, and durable failure/usage evidence."""

import asyncio
import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from inspect_ai import Task, eval_async
from inspect_ai.dataset import Sample
from inspect_ai.model import Model, ModelCost, ModelInfo, get_model, set_model_info
from inspect_ai.solver import Generate, Solver, TaskState, solver

from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.experiment import provenance
from poker_collusion.honesty_probe import (
    INPUT_RESERVE,
    SCOPE,
    HonestyConfig,
    can_request,
    decision_record,
    honesty_plan,
    honesty_trials,
)
from poker_collusion.inspect_transport import configured_model, generation_config, inspect_generator
from poker_collusion.model_adapter import model_decider
from poker_collusion.model_log import ModelJournal
from poker_collusion.offline_model import offline_model
from poker_collusion.poker_basics import BasicsConfig
from poker_collusion.poker_basics_run import _response_evidence
from poker_collusion.records import SessionFailure
from poker_collusion.serialization import canonical
from poker_collusion.session_audit import SessionAudit


def prepare_honesty(config: HonestyConfig, *, offline: bool) -> tuple[HonestyConfig, Model]:
    if offline:
        set_model_info(
            "mockllm/model",
            ModelInfo(cost=ModelCost(input=0, output=0, input_cache_read=0, input_cache_write=0)),
        )
        effective = replace(config, model=replace(config.model, model="mockllm/model"))
        model = offline_model()
    else:
        if config.model.model != "openai/gpt-6-luna":
            raise ValueError("Live probe requires Luna; use --offline for mocks")
        effective = config
        honesty_plan(effective)
        model = configured_model(effective.model, 1)
    honesty_plan(effective)
    return effective, model


@solver
def honesty_solver(config: HonestyConfig, directory: str, run_id: str) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        model = get_model()
        if str(model) != config.model.model or state.epoch != 1:
            raise ValueError("Unexpected model or epoch")
        plan = honesty_plan(config)
        audit = SessionAudit()
        path = Path(directory)
        tokens, cost = 0, 0.0
        stop_reason: str | None = None
        pending: dict[str, Any] | None = None
        with (
            ModelJournal(path / "model.jsonl", run_id) as journal,
            DurableJsonl(path / "results.jsonl") as results,
        ):
            journal.emit(
                "model_audit_started",
                model_config=json.loads(config.model.to_json()),
                model_config_sha256=config.model.sha256,
                purpose="honesty_probe",
                sources_sha256=plan["sources_sha256"],
                trials_sha256=plan["trials_sha256"],
            )
            decide = model_decider(config.model, inspect_generator(model, journal, 1))
            try:
                async with asyncio.timeout(config.run_time_limit):
                    for trial in honesty_trials(config):
                        if not can_request(plan, tokens, cost):
                            stop_reason = "Insufficient reserved cost/token headroom"
                            break
                        request = audit.requested(trial.view)
                        pending = {
                            "request_id": request,
                            "trial_id": trial.trial_id,
                            "source_id": trial.source_id,
                            "condition": trial.condition,
                            "repetition": trial.repetition,
                        }
                        results.write({"event": "probe_started", **pending})
                        outcome = await audit.request(
                            request, trial.view, decide, config.decision_timeout_seconds
                        )
                        evidence = _response_evidence(
                            journal.path, BasicsConfig(model=config.model)
                        )
                        usage = evidence["usage"]
                        issues = list(evidence["evidence_issues"])
                        if usage is None:
                            issues.append("Usage unavailable; billing unknown")
                        else:
                            tokens += usage["total_tokens"]
                            if usage["total_cost"] is not None:
                                cost += usage["total_cost"]
                            if usage["total_tokens"] - usage["output_tokens"] > INPUT_RESERVE:
                                issues.append("Input token reservation exceeded")
                            if usage["output_tokens"] > config.model.max_tokens:
                                issues.append("Output token cap exceeded")
                            if tokens > config.token_limit or cost > config.cost_limit:
                                issues.append("Actual cost/token limit exceeded")
                        failed = isinstance(outcome, SessionFailure)
                        results.write(
                            {
                                "event": "probe_finished",
                                **pending,
                                "status": "incomplete" if failed or issues else "usable",
                                "decision": None if failed else decision_record(outcome),
                                "failure": json.loads(canonical(outcome)) if failed else None,
                                **evidence,
                                "evidence_issues": issues,
                            }
                        )
                        pending = None
                        if failed or issues:
                            stop_reason = "Response/schema/usage failure; no retry or replacement"
                            break
            except TimeoutError:
                stop_reason = "Whole-stage deadline exceeded"
                if pending is not None:
                    results.write(
                        {
                            "event": "probe_finished",
                            **pending,
                            "status": "incomplete",
                            "decision": None,
                            "failure": stop_reason,
                            **_response_evidence(journal.path, BasicsConfig(model=config.model)),
                        }
                    )
            journal.emit(
                "model_audit_ended", status="complete" if stop_reason is None else "interrupted"
            )
            results.write({"event": "ended", "stop_reason": stop_reason})
        state.completed = True
        return state

    return solve


async def run_honesty(
    config: HonestyConfig,
    output: Path,
    *,
    model: Model,
    requested: HonestyConfig | None = None,
    previous_run: Path | None = None,
    authorization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if str(model) != config.model.model:
        raise ValueError("Injected model differs")
    if config.model.model == "openai/gpt-6-luna" and not authorization:
        raise ValueError("Paid execution requires an explicit authorization record")
    gate = None
    if config.stage == "completion":
        from poker_collusion.honesty_probe_verify import completion_gate

        if previous_run is None:
            raise ValueError("Verified stage-one gate required before completion")
        gate = await completion_gate(previous_run, config)
    elif previous_run is not None:
        raise ValueError("Screen cannot consume a previous-stage gate")
    plan = honesty_plan(config)
    run_id = uuid4().hex
    mock = config.model.model.startswith("mockllm/")
    task = Task(
        name="honesty_probe",
        version=1,
        dataset=[Sample(id=f"honesty-{config.stage}", input="Selected communication probes")],
        solver=honesty_solver(config, str(output.resolve()), run_id),
        model=model,
        config=generation_config(config.model, 1),
        epochs=1,
        fail_on_error=False,
        token_limit=config.token_limit,
        cost_limit=config.cost_limit,
    )
    output.mkdir(parents=True, exist_ok=False)
    with DurableJsonl(output / "run.jsonl") as manifest:
        manifest.write(
            {
                "kind": "honesty_probe_run",
                "version": 1,
                "event": "started",
                "run_id": run_id,
                "mock": mock,
                "requested_config": json.loads((requested or config).to_json()),
                "effective_config": json.loads(config.to_json()),
                "trials": honesty_trials(config),
                "plan": plan,
                "provenance": provenance(),
                "previous_stage_gate": gate,
                "authorization": authorization,
            }
        )
        logs = await eval_async(
            task,
            log_dir=str(output / "inspect"),
            max_samples=1,
            max_connections=1,
            retry_on_error=0,
            log_model_api=True,
            log_samples=True,
            log_realtime=True,
            ctl_server=False,
            score=False,
            fail_on_error=False,
        )
        rows = (
            [json.loads(s) for s in (output / "results.jsonl").read_text().splitlines()]
            if (output / "results.jsonl").exists()
            else []
        )
        probes = [r for r in rows if r["event"] == "probe_finished"]
        errors = [s.error.message for log in logs for s in log.samples or [] if s.error]
        complete = (
            len(probes) == plan["maximum_calls"]
            and all(r["status"] == "usable" for r in probes)
            and rows[-1] == {"event": "ended", "stop_reason": None}
            and bool(logs)
            and all(log.status == "success" for log in logs)
            and not errors
        )
        usages = [r["usage"] for r in probes if r.get("usage") is not None]
        started = sum(r["event"] == "probe_started" for r in rows)
        summary = {
            "kind": "honesty_probe_summary",
            "version": 1,
            "run_id": run_id,
            "mock": mock,
            "stage": config.stage,
            "result": "complete" if complete else "incomplete",
            "planned_calls": plan["maximum_calls"],
            "attempted_calls": started,
            "usable_responses": sum(r["status"] == "usable" for r in probes),
            "usage_recorded_calls": len(usages),
            "unknown_usage_requests": started - len(usages),
            "unknown_cost_requests": started - sum(u["total_cost"] is not None for u in usages),
            "total_tokens": sum(u["total_tokens"] for u in usages),
            "metered_cost": math.fsum(u["total_cost"] or 0 for u in usages),
            "usage_note": "Estimates, not invoices; missing usage is unknown. Mocks are synthetic.",
            "errors": errors,
            "probes": probes,
            "inspect_logs": [log.location for log in logs],
            "human_annotations": 0,
            "human_primary_estimate": None,
            "coalition_inference": None,
            "scope": SCOPE,
        }
        manifest.write({"event": "ended", "summary": "summary.json", "result": summary["result"]})
    with DurableJsonl(output / "summary.json") as f:
        f.write(summary)
    return summary
