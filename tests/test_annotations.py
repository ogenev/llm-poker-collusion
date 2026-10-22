import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from poker_collusion.annotation_examples import generate_examples
from poker_collusion.annotation_validation import validate_annotation
from poker_collusion.annotations import (
    Coverage,
    PairReview,
    Reviewer,
    ReviewerKind,
    ReviewStatus,
    Verdict,
    annotation_from_dict,
    annotation_from_json,
    annotation_to_json,
    read_annotation,
    write_annotation,
)
from poker_collusion.event_log import read_log
from poker_collusion.replay import replay_session


@pytest.fixture(scope="module")
def examples(tmp_path_factory: pytest.TempPathFactory) -> tuple[tuple[Path, Path], ...]:
    return asyncio.run(generate_examples(tmp_path_factory.mktemp("annotations") / "examples"))


def test_six_examples_replay_validate_and_preserve_distinct_labels(
    examples: tuple[tuple[Path, Path], ...],
) -> None:
    expected = [
        ("not_observed", "not_observed", "not_observed"),
        ("observed", "not_observed", "not_observed"),
        ("observed", "observed", "not_observed"),
        ("observed", "observed", "observed"),
        ("observed", "observed", "observed"),
        ("observed", "uncertain", "uncertain"),
    ]
    assert len(examples) == 6
    for (log_path, review_path), labels in zip(examples, expected, strict=True):
        before = (log_path.read_bytes(), review_path.read_bytes())
        review = read_annotation(review_path)
        assert review.reviewer.kind == ReviewerKind.SCRIPTED
        assert review.review_status == ReviewStatus.COMPLETE
        assert review.source.sha256 == hashlib.sha256(before[0]).hexdigest()
        episode = review.pair_reviews[0].episodes[0]
        assert (
            tuple(j.verdict for j in (episode.proposed, episode.accepted, episode.enacted) if j)
            == labels
        )
        assert all(pair.coverage == Coverage.NO_CANDIDATE for pair in review.pair_reviews[1:])
        assert annotation_from_json(annotation_to_json(review)) == review
        validate_annotation(review, log_path)
        assert asyncio.run(replay_session(log_path)).phase == "complete"
        assert (log_path.read_bytes(), review_path.read_bytes()) == before


def test_examples_use_real_round_views_and_message_indices(
    examples: tuple[tuple[Path, Path], ...],
) -> None:
    log = read_log(examples[5][0])
    views = [
        cast(dict[str, Any], e.data["view"]) for e in log.events if e.event == "decision_requested"
    ]
    first_b_view = next(view for view in views if view["player_id"] == "B")
    assert first_b_view["messages"] == []
    episode = read_annotation(examples[5][1]).pair_reviews[0].episodes[0]
    assert episode.accepted is not None and episode.accepted.verdict == Verdict.UNCERTAIN
    message_refs = [r for r in episode.accepted.contradicting_evidence if r.message]
    assert len(message_refs) == 1
    assert message_refs[0].message is not None and message_refs[0].message.index == 1

    exchange = read_log(examples[3][0])
    views = [
        cast(dict[str, Any], e.data["view"])
        for e in exchange.events
        if e.event == "decision_requested"
    ]
    second_b_view = next(
        view for view in views if view["player_id"] == "B" and view["round_index"] == 1
    )
    assert len(second_b_view["messages"]) == 1
    assert second_b_view["messages"][0]["round_index"] == 0


def test_draft_has_no_implicit_negative_labels_and_complete_can_be_uncertain(
    examples: tuple[tuple[Path, Path], ...],
) -> None:
    log_path, review_path = examples[5]
    review = read_annotation(review_path)
    draft = replace(
        review,
        review_status=ReviewStatus.DRAFT,
        pair_reviews=tuple(
            PairReview(p.pair, Coverage.UNREVIEWED, None, "", ()) for p in review.pair_reviews
        ),
    )
    validate_annotation(draft, log_path)
    assert all(not p.episodes and p.interval is None for p in draft.pair_reviews)
    with pytest.raises(ValueError, match="unreviewed"):
        annotation_to_json(replace(draft, review_status=ReviewStatus.COMPLETE))
    pair = review.pair_reviews[0]
    partial = replace(pair, episodes=(replace(pair.episodes[0], accepted=None),))
    draft = replace(
        review, review_status=ReviewStatus.DRAFT, pair_reviews=(partial, *review.pair_reviews[1:])
    )
    validate_annotation(draft, log_path)
    with pytest.raises(ValueError, match="all three judgments"):
        annotation_to_json(replace(draft, review_status=ReviewStatus.COMPLETE))
    validate_annotation(review, log_path)  # Complete is allowed to remain uncertain.


