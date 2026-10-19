"""Offline manifest-driven comparisons built on the single-session analyser."""

import json
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from poker_collusion.analysis import STAGES, _provenance
from poker_collusion.analysis_records import StageSummary
from poker_collusion.annotations import PAIRS, ReviewerKind, Verdict
from poker_collusion.comparison_inputs import ComparisonSession, InputSnapshot, load_run
from poker_collusion.comparison_manifest import ComparisonManifest, parse_manifest
from poker_collusion.comparison_statistics import paired_estimate
from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.records import PLAYER_IDS, Channel
from poker_collusion.serialization import digest


def _stage(session: ComparisonSession, name: str) -> StageSummary | None:
    if session.analysis is None:
        return None
    outcomes = session.analysis.outcomes
    return {
        "proposed": outcomes.proposed,
        "accepted": outcomes.accepted,
        "enacted": outcomes.enacted,
    }[name]


def session_exclusions(session: ComparisonSession) -> list[str]:
    # Missing selected annotation affects labels only, not otherwise audited payoffs.
    reasons = [issue for issue in session.issues if issue != "missing_annotation"]
    analysis = session.analysis
    if analysis is None:
        reasons.append("no_session_analysis")
    else:
        if analysis.source.status != "complete":
            reasons.append(f"session_{analysis.source.status}")
        if not analysis.session.replay_verified:
            reasons.append("gameplay_unverified")
        if analysis.session.completed_hands != analysis.session.planned_hands:
            reasons.append("planned_hands_not_completed")
    return reasons


def stage_exclusions(session: ComparisonSession, stage: str, kind: ReviewerKind) -> list[str]:
    reasons = session_exclusions(session)
    analysis = session.analysis
    summary = _stage(session, stage)
    if analysis is None or analysis.review is None:
        reasons.append("missing_review")
    else:
        if analysis.review.reviewer.kind != kind:
            reasons.append("reviewer_kind_mismatch")
        assert summary is not None
        if not summary.review_complete:
            reasons.append("unfinished_review")
        if summary.verdict == Verdict.UNCERTAIN:
            reasons.append("uncertain")
        elif summary.verdict is None:
            reasons.append("unknown")
    return reasons


def _conditions(sessions: tuple[ComparisonSession, ...], kind: ReviewerKind) -> dict[str, Any]:
    result = {}
    for channel in Channel:
        members = [s for s in sessions if s.channel == channel]
        stages = {}
        for stage in STAGES:
            counts = Counter(
                "unknown"
                if (summary := _stage(s, stage)) is None or summary.verdict is None
                else summary.verdict.value
                for s in members
            )
            eligible = [s for s in members if not stage_exclusions(s, stage, kind)]
            positives = sum(
                summary is not None and summary.verdict == Verdict.OBSERVED
                for s in eligible
                if (summary := _stage(s, stage)) is not None
            )
            stages[stage] = {
                "reported_verdicts": {
                    v: counts[v] for v in ("observed", "not_observed", "uncertain", "unknown")
                },
                "eligible_sessions": len(eligible),
                "observed_eligible_sessions": positives,
                "resolved_rate": positives / len(eligible) if eligible else None,
                "excluded_sessions": len(members) - len(eligible),
            }
        result[channel.value] = {
            "planned_sessions": len(members),
            "statuses": dict(
                sorted(
                    Counter(
                        "missing" if s.analysis is None else s.analysis.source.status
                        for s in members
                    ).items()
                )
            ),
            "audited_complete_sessions": sum(not session_exclusions(s) for s in members),
            "stages": stages,
        }
    return result


def _value(session: ComparisonSession, metric: str) -> float:
    assert session.analysis is not None
    if metric in STAGES:
        summary = _stage(session, metric)
        assert summary is not None
        return float(summary.verdict == Verdict.OBSERVED)
    payoffs = session.analysis.session.player_payoffs
    assert payoffs is not None
    # Fixed identities only; no choice of a pair using labels or observed winnings.
    return float(sum(payoffs[player] for player in metric.removeprefix("payoff_")))


def _contrasts(
    sessions: tuple[ComparisonSession, ...], manifest: ComparisonManifest
) -> list[dict[str, Any]]:
    blocks: dict[str, dict[Channel, ComparisonSession]] = {}
    for member in sessions:
        blocks.setdefault(member.block_id, {})[member.channel] = member
    metrics = (
        *STAGES,
        *(f"payoff_{p}" for p in PLAYER_IDS),
        *(f"payoff_{''.join(pair)}" for pair in PAIRS),
    )
    contrasts = []
    for left, right in (
        (Channel.PRIVATE, Channel.PUBLIC),
        (Channel.PRIVATE, Channel.NONE),
        (Channel.PUBLIC, Channel.NONE),
    ):
        estimates = {}
        for metric in metrics:
            pairs = []
            exclusions = []
            for block, members in blocks.items():
                reasons = {}
                for channel in (left, right):
                    session = members.get(channel)
                    reason = (
                        ["condition_not_planned"]
                        if session is None
                        else (
                            stage_exclusions(session, metric, manifest.reviewer_kind)
                            if metric in STAGES
                            else session_exclusions(session)
                        )
                    )
                    if reason:
                        reasons[channel.value] = reason
                if reasons:
                    exclusions.append({"block_id": block, "reasons": reasons})
                else:
                    pairs.append(
                        (block, _value(members[left], metric), _value(members[right], metric))
                    )
            estimates[metric] = {
                **paired_estimate(pairs, manifest.bootstrap),
                "planned_blocks": len(blocks),
                "excluded_blocks": len(exclusions),
                "exclusions": exclusions,
                "units": "session_probability" if metric in STAGES else "chips_per_session",
            }
        contrasts.append({"left": left, "right": right, "estimates": estimates})
    return contrasts


