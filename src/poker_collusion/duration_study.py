"""A frozen six-condition, three-seed exploratory duration matrix; no model calls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from poker_collusion.experiment import experiment_plan
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.poker import generate_schedule
from poker_collusion.serialization import canonical, digest
from poker_collusion.verification import _require, verify_run


def duration_plan(short: ExperimentConfig, long: ExperimentConfig) -> dict[str, Any]:
    """Keep the first twelve deals/rotations identical, with fresh histories per sample."""
    _require(short.session.hands == 12 and long.session.hands == 36, "Expected 12/36 hands")
    _require(len(short.seeds) == 3, "Exactly three seed blocks are planned")
    _require(
        tuple(short.channels) == ("none", "public", "private"),
        "Expected all three communication channels in fixed order",
    )
    baseline, extended = json.loads(short.to_json()), json.loads(long.to_json())
    for record in (baseline, extended):
        record["session"].pop("hands")
        for key in ("token_limit", "cost_limit", "session_time_limit"):
            record.pop(key)
    _require(baseline == extended, "Duration configs differ outside horizon and stop limits")
    configs = {"12": json.loads(short.to_json()), "36": json.loads(long.to_json())}
    batches: list[dict[str, Any]] = []
    for index, seed in enumerate(short.seeds):
        schedules = {
            hands: generate_schedule(seed, hands, initial_rotation=index % 3) for hands in (12, 36)
        }
        _require(schedules[12].deals == schedules[36].deals[:12], "Deal prefixes differ")
        for hands in (12, 36) if index % 2 == 0 else (36, 12):
            batches.append(
                {
                    "order": len(batches),
                    "directory": f"seed-{seed}-{hands}hands",
                    "block_index": index,
                    "seed": seed,
                    "initial_rotation": index % 3,
                    "hands": hands,
                    "channels": list(short.channels),
                    "schedule": json.loads(schedules[hands].to_json()),
                    "config_sha256": digest(configs[str(hands)]),
                }
            )
    short_plan, long_plan = experiment_plan(short), experiment_plan(long)
    return {
        "kind": "duration_study_plan",
        "version": 1,
        "configs": configs,
        "batches": batches,
        "planned_seed_blocks": 3,
        "planned_sessions": 18,
        "planned_hands": 432,
        "maximum_decision_calls": cast(int, short_plan["maximum_decision_calls"])
        + cast(int, long_plan["maximum_decision_calls"]),
        "sum_token_thresholds": 9 * (short.token_limit + long.token_limit),
        "sum_cost_thresholds": 9 * ((short.cost_limit or 0) + (long.cost_limit or 0)),
        "scope": "Exploratory duration-by-channel study; seed blocks are the replication unit.",
        "limits_note": "Per-session post-response thresholds may overshoot; no hard billing cap.",
    }


def validate_duration_plan(plan: dict[str, Any]) -> None:
    """Reject edited schedules, duplicates, missing conditions and ambiguous block numbering."""
    configs = plan["configs"]
    short = ExperimentConfig.from_json(canonical(configs["12"]))
    long = ExperimentConfig.from_json(canonical(configs["36"]))
    _require(plan == duration_plan(short, long), "Saved duration plan differs from frozen matrix")


async def verify_duration_study(plan: dict[str, Any], root: Path) -> dict[str, Any]:
    """Preserve every planned cell, including missing/failed batches; never infer human labels."""
    validate_duration_plan(plan)
    reports = []
    identities: set[str] = set()
    complete: set[tuple[int, int, str]] = set()
    for batch in plan["batches"]:
        directory = root / batch["directory"]
        try:
            verified_cells = set()
            report = await verify_run(directory)
            start = json.loads((directory / "run.jsonl").read_text().splitlines()[0])
            _require(
                start["config"] == plan["configs"][str(batch["hands"])]
                and start["block_index"] == batch["block_index"],
                "Batch does not match its planned config/selection",
            )
            _require(report["run_id"] not in identities, "Duplicate run identity")
            identities.add(report["run_id"])
            for sample in report["sessions"]:
                session = directory / "sessions" / sample["session_id"] / "session.jsonl"
                header = json.loads(session.read_text().splitlines()[0])
                _require(
                    header["data"]["schedule"] == batch["schedule"],
                    "Saved deals differ from the precollection schedule",
                )
                _require(sample["session_id"] not in identities, "Duplicate session identity")
                identities.add(sample["session_id"])
                if sample["status"] == "complete" and not sample["issues"]:
                    verified_cells.add((batch["seed"], batch["hands"], sample["channel"]))
            reports.append({"batch": batch["directory"], "verification": report})
            complete.update(verified_cells)
        except (OSError, ValueError, KeyError, TypeError) as error:
            reports.append({"batch": batch["directory"], "error": str(error)})
    passed = all(record.get("verification", {}).get("passed", False) for record in reports)
    blocks = sum(
        all(
            (seed, hands, channel) in complete
            for hands in (12, 36)
            for channel in plan["configs"]["12"]["channels"]
        )
        for seed in plan["configs"]["12"]["seeds"]
    )
    return {
        "kind": "duration_study_verification",
        "version": 1,
        "plan_sha256": digest(plan),
        "passed": passed and len(complete) == 18,
        "live_collection_complete": passed
        and len(complete) == 18
        and all(not record["verification"]["mock"] for record in reports),
        "planned_blocks": 3,
        "complete_blocks": blocks,
        "planned_sessions": 18,
        "complete_sessions": len(complete),
        "human_primary_estimate": None,
        "human_review_status": "Not assessed by this integrity verifier",
        "batches": reports,
        "paid_calls": 0,
        "scope": "Evidence integrity only. No coalition labels or independent human review.",
    }
