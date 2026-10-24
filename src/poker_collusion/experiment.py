"""One Inspect sample per poker session, with matched schedules and durable evidence."""

import asyncio
import hashlib
import json
import platform
from dataclasses import asdict, replace
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from inspect_ai import Task, eval_async
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog, transcript
from inspect_ai.model import Model, ModelOutput, get_model, get_model_info
from inspect_ai.solver import Generate, Solver, TaskState, solver

from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.event_log import JsonlRecorder
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.inspect_transport import configured_model, generation_config, inspect_generator
from poker_collusion.model_adapter import model_decider
from poker_collusion.model_log import ModelJournal
from poker_collusion.poker import generate_schedule
from poker_collusion.records import Channel, DealSchedule, Phase, SessionState
from poker_collusion.serialization import canonical, config_record, digest
from poker_collusion.session import SessionInterrupted, run_session


class SessionFailedError(RuntimeError):
    """Inspect should expose a failed poker session as a sample error."""


def experiment_plan(
    config: ExperimentConfig, *, block_index: int | None = None
) -> dict[str, object]:
    """Describe the planned workload and stopping thresholds without model calls."""
    blocks = config.selected_blocks(block_index)
    info = get_model_info(config.model.model)
    pricing = info.cost.model_dump() if info is not None and info.cost is not None else None
    if config.cost_limit is not None and pricing is None:
        raise ValueError("A cost limit requires Inspect pricing for the selected model")
    sessions = len(blocks) * len(config.channels)
    # Three-player Kuhn has at most five betting actions per hand.
    calls = (
        len(blocks)
        * config.session.hands
        * sum(
            5 + (0 if channel == Channel.NONE else 3 * config.session.communication_rounds)
            for channel in config.channels
        )
    )
    return {
        "model": config.model.model,
        "config_sha256": digest(json.loads(config.to_json())),
        "sessions": sessions,
        "selected_block_indices": list(blocks),
        "hands_per_session": config.session.hands,
        "maximum_decision_calls": calls,
        "max_samples": config.max_samples,
        "max_connections": config.max_connections,
        "token_limit_per_session": config.token_limit,
        "cost_limit_per_session": config.cost_limit,
        "sum_of_cost_thresholds": sessions * config.cost_limit if config.cost_limit else None,
        "session_time_limit": config.session_time_limit,
        "pricing_per_million_tokens": pricing,
        "limits_note": (
            "Usage limits are checked after responses and may overshoot; not a billing cap."
        ),
    }


def provenance() -> dict[str, object]:
    root = Path(__file__).parent
    sources = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.suffix in {".py", ".txt"}
    }
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            name: version(name)
            for name in ("llm-poker-collusion", "inspect-ai", "open-spiel", "openai")
        },
        "source_sha256": digest(sources),
    }


def session_summary(state: SessionState) -> dict[str, object]:
    return {
        "status": state.phase,
        "completed_hands": state.completed_hands,
        "rewards": state.rewards,
        "failure": asdict(state.failure) if state.failure else None,
    }


@solver
def poker_solver(config: ExperimentConfig, output_dir: str, run_id: str) -> Solver:
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
                            session_config, schedule, decide, recorder=recorder
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


def poker_task(
    config: ExperimentConfig,
    output_dir: Path,
    run_id: str,
    model: Model | None = None,
    *,
    block_index: int | None = None,
) -> Task:
    if model is not None and str(model) != config.model.model:
        raise ValueError("Injected model differs from experiment configuration")
    experiment_plan(config, block_index=block_index)
    samples = []
    for index in config.selected_blocks(block_index):
        seed = config.seeds[index]
        schedule = generate_schedule(seed, config.session.hands, initial_rotation=index % 3)
        block_id = f"{run_id}-block-{index}"
        for channel in config.channels:
            samples.append(
                Sample(
                    id=f"block-{index}-{channel.value}",
                    input="Poker session; player inputs are constructed separately.",
                    metadata={
                        "matched_block_id": block_id,
                        "channel": channel.value,
                        "schedule": schedule.to_json(),
                    },
                )
            )
    return Task(
        name="poker_sessions",
        version=1,
        dataset=samples,
        solver=poker_solver(config, str(output_dir.resolve()), run_id),
        model=model
        if model is not None
        else configured_model(config.model, config.max_connections),
        config=generation_config(config.model, config.max_connections),
        epochs=1,
        fail_on_error=False,
        token_limit=config.token_limit,
        cost_limit=config.cost_limit,
        metadata={
            "run_id": run_id,
            "instruction": config.model.instruction.value,
            "experiment_config": json.loads(config.to_json()),
            "block_index": block_index,
        },
    )


async def run_experiment(
    config: ExperimentConfig,
    output_dir: Path,
    *,
    model: Model | None = None,
    block_index: int | None = None,
) -> list[EvalLog]:
    """Run a fresh attempt; output directories are exclusive and never resumed."""
    run_id = uuid4().hex
    task = poker_task(config, output_dir, run_id, model, block_index=block_index)
    output_dir.mkdir(parents=True, exist_ok=False)
    with DurableJsonl(output_dir / "run.jsonl") as manifest:
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
            }
        )
        logs = await eval_async(
            task,
            log_dir=str(output_dir / "inspect"),
            max_samples=config.max_samples,
            max_connections=config.max_connections,
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
