import asyncio
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from poker_collusion.annotation_examples import generate_examples
from poker_collusion.annotation_validation import source_for_log, validate_annotation
from poker_collusion.annotations import (
    Interval,
    Reviewer,
    ReviewerKind,
    ReviewStatus,
    RevisionReference,
    Verdict,
    read_annotation,
    write_annotation,
)
from poker_collusion.event_log import read_log


@pytest.fixture(scope="module")
def examples(tmp_path_factory: pytest.TempPathFactory) -> tuple[tuple[Path, Path], ...]:
    return asyncio.run(generate_examples(tmp_path_factory.mktemp("annotation-links") / "examples"))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("session", "another session"),
        ("missing", "does not exist"),
        ("event", "has type"),
        ("message_index", "outside event"),
        ("sender", "sender/recipient"),
        ("recipient", "sender/recipient"),
        ("episode_interval", "outside its episode"),
        ("episode_bounds", "outside the reviewed"),
        ("pair_bounds", "outside the reviewed"),
        ("partial_complete", "entire saved journal"),
    ],
)
def test_broken_evidence_and_coverage_are_rejected(
    examples: tuple[tuple[Path, Path], ...],
    change: str,
    message: str,
) -> None:
    log_path, review_path = examples[3]
    review = read_annotation(review_path)
    pair = review.pair_reviews[0]
    episode = pair.episodes[0]
    judgment = episode.proposed
    assert judgment is not None
    ref = judgment.supporting_evidence[0]
    selector, interval = ref.message, pair.interval
    assert selector is not None and interval is not None
    if change == "session":
        ref = replace(ref, session_id="another-session")
    elif change == "missing":
        ref = replace(ref, sequence=1_000_000)
    elif change == "event":
        ref = replace(ref, event="action_applied", message=None)
    elif change == "message_index":
        ref = replace(ref, message=replace(selector, index=100))
    elif change == "sender":
        ref = replace(ref, message=replace(selector, sender="C"))
    elif change == "recipient":
        ref = replace(ref, message=replace(selector, recipient="C"))
    elif change == "episode_interval":
        episode = replace(episode, interval=Interval(ref.sequence + 1, episode.interval.end))
    elif change == "episode_bounds":
        episode = replace(episode, interval=Interval(0, interval.end + 1))
    elif change == "pair_bounds":
        pair = replace(pair, interval=Interval(0, interval.end + 1))
    else:
        pair = replace(pair, interval=Interval(1, interval.end))
    episode = replace(episode, proposed=replace(judgment, supporting_evidence=(ref,)))
    review = replace(
        review, pair_reviews=(replace(pair, episodes=(episode,)), *review.pair_reviews[1:])
    )
    with pytest.raises(ValueError, match=message):
        validate_annotation(review, log_path)


def test_source_digest_identity_and_status_are_checked_without_modifying_logs(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log_path, review_path = examples[3]
    review = read_annotation(review_path)
    before = log_path.read_bytes()
    for source, message in [
        (replace(review.source, sha256="0" * 64), "SHA-256"),
        (replace(review.source, session_id="wrong"), "session ID"),
        (replace(review.source, status="failed"), "status"),
    ]:
        with pytest.raises(ValueError, match=message):
            validate_annotation(replace(review, source=source), log_path)
    changed = tmp_path / "changed.jsonl"
    changed.write_bytes(before.replace(b"Agreed.", b"Maybe."))
    with pytest.raises(ValueError, match="SHA-256"):
        validate_annotation(review, changed)
    assert log_path.read_bytes() == before
    assert changed.read_bytes() != before
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="empty journal"):
        source_for_log(empty)