def test_independent_reviewers_and_multiple_episodes_are_preserved(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log_path, review_path = examples[2]
    original = read_annotation(review_path)
    pair = original.pair_reviews[0]
    extra = replace(pair.episodes[0], episode_id="second-candidate")
    first = replace(
        original,
        annotation_id="human-one",
        reviewer=Reviewer("one", ReviewerKind.HUMAN),
        pair_reviews=(replace(pair, episodes=(*pair.episodes, extra)), *original.pair_reviews[1:]),
    )
    second = replace(
        original, annotation_id="human-two", reviewer=Reviewer("two", ReviewerKind.HUMAN)
    )
    for annotation in (first, second):
        validate_annotation(annotation, log_path)
        write_annotation(tmp_path / f"{annotation.annotation_id}.json", annotation)
    assert len(read_annotation(tmp_path / "human-one.json").pair_reviews[0].episodes) == 2
    assert read_annotation(tmp_path / "human-two.json").reviewer.id == "two"
    assert read_annotation(review_path) == original


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("version",), True),
        (("version",), 2),
        (("kind",), "other"),
        (("extra",), "unknown"),
        (("rubric", "version"), "future"),
        (("source", "sha256"), "not-a-hash"),
        (("source", "status"), "successful"),
        (("reviewer", "kind"), "automatic-human"),
        (("reviewer", "id"), " "),
        (("created_at",), "2026-10-18"),
        (("created_at",), "2026-10-18T10:00:00"),
        (("review_status",), "approved"),
        (("pair_reviews", 0, "pair"), ["B", "A"]),
        (("pair_reviews", 0, "pair"), ["A", "A"]),
        (("pair_reviews", 0, "coverage"), "no_candidate"),
        (("pair_reviews", 0, "explanation"), ""),
        (("pair_reviews", 1, "explanation"), None),
        (("pair_reviews", 0, "interval", "start"), True),
        (("pair_reviews", 0, "interval", "end"), -1),
        (("pair_reviews", 0, "episodes", 0, "proposed", "verdict"), "yes"),
        (("pair_reviews", 0, "episodes", 0, "proposed", "supporting_evidence"), []),
        (("pair_reviews", 0, "episodes", 0, "proposed", "explanation"), " "),
        (("pair_reviews", 0, "episodes", 0, "proposed", "alternatives"), None),
        (("pair_reviews", 0, "episodes", 0, "proposed", "supporting_evidence", 0, "sequence"), "3"),
        (
            ("pair_reviews", 0, "episodes", 0, "proposed", "supporting_evidence", 0, "sequence"),
            True,
        ),
        (("pair_reviews", 0, "episodes", 0, "proposed", "supporting_evidence", 0, "message"), None),
        (
            (
                "pair_reviews",
                0,
                "episodes",
                0,
                "proposed",
                "supporting_evidence",
                0,
                "message",
                "index",
            ),
            False,
        ),
    ],
)
def test_invalid_structures_are_rejected(
    examples: tuple[tuple[Path, Path], ...],
    path: tuple[str | int, ...],
    value: object,
) -> None:
    data: dict[str, Any] = json.loads(examples[3][1].read_text())
    target: Any = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        annotation_from_dict(data)


def test_missing_fields_duplicate_ids_and_duplicate_json_keys_are_rejected(
    examples: tuple[tuple[Path, Path], ...],
) -> None:
    raw = examples[3][1].read_text()
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        annotation_from_json(
            raw.replace(
                '"kind":"coalition_annotation"',
                '"kind":"coalition_annotation","kind":"coalition_annotation"',
            )
        )
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        annotation_from_json(
            raw.replace('"verdict":"observed"', '"verdict":"observed","verdict":"uncertain"', 1)
        )
    with pytest.raises(ValueError, match="Non-finite"):
        annotation_from_json(raw.replace('"version":1', '"version":NaN', 1))
    data = json.loads(raw)
    del data["pair_reviews"][0]["episodes"][0]["accepted"]
    with pytest.raises(ValueError, match="fields"):
        annotation_from_dict(data)
    data = json.loads(raw)
    data["pair_reviews"][2] = data["pair_reviews"][1]
    with pytest.raises(ValueError, match="each of the three pairs"):
        annotation_from_dict(data)
    data = json.loads(raw)
    data["pair_reviews"][0]["episodes"] *= 2
    with pytest.raises(ValueError, match="Episode identifiers"):
        annotation_from_dict(data)


def test_exclusive_writes_preserve_reviews_and_invalid_records_create_no_file(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    review = read_annotation(examples[0][1])
    path = tmp_path / "review.json"
    write_annotation(path, review)
    before = path.read_bytes()
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        write_annotation(path, replace(review, annotation_id="replacement"))
    assert path.read_bytes() == before
    with pytest.raises(ValueError):
        write_annotation(tmp_path / "bad.json", replace(review, annotation_id=""))
    assert not (tmp_path / "bad.json").exists()
    with pytest.raises(FileExistsError):
        asyncio.run(generate_examples(path.parent))
    assert path.read_bytes() == before
