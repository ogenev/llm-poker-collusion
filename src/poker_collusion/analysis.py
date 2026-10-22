"""Offline descriptive analysis of one journal and one explicitly selected review."""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict, replace
from importlib.metadata import version
from pathlib import Path
from typing import cast

from poker_collusion.analysis_records import (
    AnalysisProvenance,
    EpisodeAnalysis,
    HandAnalysis,
    PairAnalysis,
    PairPayoffs,
    SelectedReview,
    SessionAnalysis,
    SessionFacts,
    StageOutcomes,
    StageSummary,
)
from poker_collusion.annotation_validation import source_for_log, validate_annotation
from poker_collusion.annotations import (
    PAIRS,
    Annotation,
    Coverage,
    Episode,
    Interval,
    PairReview,
    ReviewerKind,
    ReviewStatus,
    Verdict,
    annotation_from_json,
)
from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.event_log import SessionLog
from poker_collusion.records import PLAYER_IDS, Seats, SessionState
from poker_collusion.replay import replay_session
from poker_collusion.serialization import digest, read_config

STAGES = ("proposed", "accepted", "enacted")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _provenance() -> AnalysisProvenance:
    root = Path(__file__).parent
    sources = {path.name: _sha256(path.read_bytes()) for path in sorted(root.glob("*.py"))}
    return AnalysisProvenance(
        "single_session_descriptive",
        "0.1",
        digest(sources),
        platform.python_version(),
        version("open-spiel"),
    )


def _outcomes(episodes: tuple[Episode, ...], complete: bool) -> StageOutcomes:
    stages = []
    for name in STAGES:
        observed, negative, uncertain, unfinished = [], [], [], []
        for episode in episodes:
            judgment = {
                "proposed": episode.proposed,
                "accepted": episode.accepted,
                "enacted": episode.enacted,
            }[name]
            if judgment is None:
                unfinished.append(episode.episode_id)
            elif judgment.verdict == Verdict.OBSERVED:
                observed.append(episode.episode_id)
            elif judgment.verdict == Verdict.UNCERTAIN:
                uncertain.append(episode.episode_id)
            else:
                negative.append(episode.episode_id)
        reviewed = complete and not unfinished
        verdict = (
            Verdict.OBSERVED
            if observed
            else Verdict.UNCERTAIN
            if uncertain
            else Verdict.NOT_OBSERVED
            if reviewed
            else None
        )
        stages.append(
            StageSummary(
                verdict,
                reviewed,
                tuple(observed),
                tuple(negative),
                tuple(uncertain),
                tuple(unfinished),
            )
        )
    return StageOutcomes(*stages)


def _verified_hands(log: SessionLog, state: SessionState) -> tuple[HandAnalysis, ...]:
    """Seat returns are per-hand; rewards_settled.rewards is already cumulative."""
    hands: list[HandAnalysis] = []
    totals = dict.fromkeys(PLAYER_IDS, 0)
    for event in log.events:
        if event.event == "hand_dealt":
            hands.append(
                HandAnalysis(
                    cast(int, event.data["hand_index"]),
                    cast(Seats, tuple(cast(list[str], event.data["seats"]))),
                    event.sequence,
                    None,
                    None,
                )
            )
        elif event.event == "rewards_settled":
            hand = hands[-1]
            if hand.player_payoffs is not None:
                raise ValueError("Duplicate settlement in analysed hand")
            returns = cast(list[int], event.data["returns"])
            payoffs = dict(zip(hand.seats, returns, strict=True))
            for player, reward in payoffs.items():
                totals[player] += reward
            if sum(payoffs.values()) != 0 or totals != event.data["rewards"]:
                raise ValueError("Per-hand payoffs differ from recorded cumulative rewards")
            hands[-1] = replace(hand, settlement_sequence=event.sequence, player_payoffs=payoffs)
    if totals != state.rewards:
        raise ValueError("Analysed payoffs differ from replayed session rewards")
    return tuple(hands)


def _hand_indices(log: SessionLog) -> tuple[int | None, ...]:
    current: int | None = None
    result = []
    for event in log.events:
        if "hand_index" in event.data:
            current = cast(int, event.data["hand_index"])
        result.append(current)
    return tuple(result)


def _pair_analysis(
    pair: PairReview,
    review: Annotation | None,
    facts: SessionFacts,
    coordinates: tuple[int | None, ...] | None,
) -> PairAnalysis:
    complete = (
        review is not None
        and review.review_status == ReviewStatus.COMPLETE
        and pair.coverage != Coverage.UNREVIEWED
        and pair.interval == Interval(0, facts.event_count - 1)
    )
    payoffs = None
    if facts.player_payoffs is not None and facts.settled_hands is not None:
        members = {player: facts.player_payoffs[player] for player in pair.pair}
        outsider = next(player for player in PLAYER_IDS if player not in pair.pair)
        payoffs = PairPayoffs(
            facts.settled_hands,
            members,
            sum(members.values()),
            outsider,
            facts.player_payoffs[outsider],
        )
    episodes = tuple(
        EpisodeAnalysis(
            episode,
            None
            if coordinates is None
            else tuple(
                sorted(
                    {
                        index
                        for index in coordinates[episode.interval.start : episode.interval.end + 1]
                        if index is not None
                    }
                )
            ),
        )
        for episode in pair.episodes
    )
    return PairAnalysis(
        pair.pair,
        pair.coverage,
        pair.interval,
        complete,
        _outcomes(pair.episodes, complete),
        payoffs,
        episodes,
    )


