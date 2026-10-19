"""Validate saved report structure and internal references, without replay or inference."""

import math
from collections import Counter
from pathlib import Path
from statistics import fmean
from typing import Any, cast

from poker_collusion.annotations import PAIRS, _hash
from poker_collusion.comparison_manifest import parse_manifest
from poker_collusion.experiment_config import ExperimentConfig
from poker_collusion.model_adapter import _read_object
from poker_collusion.report_schema import ComparisonReport, check_shape
from poker_collusion.serialization import canonical, digest

STAGES = ("proposed", "accepted", "enacted")
CHANNELS = ("none", "public", "private")
METRICS = (*STAGES, "payoff_A", "payoff_B", "payoff_C", "payoff_AB", "payoff_AC", "payoff_BC")


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(f"Invalid comparison report: {detail}")


def _numbers(value: Any) -> None:
    if type(value) is float:
        require(math.isfinite(value), "non-finite number")
    elif type(value) is int:
        require(abs(value) <= 2**53 - 1, "integer exceeds exact browser range")
    elif isinstance(value, dict):
        for item in value.values():
            _numbers(item)
    elif isinstance(value, list):
        for item in value:
            _numbers(item)


def _sessions(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    blocks: dict[str, dict[str, Any]] = {}
    expected = {}
    for run in report["runs"]:
        require(bool(run["run_id"]) and bool(run["seeds"]), "empty run identity/seeds")
        for index, seed in enumerate(run["seeds"]):
            block_id = f"{run['run_id']}-block-{index}"
            require(block_id not in expected, "duplicate run/block")
            expected[block_id] = (run["run_id"], seed, index)
    require(len(expected) == report["planned_blocks"] > 0, "planned block count")
    seeds = [seed for run in report["runs"] for seed in run["seeds"]]
    require(len(seeds) == len(set(seeds)), "repeated seeds")
    require(len(report["sessions"]) == report["planned_sessions"], "planned session count")
    ids = set()
    for row in report["sessions"]:
        block, channel = row["block_id"], row["channel"]
        require(block in expected, "session references an unknown block")
        run, seed, index = expected[block]
        require(
            row["run_id"] == run
            and row["seed"] == seed
            and row["sample_id"] == f"block-{index}-{channel}",
            "session identity",
        )
        require(channel not in blocks.setdefault(block, {}), "duplicate block condition")
        blocks[block][channel] = row
        require(set(row["stage_exclusions"]) == set(STAGES), "stage exclusions")
        analysis = row["analysis"]
        if analysis is None:
            require(bool(row["session_exclusions"]), "missing analysis requires exclusion")
            require(
                all(row["stage_exclusions"].values()), "missing analysis requires stage exclusions"
            )
            continue
        require(
            analysis["kind"] == "session_analysis" and analysis["version"] == 1, "session schema"
        )
        source, facts = analysis["source"], analysis["session"]
        require(
            source["session_id"] not in ids and bool(source["session_id"]),
            "duplicate/empty session ID",
        )
        ids.add(source["session_id"])
        _hash(source["sha256"], "source.sha256")
        require(
            source["status"] in ("complete", "failed", "interrupted", "incomplete"), "source status"
        )
        require(
            facts["run_id"] == run
            and facts["matched_block_id"] == block
            and facts["channel"] == channel,
            "analysis identity",
        )
        require(
            [tuple(p["pair"]) for p in analysis["pairs"]] == list(PAIRS),
            "canonical pair membership",
        )
        require(facts["planned_hands"] > 0 and facts["event_count"] > 0, "invalid session counts")
        if not row["session_exclusions"]:
            require(
                source["status"] == "complete"
                and facts["replay_verified"]
                and facts["completed_hands"] == facts["planned_hands"]
                and facts["player_payoffs"] is not None,
                "ineligible complete-session claim",
            )
        if facts["player_payoffs"] is not None:
            require(set(facts["player_payoffs"]) == set("ABC"), "player payoff identities")
        for stage in STAGES:
            if not row["stage_exclusions"][stage]:
                require(
                    not row["session_exclusions"]
                    and analysis["review"] is not None
                    and analysis["review"]["reviewer"]["kind"] == report["reviewer_kind"]
                    and analysis["review"]["review_status"] == "complete"
                    and analysis["outcomes"][stage]["review_complete"]
                    and analysis["outcomes"][stage]["verdict"] in ("observed", "not_observed"),
                    "ineligible resolved-stage claim",
                )
    require(set(blocks) == set(expected), "missing planned block")
    for members in blocks.values():
        require(
            set(members) == set(report["experiment_settings"]["channels"]),
            "missing planned condition row",
        )
    return blocks


def _conditions(report: dict[str, Any]) -> None:
    require(set(report["conditions"]) == set(CHANNELS), "condition summary keys")
    for channel, condition in report["conditions"].items():
        members = [s for s in report["sessions"] if s["channel"] == channel]
        count = len(members)
        require(condition["planned_sessions"] == count, "condition denominator")
        statuses = Counter(
            "missing" if s["analysis"] is None else s["analysis"]["source"]["status"]
            for s in members
        )
        require(condition["statuses"] == dict(statuses), "condition statuses")
        require(
            condition["audited_complete_sessions"]
            == sum(not s["session_exclusions"] for s in members),
            "audited session count",
        )
        require(set(condition["stages"]) == set(STAGES), "condition stages")
        for stage, values in condition["stages"].items():
            require(
                set(values["reported_verdicts"])
                == {"observed", "not_observed", "uncertain", "unknown"},
                "verdict keys",
            )
            counts = Counter(
                "unknown"
                if s["analysis"] is None
                else s["analysis"]["outcomes"][stage]["verdict"] or "unknown"
                for s in members
            )
            require(
                all(value == counts[key] for key, value in values["reported_verdicts"].items()),
                "verdict counts",
            )
            eligible = [s for s in members if not s["stage_exclusions"][stage]]
            positives = sum(
                s["analysis"]["outcomes"][stage]["verdict"] == "observed" for s in eligible
            )
            require(
                values["eligible_sessions"] == len(eligible)
                and values["excluded_sessions"] == count - len(eligible)
                and values["observed_eligible_sessions"] == positives,
                "stage denominator",
            )
            rate = positives / len(eligible) if eligible else None
            require(values["resolved_rate"] == rate, "resolved rate disagrees with counts")


def _estimates(report: dict[str, Any], blocks: dict[str, dict[str, Any]]) -> None:
    require(
        [(c["left"], c["right"]) for c in report["contrasts"]]
        == [("private", "public"), ("private", "none"), ("public", "none")],
        "contrast order or identity",
    )
    for contrast in report["contrasts"]:
        require(set(contrast["estimates"]) == set(METRICS), "estimate metrics")
        for metric, estimate in contrast["estimates"].items():
            members, excluded = estimate["members"], estimate["exclusions"]
            keys = [row["block_id"] for row in (*members, *excluded)]
            require(
                set(keys) == set(blocks) and len(keys) == len(blocks), "estimate block partition"
            )
            require(
                estimate["planned_blocks"] == len(blocks)
                and estimate["eligible_blocks"] == len(members)
                and estimate["excluded_blocks"] == len(excluded),
                "estimate denominator",
            )
            require(
                estimate["units"]
                == ("session_probability" if metric in STAGES else "chips_per_session"),
                "estimate units",
            )
            for row in members:
                for side in ("left", "right"):
                    session = blocks[row["block_id"]].get(contrast[side])
                    require(session is not None, "unplanned included condition")
                    assert session is not None
                    reasons = (
                        session["stage_exclusions"][metric]
                        if metric in STAGES
                        else session["session_exclusions"]
                    )
                    require(
                        not reasons and session["analysis"] is not None,
                        "excluded session in estimate",
                    )
                    analysis = session["analysis"]
                    value = (
                        float(analysis["outcomes"][metric]["verdict"] == "observed")
                        if metric in STAGES
                        else sum(
                            analysis["session"]["player_payoffs"][p]
                            for p in metric.removeprefix("payoff_")
                        )
                    )
                    require(row[side] == value, "member value disagrees with session")
                require(
                    math.isclose(row["difference"], row["left"] - row["right"], abs_tol=1e-12),
                    "member difference",
                )
            for row in excluded:
                expected_reasons = {}
                for channel in (contrast["left"], contrast["right"]):
                    session = blocks[row["block_id"]].get(channel)
                    reasons = (
                        ["condition_not_planned"]
                        if session is None
                        else (
                            session["stage_exclusions"][metric]
                            if metric in STAGES
                            else session["session_exclusions"]
                        )
                    )
                    if reasons:
                        expected_reasons[channel] = reasons
                require(
                    bool(row["reasons"]) and row["reasons"] == expected_reasons,
                    "exclusion reasons",
                )
            for key in ("left_mean", "right_mean", "difference"):
                require((estimate[key] is None) == (not members), "missing estimate")
            interval = estimate["interval"]
            require((interval is None) == (len(members) < 2), "interval availability")
            if interval is not None:
                require(interval["lower"] <= interval["upper"], "reversed interval")
            if members:
                for mean, field in (
                    ("left_mean", "left"),
                    ("right_mean", "right"),
                    ("difference", "difference"),
                ):
                    require(
                        math.isclose(
                            estimate[mean], fmean(row[field] for row in members), abs_tol=1e-12
                        ),
                        "estimate mean disagrees with members",
                    )
                require(
                    math.isclose(
                        estimate["difference"],
                        estimate["left_mean"] - estimate["right_mean"],
                        abs_tol=1e-12,
                    ),
                    "estimate difference",
                )
                if metric in STAGES:
                    require(
                        0 <= estimate["left_mean"] <= 1 and 0 <= estimate["right_mean"] <= 1,
                        "probability range",
                    )
                    if interval:
                        require(
                            -1 <= interval["lower"] <= interval["upper"] <= 1,
                            "probability interval range",
                        )


def read_comparison_report(payload: str) -> dict[str, Any]:
    report = cast(dict[str, Any], _read_object(payload))
    _numbers(report)
    check_shape(report, ComparisonReport)
    manifest = parse_manifest(canonical(report["selection"]), Path("."))
    require(len(manifest.runs) == len(report["runs"]), "selected run count")
    require(
        report["dataset_role"] == manifest.dataset_role
        and report["reviewer_kind"] == manifest.reviewer_kind,
        "selection labels",
    )
    require(report["policy"]["bootstrap"] == report["selection"]["bootstrap"], "bootstrap settings")
    settings = report["experiment_settings"]
    ExperimentConfig.from_json(canonical({**settings, "seeds": [0]}))
    require({"public", "private"} <= set(settings["channels"]), "primary conditions not planned")
    require(digest(settings) == report["experiment_settings_sha256"], "settings hash")
    require(report["instruction"] == settings["model"]["settings"]["instruction"], "instruction")
    mock = settings["model"]["settings"]["model"].startswith("mockllm/")
    require(
        report["gameplay_kind"] == ("scripted_mock" if mock else "model")
        and (not mock or report["dataset_role"] == "preparation"),
        "gameplay kind",
    )
    require(
        report["provenance"]["ruleset"] == "matched_session_comparison"
        and report["provenance"]["ruleset_version"] == "0.1",
        "analysis ruleset",
    )
    _hash(report["provenance"]["implementation_sha256"], "implementation hash")
    for item in report["inputs"]:
        if item["sha256"] is not None:
            _hash(item["sha256"], "input hash")
    blocks = _sessions(report)
    _conditions(report)
    _estimates(report, blocks)
    return report
