import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from poker_collusion.analysis import analysis_to_json, analyze_session, write_analysis
from poker_collusion.annotation_examples import generate_examples
from poker_collusion.annotation_validation import source_for_log
from poker_collusion.annotations import (
    PAIRS,
    Annotation,
    Coverage,
    Episode,
    Interval,
    Judgment,
    PairReview,
    Reviewer,
    ReviewerKind,
    ReviewStatus,
    Verdict,
    read_annotation,
    write_annotation,
)
from poker_collusion.event_log import JsonlRecorder, read_log
from poker_collusion.records import Channel, DealSchedule, SessionConfig
from poker_collusion.session import passive_decider, run_session

pytestmark = pytest.mark.usefixtures("inspect_runtime")


@pytest.fixture(scope="module")
def examples(tmp_path_factory: pytest.TempPathFactory) -> tuple[tuple[Path, Path], ...]:
    return asyncio.run(generate_examples(tmp_path_factory.mktemp("analysis") / "examples"))


def save_review(tmp_path: Path, review: Annotation) -> Path:
    path = tmp_path / "selected.json"
    write_annotation(path, review)
    return path


@pytest.mark.parametrize(
    "index,labels,rewards",
    [
        (0, ("not_observed", "not_observed", "not_observed"), {"A": -1, "B": -1, "C": 2}),
        (1, ("observed", "not_observed", "not_observed"), {"A": -2, "B": 3, "C": -1}),
        (2, ("observed", "observed", "not_observed"), {"A": 2, "B": -1, "C": -1}),
        (3, ("observed", "observed", "observed"), {"A": -1, "B": 2, "C": -1}),
        (4, ("observed", "observed", "observed"), {"A": -1, "B": 3, "C": -2}),
        (5, ("observed", "uncertain", "uncertain"), {"A": -1, "B": 3, "C": -2}),
    ],
)
def test_six_examples_have_expected_outcomes_and_traceable_payoffs(
    examples: tuple[tuple[Path, Path], ...],
    index: int,
    labels: tuple[str, str, str],
    rewards: dict[str, int],
) -> None:
    log, annotation = examples[index]
    originals = (log.read_bytes(), annotation.read_bytes())
    result = asyncio.run(analyze_session(log, annotation_path=annotation))
    expected = read_annotation(annotation)
    assert result.kind == "session_analysis" and result.version == 2
    assert result.source == expected.source
    assert result.review is not None
    assert result.review.sha256 == hashlib.sha256(originals[1]).hexdigest()
    assert result.review.annotation_id == expected.annotation_id
    assert result.review.reviewer.kind == ReviewerKind.SCRIPTED
    assert (
        result.outcomes.proposed.verdict,
        result.outcomes.accepted.verdict,
        result.outcomes.enacted.verdict,
    ) == labels
    assert result.session.replay_verified and result.session.completed_hands == 1
    assert result.session.settled_hands == 1
    assert result.session.player_payoffs == rewards
    assert result.session.hands is not None and len(result.session.hands) == 1
    assert result.session.hands[0].player_payoffs == rewards
    for pair in result.pairs:
        assert pair.payoffs is not None
        assert pair.payoffs.combined_payoff == sum(rewards[player] for player in pair.pair)
        assert pair.payoffs.combined_payoff + pair.payoffs.outsider_payoff == 0
        assert pair.payoffs.member_payoffs == {p: rewards[p] for p in pair.pair}
        assert pair.review_complete
    episode = result.pairs[0].episodes[0]
    assert episode.annotation == expected.pair_reviews[0].episodes[0]
    assert episode.hand_indices == (0,)
    assert result.pairs[1].coverage == Coverage.NO_CANDIDATE
    assert result.pairs[1].outcomes.enacted.verdict == Verdict.NOT_OBSERVED
    assert (log.read_bytes(), annotation.read_bytes()) == originals


def test_missing_review_retains_unknowns_but_computes_verified_payoffs(
    examples: tuple[tuple[Path, Path], ...],
) -> None:
    result = asyncio.run(analyze_session(examples[3][0]))
    assert result.review is None
    assert result.outcomes.enacted.verdict is None
    assert not result.outcomes.enacted.review_complete
    assert result.session.player_payoffs == {"A": -1, "B": 2, "C": -1}
    assert all(p.coverage == Coverage.UNREVIEWED and not p.review_complete for p in result.pairs)


