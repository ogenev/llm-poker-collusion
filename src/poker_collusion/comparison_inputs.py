"""Load saved Inspect evidence, retaining planned attempts with missing artifacts."""

import hashlib
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalLog, read_eval_log_async

from poker_collusion.analysis import analyze_session
from poker_collusion.analysis_records import SessionAnalysis
from poker_collusion.comparison_manifest import RunSelection
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import _read_object
from poker_collusion.model_log import read_model_log
from poker_collusion.records import Channel, DealSchedule
from poker_collusion.serialization import canonical, config_record, digest
from poker_collusion.verification import _require, verify_saved_sample


class InputSnapshot:
    """Hash exact inputs, including absence, and detect changes during analysis."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.files: dict[Path, str | None] = {}
        self.inventories: dict[Path, tuple[str, ...]] = {}

    def track(self, path: Path) -> bool:
        # Keep the reference path: resolving symlinks here could miss a retargeted input.
        path = Path(os.path.abspath(path))
        value = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if path in self.files and self.files[path] != value:
            raise ValueError("Comparison input changed while being read")
        self.files[path] = value
        return value is not None

    def inventory(self, directory: Path) -> None:
        self.inventories[directory] = tuple(sorted(p.name for p in directory.glob("*")))

    def finish(self) -> list[dict[str, str | None]]:
        for path in list(self.files):
            self.track(path)
        for path, expected in self.inventories.items():
            _require(
                tuple(sorted(p.name for p in path.glob("*"))) == expected, "Run inventory changed"
            )
        return [
            {"path": os.path.relpath(path, self.base), "sha256": value}
            for path, value in sorted(self.files.items())
        ]


@dataclass(frozen=True)
class ComparisonSession:
    run_id: str
    block_id: str
    sample_id: str
    channel: Channel
    seed: int
    analysis: SessionAnalysis | None
    issues: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonRun:
    run_id: str
    config: ExperimentConfig
    provenance: dict[str, Any]
    inspect_status: str | None
    sessions: tuple[ComparisonSession, ...]
    unlinked_session_directories: tuple[str, ...]


async def _index(
    directory: Path, snapshot: InputSnapshot
) -> tuple[dict[str, Any], ExperimentConfig, EvalLog | None]:
    path = directory / "run.jsonl"
    snapshot.track(path)
    lines = path.read_bytes().splitlines(keepends=True)
    _require(bool(lines) and lines[0].endswith(b"\n"), "Missing committed run header")
    rows = [_read_object(line.decode()) for line in lines if line.endswith(b"\n")]
    _require(1 <= len(rows) <= 2 and len(lines) <= 2, "Invalid run manifest length")
    start = rows[0]
    for row, event in zip(rows, ("started", "ended"), strict=False):
        _require(
            row.get("kind") == "experiment_run"
            and type(row.get("version")) is int
            and row["version"] == 1
            and row.get("event") == event
            and row.get("run_id") == start.get("run_id"),
            "Invalid run manifest envelope",
        )
    _require(isinstance(start.get("run_id"), str) and bool(start["run_id"]), "Invalid run ID")
    config = ExperimentConfig.from_json(canonical(start.get("config")))
    _require(
        start.get("config_sha256") == digest(start["config"]), "Run configuration hash mismatch"
    )
    _require(isinstance(start.get("provenance"), dict), "Missing run provenance")
    snapshot.inventory(directory / "inspect")
    if len(rows) == 1:
        return start, config, None
    references = rows[1].get("inspect_logs")
    _require(
        isinstance(references, list) and len(references) == 1, "Expected one Inspect evaluation"
    )
    assert isinstance(references, list)
    reference = references[0]
    _require(
        isinstance(reference, dict) and isinstance(reference.get("location"), str),
        "Invalid Inspect reference",
    )
    path = directory / "inspect" / Path(reference["location"]).name
    _require(set((directory / "inspect").glob("*.eval")) <= {path}, "Unexpected Inspect log")
    if not snapshot.track(path):
        return start, config, None
    log = await read_eval_log_async(str(path), resolve_attachments="full")
    metadata = log.eval.metadata or {}
    _require(
        log.eval.eval_id == reference.get("eval_id")
        and log.status == reference.get("status")
        and log.eval.model == config.model.model
        and metadata.get("run_id") == start["run_id"]
        and metadata.get("experiment_config") == start["config"],
        "Inspect evaluation differs from run manifest",
    )
    return start, config, log


async def load_run(selection: RunSelection, snapshot: InputSnapshot) -> ComparisonRun:
    directory = selection.directory
    start, config, log = await _index(directory, snapshot)
    run_id = start["run_id"]
    expected = {
        f"block-{block}-{channel.value}": (block, channel)
        for block in range(len(config.seeds))
        for channel in config.channels
    }
    samples = {sample.id: sample for sample in log.samples or []} if log else {}
    _require(
        set(samples) <= set(expected) and len(samples) == len(log.samples or [] if log else []),
        "Duplicate or unexpected Inspect samples",
    )
    reviews = {review.sample_id: review for review in selection.reviews}
    _require(set(reviews) <= set(expected), "Review selection names an unplanned sample")
    sessions: list[ComparisonSession] = []
    schedules: dict[int, DealSchedule] = {}
    linked: set[str] = set()
    snapshot.inventory(directory / "sessions")
    for key, (block, channel) in expected.items():
        issues = []
        analysis = None
        block_id = f"{run_id}-block-{block}"
        selected = reviews.get(key)
        annotation = None if selected is None else selected.annotation
        previous = None if selected is None else selected.previous
        if annotation is not None and not snapshot.track(annotation):
            issues.append("missing_annotation")
            annotation = None
        if previous is not None:
            if not snapshot.track(previous):
                raise ValueError("Missing selected annotation predecessor")
        sample = samples.get(key)
        if sample is None:
            issues.append("missing_inspect_sample" if log else "inspect_index_unavailable")
        else:
            saved = sample.metadata.get("schedule")
            _require(isinstance(saved, str), "Missing saved schedule")
            assert isinstance(saved, str)
            schedule = DealSchedule.from_json(saved)
            _require(
                schedule.seed == config.seeds[block]
                and schedule.initial_rotation == block % 3
                and len(schedule.deals) == config.session.hands,
                "Saved schedule differs from the planned matched block",
            )
            _require(
                schedule == schedules.setdefault(block, schedule),
                "Saved schedules differ within the matched block",
            )
            sid = sample.metadata.get("session_id")
            _require(
                sample.epoch == 1
                and sample.metadata.get("matched_block_id") == block_id
                and sample.metadata.get("channel") == channel.value,
                "Sample identity mismatch",
            )
            if sid is None:
                issues.append("session_not_started")
            else:
                _require(
                    isinstance(sid, str)
                    and sid not in ("", ".", "..")
                    and Path(sid).name == sid
                    and sid not in linked,
                    "Invalid or duplicate session ID",
                )
                assert isinstance(sid, str)
                linked.add(sid)
                game_path = directory / "sessions" / sid / "session.jsonl"
                model_path = directory / "sessions" / sid / "model.jsonl"
                game_present = snapshot.track(game_path)
                model_present = snapshot.track(model_path)
                if not model_present:
                    issues.append("missing_model_journal")
                if not game_present:
                    issues.append("missing_session_journal")
                else:
                    analysis = await analyze_session(
                        game_path,
                        annotation_path=annotation,
                        previous_path=previous if annotation else None,
                    )
                    facts = analysis.session
                    _require(
                        analysis.source.session_id == sid
                        and facts.run_id == run_id
                        and sample.metadata.get("run_id") == run_id
                        and facts.matched_block_id == block_id
                        and facts.channel == channel
                        and facts.config_sha256
                        == digest(config_record(replace(config.session, channel=channel)))
                        and facts.schedule_sha256 == digest(_read_object(saved)),
                        "Journal differs from planned Inspect sample",
                    )
                    if model_present:
                        audit = read_model_log(model_path)
                        _require(bool(audit.events), "Missing model audit header")
                        header = audit.events[0].data
                        _require(
                            audit.session_id == sid
                            and header.get("run_id") == run_id
                            and header.get("matched_block_id") == block_id
                            and header.get("inspect_sample_id") == key
                            and header.get("inspect_epoch") == 1
                            and header.get("model_config_sha256") == config.model.sha256
                            and header.get("provenance") == start["provenance"],
                            "Model audit differs from run",
                        )
                        if analysis.source.status == "incomplete" or audit.status == "incomplete":
                            issues.append("incomplete_audit")
                        else:
                            audit_report = await verify_saved_sample(
                                directory, sample, config, run_id, block, channel, schedule
                            )
                            issues.extend(f"audit: {issue}" for issue in audit_report["issues"])
        sessions.append(
            ComparisonSession(
                run_id, block_id, key, channel, config.seeds[block], analysis, tuple(issues)
            )
        )
    unlinked = tuple(
        sorted(p.name for p in (directory / "sessions").glob("*") if p.name not in linked)
    )
    return ComparisonRun(
        run_id,
        config,
        start["provenance"],
        None if log is None else log.status,
        tuple(sessions),
        unlinked,
    )
