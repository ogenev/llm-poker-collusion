import asyncio
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import poker_collusion.analysis as analysis_module
from poker_collusion.analysis import analyze_session
from poker_collusion.annotation_examples import generate_examples
from poker_collusion.annotation_validation import source_for_log
from poker_collusion.annotations import (
    PAIRS,
    Coverage,
    Interval,
    PairReview,
    ReviewStatus,
    RevisionReference,
    read_annotation,
    write_annotation,
)
from poker_collusion.event_log import JsonlRecorder, read_log
from poker_collusion.records import (
    Channel,
    DealSchedule,
    Decision,
    PlayerView,
    SessionConfig,
    SessionState,
)
from poker_collusion.replay import ReplayError, replay_session
from poker_collusion.session import SessionInterrupted, passive_decider, run_session

pytestmark = pytest.mark.usefixtures("inspect_runtime")


@pytest.fixture(scope="module")
def examples(tmp_path_factory: pytest.TempPathFactory) -> tuple[tuple[Path, Path], ...]:
    return asyncio.run(
        generate_examples(tmp_path_factory.mktemp("analysis-integrity") / "examples")
    )


@pytest.mark.parametrize("status", ["failed", "interrupted"])
def test_failed_and_interrupted_sessions_replay_without_counting_unsettled_hands(
    tmp_path: Path,
    status: str,
) -> None:
    log = tmp_path / "partial.jsonl"

    async def decide(view: PlayerView) -> Decision:
        if view.hand_index == 1:
            if status == "interrupted":
                raise asyncio.CancelledError()
            raise RuntimeError("fixture failure")
        return await passive_decider(view)

    with JsonlRecorder(log) as recorder:
        try:
            asyncio.run(
                run_session(
                    SessionConfig(hands=2, channel=Channel.PRIVATE),
                    DealSchedule(0, 0, ((3, 1, 0),) * 2),
                    decide,
                    recorder=recorder,
                )
            )
        except SessionInterrupted:
            assert status == "interrupted"
    result = asyncio.run(analyze_session(log))
    assert result.source.status == status
    assert result.session.replay_verified
    assert result.session.completed_hands == result.session.settled_hands == 1
    assert result.session.player_payoffs == {"A": 2, "B": -1, "C": -1}
    assert result.session.failure is not None
    assert result.session.hands is not None and len(result.session.hands) == 2
    assert result.session.hands[1].player_payoffs is None
    assert result.session.hands[1].settlement_sequence is None
    assert result.outcomes.enacted.verdict is None


@pytest.mark.parametrize("cutoff", ["start", "settled", "memory", "footer"])
@pytest.mark.parametrize("tail", [b"", b'{"torn":'])
def test_incomplete_prefix_retains_status_and_hash_without_claiming_verified_totals(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
    cutoff: str,
    tail: bytes,
) -> None:
    full, template_path = examples[0]
    events = read_log(full).events
    count = {
        "start": 1,
        "footer": len(events) - 1,
        "settled": next(e.sequence for e in events if e.event == "rewards_settled") + 1,
        "memory": next(e.sequence for e in events if e.event == "memory_updated") + 1,
    }[cutoff]
    log = tmp_path / "prefix.jsonl"
    payload = b"".join(full.read_bytes().splitlines(keepends=True)[:count]) + tail
    log.write_bytes(payload)
    source, _ = source_for_log(log)
    review = replace(
        read_annotation(template_path),
        source=source,
        pair_reviews=tuple(
            PairReview(
                pair,
                Coverage.NO_CANDIDATE,
                Interval(0, count - 1),
                (),
            )
            for pair in PAIRS
        ),
    )
    annotation = tmp_path / "prefix-review.json"
    write_annotation(annotation, review)
    result = asyncio.run(analyze_session(log, annotation_path=annotation))
    assert result.source.status == "incomplete"
    assert result.source.sha256 == hashlib.sha256(payload).hexdigest()
    assert result.session.event_count == count
    assert result.session.trailing_bytes == len(tail)
    assert not result.session.replay_verified
    assert result.session.completed_hands is None and result.session.settled_hands is None
    assert result.session.player_payoffs is None and result.session.hands is None
    assert all(pair.payoffs is None for pair in result.pairs)
    assert result.review is not None and result.review.review_status == ReviewStatus.COMPLETE
    assert log.read_bytes() == payload