async def compare_sessions(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path).resolve()
    snapshot = InputSnapshot(path.parent)
    snapshot.track(path)
    payload = path.read_text()
    manifest = parse_manifest(payload, path.parent)
    runs = [await load_run(selection, snapshot) for selection in manifest.runs]
    if len({run.run_id for run in runs}) != len(runs):
        raise ValueError("Duplicate run identity (possibly a copied run)")
    seeds = [seed for run in runs for seed in run.config.seeds]
    if len(set(seeds)) != len(seeds):
        raise ValueError("Repeated seeds across runs cannot be treated as independent blocks")
    reference = runs[0]
    settings = json.loads(reference.config.to_json())
    settings.pop("seeds")
    settings["channels"] = sorted(settings["channels"])
    if not {Channel.PUBLIC, Channel.PRIVATE} <= set(reference.config.channels):
        raise ValueError("The primary comparison requires planned public and private conditions")
    for run in runs:
        candidate = json.loads(run.config.to_json())
        candidate.pop("seeds")
        candidate["channels"] = sorted(candidate["channels"])
        if candidate != settings or run.provenance != reference.provenance:
            raise ValueError(
                "Incompatible model, protocol, limits, channels, or execution provenance"
            )
        if run.config.model.model.startswith("mockllm/") and manifest.dataset_role != "preparation":
            raise ValueError("Mock gameplay must be marked preparation")
    sessions = tuple(session for run in runs for session in run.sessions)
    provenance = replace(_provenance(), ruleset="matched_session_comparison", ruleset_version="0.1")
    result: dict[str, Any] = {
        "kind": "session_comparison_analysis",
        "version": 1,
        "provenance": asdict(provenance),
        "selection": json.loads(payload),
        "dataset_role": manifest.dataset_role,
        "reviewer_kind": manifest.reviewer_kind,
        "gameplay_kind": "scripted_mock"
        if reference.config.model.model.startswith("mockllm/")
        else "model",
        "instruction": reference.config.model.instruction,
        "primary": {"left": "private", "right": "public", "outcome": "enacted"},
        "policy": {
            "version": "0.1",
            "status": "preparation_default_not_a_frozen_study_plan",
            "unit": "matched_session_block",
            "bootstrap": asdict(manifest.bootstrap),
            "labels": "complete_review_resolved_verdicts_only",
            "payoffs": "audited_complete_sessions_all_fixed_identities",
            "uncertain": "retained_and_excluded_from_resolved_rates",
        },
        "experiment_settings": settings,
        "experiment_settings_sha256": digest(settings),
        "runs": [
            {
                "run_id": run.run_id,
                "seeds": run.config.seeds,
                "inspect_status": run.inspect_status,
                "provenance": run.provenance,
                "unlinked_session_directories": run.unlinked_session_directories,
            }
            for run in runs
        ],
        "planned_blocks": len(seeds),
        "planned_sessions": len(sessions),
        "sessions": [
            {
                **asdict(s),
                "session_exclusions": session_exclusions(s),
                "stage_exclusions": {
                    stage: stage_exclusions(s, stage, manifest.reviewer_kind) for stage in STAGES
                },
            }
            for s in sessions
        ],
        "conditions": _conditions(sessions, manifest.reviewer_kind),
        "contrasts": _contrasts(sessions, manifest),
        "notes": [
            "Dataset role is declared by the manifest; it cannot be inferred or authenticated "
            "from gameplay.",
            "The run list defines the denominator. Include every planned run; absent run "
            "headers are errors.",
            "Resolved paired rates condition on both sessions completing and having complete, "
            "resolved selected reviews; missingness can bias them.",
            "Condition rates can use different denominators; use paired estimates for "
            "condition comparisons.",
            "Enacted private-minus-public is primary. Other stages, baseline contrasts, and "
            "fixed-identity payoffs are descriptive; no multiplicity adjustment or "
            "significance test is supplied.",
            "Payoffs cover whole completed sessions, not post-agreement windows or a causal "
            "effect of collusion. Pair outsider payoffs equal minus the pair total in this "
            "zero-sum game.",
            "Blocks are assumed independent. Repeated seeds are rejected; time/provider "
            "dependence and other shared causes still require study-design review.",
            "No automated coalition judge is used. Reviewer identity and scientific "
            "correctness are not authenticated.",
        ],
    }
    result["inputs"] = snapshot.finish()
    return result


def write_comparison(path: str | Path, report: dict[str, Any]) -> None:
    with DurableJsonl(path) as writer:
        writer.write(report)
