"""A separate bounded screen of sixty authored message-context decisions."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from inspect_ai import Task, eval_async
from inspect_ai.dataset import Sample
from inspect_ai.model import Model, get_model
from inspect_ai.solver import Generate, Solver, TaskState, solver

from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.experiment import provenance
from poker_collusion.inspect_transport import configured_model, generation_config, inspect_generator
from poker_collusion.message_context import MessageContextConfig, context_cases, context_plan
from poker_collusion.model_adapter import model_decider
from poker_collusion.model_log import ModelJournal
from poker_collusion.poker_basics import BASICS_MOCK_MODEL, basics_offline_model
from poker_collusion.poker_basics_run import _response_evidence
from poker_collusion.records import BetDecision, FailureKind, SessionFailure
from poker_collusion.serialization import digest
from poker_collusion.session_audit import SessionAudit


def prepare_context(
    config: MessageContextConfig, *, offline: bool
) -> tuple[MessageContextConfig, Model]:
    if offline:
        effective = replace(config, model=replace(config.model, model=BASICS_MOCK_MODEL))
        model = basics_offline_model()
    else:
        if config.model.model.startswith("mockllm/"):
            raise ValueError("Mock models require --offline")
        effective = config
        # Check pricing before initializing the live provider.
        context_plan(effective)
        model = configured_model(effective.model, 1)
    context_plan(effective)
    return effective, model


@solver
def context_solver(config: MessageContextConfig, directory: str, run_id: str) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        model = get_model()
        if str(model) != config.model.model or state.epoch != 1:
            raise ValueError("Expected the configured model and one epoch")
        audit = SessionAudit()
        pending: dict[str, Any] | None = None
        incomplete = False
        path = Path(directory)
        with (
            ModelJournal(path / "model.jsonl", session_id=run_id) as journal,
            DurableJsonl(path / "results.jsonl") as results,
        ):
            journal.emit(
                "model_audit_started",
                model_config=json.loads(config.model.to_json()),
                model_config_sha256=config.model.sha256,
                purpose="poker_message_context",
                cases_sha256=digest(context_cases()),
            )
            decide = model_decider(config.model, inspect_generator(model, journal, 1))
            try:
                async with asyncio.timeout(config.run_time_limit):
                    for repetition in range(1, config.repetitions + 1):
                        for case in context_cases():
                            request = audit.requested(case.view)
                            pending = {
                                "request_id": request,
                                "case_id": case.case_id,
                                "context": case.context,
                                "repetition": repetition,
                                "expected_action": case.expected_action,
                            }
                            results.write({"event": "probe_started", **pending})
                            outcome = await audit.request(
                                request, case.view, decide, config.decision_timeout_seconds
                            )
                            evidence = _response_evidence(journal.path, config)
                            if isinstance(outcome, SessionFailure):
                                status = (
                                    "fail"
                                    if outcome.kind == FailureKind.INVALID_DECISION
                                    else "incomplete"
                                )
                                action, error = None, f"{outcome.kind}: {outcome.detail}"
                            else:
                                assert isinstance(outcome, BetDecision)
                                action, error = outcome.action, None
                                status = "pass" if action == case.expected_action else "fail"
                            if evidence["evidence_issues"]:
                                status = "incomplete"
                            results.write(
                                {
                                    "event": "probe_finished",
                                    **pending,
                                    "status": status,
                                    "action": action,
                                    "error": error,
                                    **evidence,
                                }
                            )
                            pending = None
                            if status == "incomplete":
                                incomplete = True
                                break
                        if incomplete:
                            break
            except TimeoutError:
                incomplete = True
                if pending is not None:
                    results.write(
                        {
                            "event": "probe_finished",
                            **pending,
                            "status": "incomplete",
                            "action": None,
                            "error": "Whole-check deadline exceeded",
                            **_response_evidence(journal.path, config),
                        }
                    )
            journal.emit("model_audit_ended", status="interrupted" if incomplete else "complete")
            results.write({"event": "ended", "incomplete": incomplete})
        state.completed = True
        return state

    return solve


async def run_context(
    config: MessageContextConfig,
    output_dir: Path,
    *,
    model: Model,
    requested_config: MessageContextConfig | None = None,
) -> dict[str, Any]:
    if str(model) != config.model.model:
        raise ValueError("Injected model differs from qualification configuration")
    plan = context_plan(config)
    mock = config.model.model.startswith("mockllm/")
    run_id = uuid4().hex
    task = Task(
        name="poker_message_context",
        version=1,
        dataset=[
            Sample(id="message-context", input="Authored final-hand message-context action checks")
        ],
        solver=context_solver(config, str(output_dir.resolve()), run_id),
        model=model,
        config=generation_config(config.model, 1),
        epochs=1,
        fail_on_error=False,
        token_limit=config.token_limit,
        cost_limit=config.cost_limit,
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    with DurableJsonl(output_dir / "run.jsonl") as manifest:
        manifest.write(
            {
                "kind": "poker_message_context_run",
                "version": 1,
                "event": "started",
                "run_id": run_id,
                "mock": mock,
                "requested_config": json.loads((requested_config or config).to_json()),
                "effective_config": json.loads(config.to_json()),
                "cases": context_cases(),
                "plan": plan,
                "provenance": provenance(),
            }
        )
        logs = await eval_async(
            task,
            log_dir=str(output_dir / "inspect"),
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
        result_path = output_dir / "results.jsonl"
        rows = (
            [json.loads(line) for line in result_path.read_text().splitlines()]
            if result_path.exists()
            else []
        )
        probes = [row for row in rows if row["event"] == "probe_finished"]
        passed = sum(row["status"] == "pass" for row in probes)
        failed = sum(row["status"] == "fail" for row in probes)
        expected = len(context_cases()) * config.repetitions
        errors = [
            sample.error.message for log in logs for sample in log.samples or [] if sample.error
        ]
        complete = (
            passed + failed == expected
            and bool(rows)
            and rows[-1] == {"event": "ended", "incomplete": False}
            and bool(logs)
            and all(log.status == "success" for log in logs)
            and not errors
        )
        status = "incomplete" if not complete else "fail" if failed else "pass"
        usage = [row["usage"] for row in probes if row.get("usage") is not None]
        summary = {
            "kind": "poker_message_context_summary",
            "version": 1,
            "run_id": run_id,
            "mock": mock,
            "result": status,
            "live_message_context_check_passed": status == "pass" and not mock,
            "planned_calls": expected,
            "attempted_calls": sum(row["event"] == "probe_started" for row in rows),
            "passed": passed,
            "failed": failed,
            "incomplete": expected - passed - failed,
            "total_tokens": sum(item["total_tokens"] for item in usage),
            "metered_cost": sum(item["total_cost"] or 0 for item in usage),
            "usage_recorded_calls": len(usage),
            "usage_note": "Synthetic for mocks; partial usage may omit billed failed calls.",
            "errors": errors,
            "probes": probes,
            "inspect_logs": [log.location for log in logs],
            "scope": "Message-context screen only; not general competence or coalition evidence.",
        }
        manifest.write({"event": "ended", "summary": "summary.json", "result": status})
    with DurableJsonl(output_dir / "summary.json") as destination:
        destination.write(summary)
    return summary