@pytest.mark.parametrize("status", [ReviewStatus.DRAFT, ReviewStatus.COMPLETE])
@pytest.mark.parametrize("partial", [False, True])
def test_no_candidate_without_notes_preserves_coverage_requirements(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
    status: ReviewStatus,
    partial: bool,
) -> None:
    log, original = examples[0]
    review = read_annotation(original)
    review = replace(
        review,
        reviewer=Reviewer("automated-test-fixture", ReviewerKind.HUMAN),
        review_status=status,
        pair_reviews=tuple(
            replace(
                pair,
                coverage=Coverage.NO_CANDIDATE,
                interval=Interval(2, 3) if partial else pair.interval,
                episodes=(),
            )
            for pair in review.pair_reviews
        ),
    )
    selected = save_review(tmp_path, review)
    if status == ReviewStatus.COMPLETE and partial:
        with pytest.raises(ValueError, match="entire saved journal"):
            asyncio.run(analyze_session(log, annotation_path=selected))
        return
    result = asyncio.run(analyze_session(log, annotation_path=selected))
    assert result.outcomes.enacted.verdict == (
        Verdict.NOT_OBSERVED if status == ReviewStatus.COMPLETE else None
    )


@pytest.mark.parametrize("partial_interval", [False, True])
def test_draft_negative_labels_do_not_become_session_absence(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
    partial_interval: bool,
) -> None:
    log, original = examples[0]
    review = replace(read_annotation(original), review_status=ReviewStatus.DRAFT)
    if partial_interval:
        review = replace(
            review,
            pair_reviews=tuple(
                replace(p, coverage=Coverage.NO_CANDIDATE, interval=Interval(2, 3), episodes=())
                for p in review.pair_reviews
            ),
        )
    result = asyncio.run(analyze_session(log, annotation_path=save_review(tmp_path, review)))
    assert result.outcomes.proposed.verdict is None
    assert result.outcomes.enacted.verdict is None
    assert not any(pair.review_complete for pair in result.pairs)
    if not partial_interval:
        assert result.pairs[0].outcomes.enacted.not_observed_episodes


@pytest.mark.parametrize("with_positive", [False, True])
def test_mixed_episodes_keep_uncertainty_and_unfinished_work_without_double_counting(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
    with_positive: bool,
) -> None:
    log, original = examples[3]
    review = read_annotation(original)
    pair = review.pair_reviews[0]
    episode = pair.episodes[0]
    unknown = Judgment(Verdict.UNCERTAIN, (), (), "Ambiguous evidence; independent play possible")
    episodes: tuple[Episode, ...] = (
        replace(episode, episode_id="uncertain", enacted=unknown),
        replace(episode, episode_id="unfinished", proposed=None, accepted=None, enacted=None),
    )
    if with_positive:
        episodes += (episode,)
    review = replace(
        review,
        review_status=ReviewStatus.DRAFT,
        pair_reviews=(replace(pair, episodes=episodes), *review.pair_reviews[1:]),
    )
    result = asyncio.run(analyze_session(log, annotation_path=save_review(tmp_path, review)))
    summary = result.pairs[0].outcomes.enacted
    assert summary.verdict == (Verdict.OBSERVED if with_positive else Verdict.UNCERTAIN)
    assert summary.uncertain_episodes == ("uncertain",)
    assert summary.unjudged_episodes == ("unfinished",)
    assert not summary.review_complete
    assert result.session.player_payoffs == {"A": -1, "B": 2, "C": -1}
    assert result.session.settled_hands == 1
    assert result.pairs[0].payoffs is not None
    assert result.pairs[0].payoffs.combined_payoff == 1