def test_annotation_requires_matching_source_and_real_evidence(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log, annotation = examples[3]
    with pytest.raises(ValueError, match="session ID"):
        asyncio.run(analyze_session(log, annotation_path=examples[4][1]))
    review = read_annotation(annotation)
    pair = review.pair_reviews[0]
    episode = pair.episodes[0]
    assert episode.proposed is not None
    judgment = replace(
        episode.proposed,
        supporting_evidence=(replace(episode.proposed.supporting_evidence[0], sequence=99999),),
    )
    changed = replace(
        review,
        pair_reviews=(
            replace(pair, episodes=(replace(episode, proposed=judgment),)),
            *review.pair_reviews[1:],
        ),
    )
    bad = tmp_path / "bad-ref.json"
    write_annotation(bad, changed)
    with pytest.raises(ValueError, match="does not exist"):
        asyncio.run(analyze_session(log, annotation_path=bad))


@pytest.mark.parametrize("field", ["rewards", "returns"])
def test_replay_rejects_tampered_payoffs_even_without_an_annotation(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
    field: str,
) -> None:
    rows = [json.loads(line) for line in examples[3][0].read_bytes().splitlines()]
    event = next(e for e in rows if e["event"] == "rewards_settled")
    if field == "rewards":
        event["data"][field]["A"] += 1
    else:
        event["data"][field][0] += 1
    path = tmp_path / "tampered.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ReplayError, match="differs"):
        asyncio.run(analyze_session(path))


def test_revision_requires_exact_immediate_predecessor(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log, original = examples[5]
    previous = tmp_path / "previous.json"
    previous.write_bytes(original.read_bytes())
    old = read_annotation(previous)
    revision = replace(
        old,
        annotation_id="revised-review",
        supersedes=RevisionReference(
            old.annotation_id,
            hashlib.sha256(previous.read_bytes()).hexdigest(),
        ),
    )
    selected = tmp_path / "revision.json"
    write_annotation(selected, revision)
    with pytest.raises(ValueError, match="requires the previous"):
        asyncio.run(analyze_session(log, annotation_path=selected))
    result = asyncio.run(analyze_session(log, annotation_path=selected, previous_path=previous))
    assert result.review is not None
    assert result.review.supersedes == revision.supersedes
    assert result.review.annotation_id == revision.annotation_id
    assert result.review.reviewer == old.reviewer
    previous.write_bytes(previous.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SHA-256"):
        asyncio.run(analyze_session(log, annotation_path=selected, previous_path=previous))
    with pytest.raises(ValueError, match="requires a selected"):
        asyncio.run(analyze_session(log, previous_path=original))
    with pytest.raises(ValueError, match="supersedes is null"):
        asyncio.run(analyze_session(log, annotation_path=original, previous_path=original))


@pytest.mark.parametrize("changed_input", ["journal", "annotation", "previous"])
def test_inputs_cannot_change_during_replay(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_input: str,
) -> None:
    log = tmp_path / "session.jsonl"
    log.write_bytes(examples[5][0].read_bytes())
    previous = tmp_path / "previous.json"
    previous.write_bytes(examples[5][1].read_bytes())
    old = read_annotation(previous)
    selected = tmp_path / "revision.json"
    write_annotation(
        selected,
        replace(
            old,
            annotation_id="revision",
            supersedes=RevisionReference(
                old.annotation_id,
                hashlib.sha256(previous.read_bytes()).hexdigest(),
            ),
        ),
    )
    original_replay = replay_session

    async def replay_then_change(path: str | Path) -> SessionState:
        state = await original_replay(path)
        change = {"journal": log, "annotation": selected, "previous": previous}[changed_input]
        change.write_bytes(change.read_bytes() + b"\n")
        return state

    monkeypatch.setattr(analysis_module, "replay_session", replay_then_change)
    with pytest.raises(ValueError, match="input changed"):
        asyncio.run(analyze_session(log, annotation_path=selected, previous_path=previous))


def test_cli_outputs_structured_results_and_never_overwrites_inputs(
    examples: tuple[tuple[Path, Path], ...],
    tmp_path: Path,
) -> None:
    log, annotation = examples[3]
    output = tmp_path / "analysis.json"
    command = [
        sys.executable,
        "scripts/analyze_session.py",
        str(log),
        "--annotation",
        str(annotation),
        "--output",
        str(output),
    ]
    success = subprocess.run(command, capture_output=True, text=True, check=False)
    assert success.returncode == 0, success.stderr
    assert json.loads(success.stdout)["replay_verified"] is True
    assert json.loads(output.read_bytes())["review"]["reviewer"]["kind"] == "scripted"
    saved = output.read_bytes()
    duplicate = subprocess.run(command, capture_output=True, text=True, check=False)
    assert duplicate.returncode == 2
    assert json.loads(duplicate.stdout)["analyzed"] is False
    assert output.read_bytes() == saved
    originals = (log.read_bytes(), annotation.read_bytes())
    for destination in (log, annotation):
        command[-1] = str(destination)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        assert result.returncode == 2
    assert originals == (log.read_bytes(), annotation.read_bytes())
    bad_output = tmp_path / "invalid-analysis.json"
    command[-1] = str(bad_output)
    command[4] = str(examples[4][1])
    invalid = subprocess.run(command, capture_output=True, text=True, check=False)
    assert invalid.returncode == 2
    assert "session ID" in json.loads(invalid.stdout)["error"]
    assert not bad_output.exists()


def test_empty_and_malformed_inputs_fail_explicitly(tmp_path: Path) -> None:
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="empty journal"):
        asyncio.run(analyze_session(empty))
    invalid = tmp_path / "invalid.jsonl"
    invalid.write_bytes(b"not-json\n")
    with pytest.raises(ValueError, match="Invalid journal"):
        asyncio.run(analyze_session(invalid))
