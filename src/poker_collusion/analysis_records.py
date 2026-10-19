"""Typed outputs for descriptive single-session analysis, schema v1."""

from dataclasses import dataclass, field

from poker_collusion.annotations import (
    Coverage,
    Episode,
    Interval,
    Reviewer,
    ReviewStatus,
    RevisionReference,
    Rubric,
    Source,
    Verdict,
)
from poker_collusion.records import Channel, Seats, SessionFailure


@dataclass(frozen=True)
class AnalysisProvenance:
    ruleset: str
    ruleset_version: str
    implementation_sha256: str
    python_version: str
    open_spiel_version: str


@dataclass(frozen=True)
class SelectedReview:
    annotation_id: str
    sha256: str
    created_at: str
    reviewer: Reviewer
    rubric: Rubric
    review_status: ReviewStatus
    supersedes: RevisionReference | None


@dataclass(frozen=True)
class StageSummary:
    # None means no positive/uncertain judgment and insufficient finished coverage
    # to conclude not_observed. Counts/IDs retain uncertainty even beside positives.
    verdict: Verdict | None
    review_complete: bool
    observed_episodes: tuple[str, ...]
    not_observed_episodes: tuple[str, ...]
    uncertain_episodes: tuple[str, ...]
    unjudged_episodes: tuple[str, ...]


@dataclass(frozen=True)
class StageOutcomes:
    proposed: StageSummary
    accepted: StageSummary
    enacted: StageSummary


@dataclass(frozen=True)
class HandAnalysis:
    hand_index: int
    seats: Seats
    deal_sequence: int
    settlement_sequence: int | None
    player_payoffs: dict[str, int] | None


@dataclass(frozen=True)
class SessionFacts:
    run_id: str | None
    matched_block_id: str | None
    channel: Channel
    config_sha256: str
    schedule_sha256: str
    planned_hands: int
    event_count: int
    trailing_bytes: int
    replay_verified: bool
    completed_hands: int | None
    settled_hands: int | None
    player_payoffs: dict[str, int] | None
    hands: tuple[HandAnalysis, ...] | None
    failure: SessionFailure | None


@dataclass(frozen=True)
class PairPayoffs:
    settled_hands: int
    member_payoffs: dict[str, int]
    combined_payoff: int
    outsider: str
    outsider_payoff: int


@dataclass(frozen=True)
class EpisodeAnalysis:
    annotation: Episode
    # Human-selected intervals mapped to zero-based hands, not inferred onset times.
    hand_indices: tuple[int, ...] | None


@dataclass(frozen=True)
class PairAnalysis:
    pair: tuple[str, str]
    coverage: Coverage
    reviewed_interval: Interval | None
    explanation: str
    review_complete: bool
    outcomes: StageOutcomes
    payoffs: PairPayoffs | None
    episodes: tuple[EpisodeAnalysis, ...]


@dataclass(frozen=True)
class SessionAnalysis:
    provenance: AnalysisProvenance
    source: Source
    review: SelectedReview | None
    session: SessionFacts
    outcomes: StageOutcomes
    pairs: tuple[PairAnalysis, ...]
    notes: tuple[str, ...]
    kind: str = field(default="session_analysis", init=False)
    version: int = field(default=1, init=False)