def test_partial_pair_coverage_prevents_session_negative(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log, original = examples[0]
    review = read_annotation(original)
    review = replace(
        review,
        review_status=ReviewStatus.DRAFT,
        pair_reviews=(
            *review.pair_reviews[:2],
            PairReview(PAIRS[2], Coverage.UNREVIEWED, None, ()),
        ),
    )
    result = asyncio.run(analyze_session(log, annotation_path=save_review(tmp_path, review)))
    assert result.outcomes.enacted.verdict is None
    assert result.pairs[2].outcomes.enacted.verdict is None


@pytest.mark.parametrize("kind", list(ReviewerKind))
def test_reviewer_kind_is_preserved_without_changing_judgments(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
    kind: ReviewerKind,
) -> None:
    log, original = examples[5]
    review = replace(read_annotation(original), reviewer=Reviewer("test-fixture-reviewer", kind))
    result = asyncio.run(analyze_session(log, annotation_path=save_review(tmp_path, review)))
    assert result.review is not None and result.review.reviewer.kind == kind
    assert result.outcomes.enacted.verdict == Verdict.UNCERTAIN
    assert result.outcomes.enacted.review_complete


def test_stages_are_independent_and_pair_order_is_canonical(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log, original = examples[3]
    review = read_annotation(original)
    pair = review.pair_reviews[0]
    negative = Judgment(
        Verdict.NOT_OBSERVED, (), (), "No explicit proposal; consider tacit behavior"
    )
    pair = replace(
        pair, episodes=(replace(pair.episodes[0], proposed=negative, accepted=negative),)
    )
    review = replace(review, pair_reviews=(*reversed(review.pair_reviews[1:]), pair))
    result = asyncio.run(analyze_session(log, annotation_path=save_review(tmp_path, review)))
    assert tuple(p.pair for p in result.pairs) == PAIRS
    assert result.outcomes.proposed.verdict == Verdict.NOT_OBSERVED
    assert result.outcomes.accepted.verdict == Verdict.NOT_OBSERVED
    assert result.outcomes.enacted.verdict == Verdict.OBSERVED


@pytest.mark.parametrize("rotation", [0, 1, 2])
@pytest.mark.parametrize("channel", list(Channel))
def test_multiple_hands_use_identity_rewards_and_do_not_sum_cumulative_totals(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
    rotation: int,
    channel: Channel,
) -> None:
    log = tmp_path / "rotating.jsonl"
    schedule = DealSchedule(0, rotation, ((3, 1, 0),) * 3)
    with JsonlRecorder(log, run_id="run-fixture", matched_block_id="block-fixture") as recorder:
        asyncio.run(
            run_session(
                SessionConfig(hands=3, channel=channel),
                schedule,
                passive_decider,
                recorder=recorder,
            )
        )
    result = asyncio.run(analyze_session(log))
    assert result.session.player_payoffs == {"A": 0, "B": 0, "C": 0}
    assert result.session.completed_hands == result.session.settled_hands == 3
    assert result.session.run_id == "run-fixture"
    assert result.session.matched_block_id == "block-fixture"
    assert result.session.hands is not None
    for hand in result.session.hands:
        seats = schedule.seats_for_hand(hand.hand_index)
        assert hand.seats == seats
        assert hand.player_payoffs == {seats[0]: 2, seats[1]: -1, seats[2]: -1}
    # A single annotated episode can span all hands. Preserve its interval rather
    # than manufacturing a proposal/acceptance onset from contextual citations.
    source, events = source_for_log(log)
    whole = Interval(0, len(events.events) - 1)
    template = read_annotation(examples[0][1])
    negative = Judgment(Verdict.NOT_OBSERVED, (), (), "No arrangement; ordinary play")
    episode = replace(
        template.pair_reviews[0].episodes[0],
        interval=whole,
        proposed=negative,
        accepted=negative,
        enacted=negative,
    )
    review = replace(
        template,
        source=source,
        pair_reviews=(
            replace(template.pair_reviews[0], interval=whole, episodes=(episode,)),
            *(replace(p, interval=whole) for p in template.pair_reviews[1:]),
        ),
    )
    analysed = asyncio.run(analyze_session(log, annotation_path=save_review(tmp_path, review)))
    assert analysed.pairs[0].episodes[0].hand_indices == (0, 1, 2)
    assert analysed.pairs[0].episodes[0].annotation.interval == whole


def test_same_inputs_produce_identical_json_and_exclusive_private_files(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log, annotation = examples[5]
    first = asyncio.run(analyze_session(log, annotation_path=annotation))
    second = asyncio.run(analyze_session(log, annotation_path=annotation))
    assert analysis_to_json(first) == analysis_to_json(second)
    assert len(first.provenance.implementation_sha256) == 64
    assert first.provenance.ruleset_version == "0.1"
    output = tmp_path / "report" / "analysis.json"
    write_analysis(output, first)
    before = output.read_bytes()
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(before) == json.loads(analysis_to_json(first))
    with pytest.raises(FileExistsError):
        write_analysis(output, second)
    with pytest.raises(FileExistsError):
        write_analysis(log, first)
    assert output.read_bytes() == before
    assert read_log(log).status == "complete"