async def analyze_session(
    log_path: str | Path,
    *,
    annotation_path: str | Path | None = None,
    previous_path: str | Path | None = None,
) -> SessionAnalysis:
    """Validate, replay, and summarise without models or automatic coalition judgments.

    Missing reviews retain unknown outcomes. Incomplete sources retain annotation
    judgments and prefix metadata, but their unverified game totals are unavailable.
    All input hashes are checked again after the reads/replay to detect changes.
    """
    if previous_path is not None and annotation_path is None:
        raise ValueError("A previous review requires a selected annotation")
    path = Path(log_path)
    source, log = source_for_log(path)
    inputs = {path: source.sha256}
    review = None
    selected = None
    if previous_path is not None:
        previous_path = Path(previous_path)
        inputs[previous_path] = _sha256(previous_path.read_bytes())
    if annotation_path is not None:
        annotation_path = Path(annotation_path)
        payload = annotation_path.read_bytes()
        inputs[annotation_path] = _sha256(payload)
        review = annotation_from_json(payload)
        validate_annotation(review, path, previous_path=previous_path)
        selected = SelectedReview(
            review.annotation_id,
            inputs[annotation_path],
            review.created_at,
            review.reviewer,
            review.rubric,
            review.review_status,
            review.supersedes,
        )
    # read_log has already checked that these envelope metadata are constant.
    with path.open("rb") as stream:
        metadata = cast(dict[str, str | None], json.loads(stream.readline())["metadata"])
    start = log.events[0].data
    config = read_config(start["config"])
    state = None if source.status == "incomplete" else await replay_session(path)
    hands = None if state is None else _verified_hands(log, state)
    facts = SessionFacts(
        metadata["run_id"],
        metadata["matched_block_id"],
        config.channel,
        cast(str, start["config_sha256"]),
        cast(str, start["schedule_sha256"]),
        config.hands,
        len(log.events),
        log.trailing_bytes,
        state is not None,
        None if state is None else state.completed_hands,
        None if hands is None else sum(hand.player_payoffs is not None for hand in hands),
        None if state is None else dict(state.rewards),
        hands,
        None if state is None else state.failure,
    )
    coordinates = None if state is None else _hand_indices(log)
    by_pair = {} if review is None else {pair.pair: pair for pair in review.pair_reviews}
    pairs = tuple(
        _pair_analysis(
            by_pair.get(pair, PairReview(pair, Coverage.UNREVIEWED, None, ())),
            review,
            facts,
            coordinates,
        )
        for pair in PAIRS
    )
    episodes = tuple(e.annotation for pair in pairs for e in pair.episodes)
    notes = [
        "Coalition judgments are declared reviewer assessments; validation does not establish "
        "their scientific correctness or authenticate reviewer identity.",
        "Payoffs describe settled hands for each fixed pair across the saved session. "
        "They do not establish a causal advantage from coordination.",
        "Episode intervals include context; they are not exact proposal, acceptance, or "
        "enactment onset times. No automatic staircase is imposed on stage judgments.",
        "This report supplies no condition comparison, inclusion decision, or statistical "
        "confidence interval. Review kind does not establish whether gameplay was scripted.",
    ]
    if review is None:
        notes.append("No annotation selected: all pairs remain unreviewed.")
    elif review.review_status == ReviewStatus.DRAFT:
        notes.append(
            "Draft review: positive/uncertain evidence is retained; negative rollups "
            "require a complete review of the entire saved journal."
        )
    if review is not None and review.reviewer.kind != ReviewerKind.HUMAN:
        notes.append(f"Selected review is {review.reviewer.kind}, not a human review.")
    if review is not None and review.supersedes is not None:
        notes.append(
            "Only the immediate predecessor is validated; earlier revision links "
            "must be checked separately."
        )
    if state is None:
        notes.append(
            "Incomplete journal: prefix structure and annotation links checked only. "
            "Gameplay, hand mapping, and payoffs are unverified and unavailable."
        )
    elif source.status != "complete":
        notes.append(
            "Failed/interrupted session: settled payoffs are partial outcomes, "
            "not results from a shorter successful session."
        )
    result = SessionAnalysis(
        _provenance(),
        source,
        selected,
        facts,
        _outcomes(episodes, all(pair.review_complete for pair in pairs)),
        pairs,
        tuple(notes),
    )
    for input_path, expected in inputs.items():
        if _sha256(input_path.read_bytes()) != expected:
            raise ValueError("Analysis input changed while being read; use stable saved files")
    return result


def analysis_to_json(analysis: SessionAnalysis) -> str:
    """Deterministic, readable JSON; no generated timestamp or random identifier."""
    return (
        json.dumps(asdict(analysis), indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    )


def write_analysis(path: str | Path, analysis: SessionAnalysis) -> None:
    """Write one exclusive, durable JSON object using the repository's private writer."""
    with DurableJsonl(path) as writer:
        writer.write(asdict(analysis))
