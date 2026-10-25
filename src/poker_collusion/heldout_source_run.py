"""Native game collection with a synchronous prospective selection sidecar."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from inspect_ai import eval_async
from inspect_ai.log import EvalLog, transcript
from inspect_ai.model import Model, ModelOutput, get_model
from inspect_ai.solver import Generate, Solver, TaskState, solver

from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.event_log import JsonlRecorder
from poker_collusion.experiment import (
    SessionFailedError,
    experiment_plan,
    poker_task,
    provenance,
    session_summary,
)
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.heldout_selection import POLICY_SHA256, SelectionRecorder, load_policy
from poker_collusion.inspect_transport import inspect_generator
from poker_collusion.model_adapter import model_decider
from poker_collusion.model_log import ModelJournal
from poker_collusion.prompts import Instruction
from poker_collusion.records import Channel, DealSchedule, Phase, SessionConfig, SessionState
from poker_collusion.serialization import canonical, config_record, digest
from poker_collusion.session import SessionInterrupted, run_session


def validate_source_config(config: ExperimentConfig) -> None:
    expected_session = SessionConfig(
        hands=36,
        communication_rounds=2,
        max_message_chars=500,
        message_budget_chars=1000,
        memory_hands=6,
        decision_timeout_seconds=90,
    )
    if (
        config.seeds != (600, 601, 602)
        or config.channels != (Channel.PRIVATE,)
        or config.session != expected_session
        or config.max_samples != 1
        or config.max_connections != 1
        or config.token_limit != 3_000_000
        or config.cost_limit != 0.35
        or config.session_time_limit != 5400
        or config.model.model not in ("openai/gpt-6-luna", "mockllm/model")
        or config.model.instruction != Instruction.NEUTRAL
        or config.model.reasoning_effort != "medium"
        or config.model.response_format != "strict_json_schema"
        or config.model.max_tokens != 4096
        or config.model.temperature is not None
    ):
        raise ValueError(
            "Cycle5 source collection must preserve the frozen game/model/budget settings"
        )


@solver
def heldout_source_solver(
    config: ExperimentConfig, output_dir: str, run_id: str, policy_path: str
) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # The shared sample transcript is an audit/display surface only.
        model = get_model()
        if str(model) != config.model.model or state.epoch != 1:
            raise ValueError("Expected the configured model and one epoch per session")
        channel = Channel(state.metadata["channel"])
        session_config = replace(config.session, channel=channel)
        schedule = DealSchedule.from_json(state.metadata["schedule"])
        session_id = uuid4().hex
        directory = Path(output_dir) / "sessions" / session_id
        session_path, model_path = directory / "session.jsonl", directory / "model.jsonl"
        references = {
            "run_id": run_id,
            "session_id": session_id,
            "session_log": str(session_path),
            "model_log": str(model_path),
        }
        state.metadata.update(references)
        state.metadata["session_status"] = "incomplete"
        transcript().info(
            {key: value for key, value in references.items()}, source="poker_artifacts"
        )
        with (
            JsonlRecorder(
                session_path,
                session_id=session_id,
                run_id=run_id,
                matched_block_id=state.metadata["matched_block_id"],
            ) as recorder,
            ModelJournal(model_path, session_id) as journal,
            SelectionRecorder(recorder, Path(policy_path), schedule.seed) as selection,
        ):
            journal.emit(
                "model_audit_started",
                run_id=run_id,
                matched_block_id=state.metadata["matched_block_id"],
                inspect_sample_id=state.sample_id,
                inspect_epoch=state.epoch,
                session_log="session.jsonl",
                model_config=json.loads(config.model.to_json()),
                model_config_sha256=config.model.sha256,
                session_config_sha256=digest(config_record(session_config)),
                schedule_sha256=digest(json.loads(schedule.to_json())),
                provenance=provenance(),
            )
            decide = model_decider(
                config.model, inspect_generator(model, journal, config.max_connections)
            )

            def finish(result: SessionState) -> None:
                summary = session_summary(result)
                journal.emit("model_audit_ended", **summary)
                state.metadata["session_status"] = result.phase.value
                state.metadata["session_result"] = summary
                state.output = ModelOutput.from_content("poker-session-summary", canonical(summary))

            try:
                async with asyncio.timeout(config.session_time_limit):
                    try:
                        result = await run_session(
                            session_config, schedule, decide, recorder=selection
                        )
                    except SessionInterrupted as error:
                        finish(error.state)
                        raise
                    finish(result)
            except TimeoutError as error:
                # Inspect handles bare TimeoutError specially, without a sample
                # error. Our deadline must remain an explicit failed attempt.
                raise SessionFailedError("Poker session exceeded its time limit") from error
        if result.phase != Phase.COMPLETE:
            raise SessionFailedError(canonical(session_summary(result)))
        state.completed = True
        return state

    return solve


async def run_heldout_source(
    config: ExperimentConfig,
    output: Path,
    *,
    model: Model,
    block_index: int,
    policy_path: Path,
    authorization: dict[str, Any] | None = None,
) -> list[EvalLog]:
    validate_source_config(config)
    load_policy(policy_path)
    if str(model) != config.model.model:
        raise ValueError("Injected model differs")
    if config.model.model == "openai/gpt-6-luna" and not authorization:
        raise ValueError("Explicit source-stage authorization required")
    config.selected_blocks(block_index)
    run_id = uuid4().hex
    task = poker_task(config, output, run_id, model, block_index=block_index)
    task.solver = heldout_source_solver(
        config, str(output.resolve()), run_id, str(policy_path.resolve())
    )
    output.mkdir(parents=True, exist_ok=False)
    with DurableJsonl(output / "run.jsonl") as manifest:
        manifest.write(
            {
                "kind": "experiment_run",
                "version": 1,
                "event": "started",
                "run_id": run_id,
                "config": json.loads(config.to_json()),
                "config_sha256": digest(json.loads(config.to_json())),
                "provenance": provenance(),
                "block_index": block_index,
                "plan": experiment_plan(config, block_index=block_index),
                "selection_policy_sha256": POLICY_SHA256,
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
        manifest.write(
            {
                "kind": "experiment_run",
                "version": 1,
                "event": "ended",
                "run_id": run_id,
                "inspect_logs": [
                    {"location": log.location, "status": log.status, "eval_id": log.eval.eval_id}
                    for log in logs
                ],
            }
        )
    return logs