def test_incomplete_source_can_have_a_completed_review_with_uncertain_enactment(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log_path, review_path = examples[2]
    log = read_log(log_path)
    cutoff = [event.sequence for event in log.events if event.event == "messages_delivered"][-1]
    prefix = tmp_path / "prefix.jsonl"
    prefix.write_bytes(
        b"".join(log_path.read_bytes().splitlines(keepends=True)[: cutoff + 1]) + b'{"torn":'
    )
    source, partial_log = source_for_log(prefix)
    assert source.status == "incomplete" and partial_log.trailing_bytes > 0
    review = read_annotation(review_path)
    pair = review.pair_reviews[0]
    episode = pair.episodes[0]
    assert episode.enacted is not None
    unknown = replace(
        episode.enacted,
        verdict=Verdict.UNCERTAIN,
        supporting_evidence=(),
        contradicting_evidence=(),
        explanation="The saved log stops before betting. Follow-through cannot be assessed.",
    )
    whole = Interval(0, cutoff)
    episode = replace(episode, interval=Interval(episode.interval.start, cutoff), enacted=unknown)
    review = replace(
        review,
        source=source,
        pair_reviews=(
            replace(pair, interval=whole, episodes=(episode,)),
            *(replace(p, interval=whole) for p in review.pair_reviews[1:]),
        ),
    )
    validate_annotation(review, prefix)
    assert review.review_status == ReviewStatus.COMPLETE
    assert review.source.status == "incomplete"
    assert review.pair_reviews[0].episodes[0].enacted == unknown


def test_revision_requires_exact_predecessor_and_keeps_both_records(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log_path, original_path = examples[5]
    original_bytes = original_path.read_bytes()
    original = read_annotation(original_path)
    revision = replace(
        original,
        annotation_id="revised",
        supersedes=RevisionReference(
            original.annotation_id, hashlib.sha256(original_bytes).hexdigest()
        ),
    )
    with pytest.raises(ValueError, match="requires the previous"):
        validate_annotation(revision, log_path)
    validate_annotation(revision, log_path, previous_path=original_path)
    new_path = tmp_path / "revision.json"
    write_annotation(new_path, revision)
    validate_annotation(read_annotation(new_path), log_path, previous_path=original_path)
    assert original_path.read_bytes() == original_bytes
    with pytest.raises(ValueError, match="supersedes is null"):
        validate_annotation(original, log_path, previous_path=original_path)
    for changed, message in [
        (
            replace(revision, supersedes=RevisionReference(original.annotation_id, "0" * 64)),
            "SHA-256",
        ),
        (
            replace(
                revision,
                supersedes=RevisionReference("wrong", hashlib.sha256(original_bytes).hexdigest()),
            ),
            "ID",
        ),
        (
            replace(revision, reviewer=Reviewer("someone-else", ReviewerKind.SCRIPTED)),
            "reviewer identity",
        ),
        (
            replace(revision, reviewer=replace(original.reviewer, kind=ReviewerKind.HUMAN)),
            "reviewer identity",
        ),
        (replace(revision, created_at="2000-01-01T00:00:00Z"), "creation time"),
        (replace(revision, annotation_id=original.annotation_id), "new annotation identifier"),
    ]:
        with pytest.raises(ValueError, match=message):
            validate_annotation(changed, log_path, previous_path=original_path)


def test_validator_does_not_upgrade_model_suggestions_to_human_reviews(
    examples: tuple[tuple[Path, Path], ...],
) -> None:
    log_path, review_path = examples[5]
    suggestion = replace(
        read_annotation(review_path), reviewer=Reviewer("example-model", ReviewerKind.MODEL)
    )
    before = suggestion
    validate_annotation(suggestion, log_path)
    assert suggestion == before
    assert suggestion.reviewer.kind == ReviewerKind.MODEL
    assert suggestion.pair_reviews[0].episodes[0].accepted is not None
    assert suggestion.pair_reviews[0].episodes[0].accepted.verdict == Verdict.UNCERTAIN


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_generation_and_validation_cli_and_nonzero_failures(tmp_path: Path) -> None:
    directory = tmp_path / "generated"
    result = _cli("scripts/generate_annotation_examples.py", str(directory))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["examples"] == 6
    manifest: dict[str, Any] = json.loads((directory / "manifest.json").read_text())
    assert manifest["data_kind"] == "scripted_preparation"
    first = manifest["examples"][0]
    annotation_path, log_path = directory / first["annotation"], directory / first["log"]
    before = {path: path.read_bytes() for path in directory.iterdir()}
    result = _cli("scripts/validate_annotation.py", str(annotation_path), "--log", str(log_path))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["valid"] and report["reviewer_kind"] == "scripted"
    assert report["scope"] == "structure_and_evidence_links_only"
    result = _cli("scripts/generate_annotation_examples.py", str(directory))
    assert result.returncode == 2 and not json.loads(result.stdout)["generated"]
    assert {path: path.read_bytes() for path in directory.iterdir()} == before
    result = _cli(
        "scripts/validate_annotation.py", str(annotation_path), "--log", str(tmp_path / "missing")
    )
    assert result.returncode == 2 and not json.loads(result.stdout)["valid"]
    annotation_path.write_text('{"kind": "bad"}\n')
    result = _cli("scripts/validate_annotation.py", str(annotation_path), "--log", str(log_path))
    assert result.returncode == 2 and not json.loads(result.stdout)["valid"]
