"""Read-only annotation validation against saved journals and prior reviews."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from poker_collusion.annotations import (
    Annotation,
    EvidenceReference,
    Interval,
    ReviewStatus,
    Source,
    annotation_from_json,
    annotation_to_json,
)
from poker_collusion.event_log import SessionLog, read_log


def source_for_log(path: str | Path) -> tuple[Source, SessionLog]:
    """Bind to the exact bytes, including an incomplete tail; require a stable file."""
    path = Path(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    log = read_log(path)
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    if before != after:
        raise ValueError("Source journal changed while being read; use a stable saved log")
    if log.session_id is None or not log.events:
        raise ValueError("Cannot annotate an empty journal")
    return Source(log.session_id, before, log.status), log


def _bounds(interval: Interval, parent: Interval, label: str) -> None:
    if not parent.start <= interval.start <= interval.end <= parent.end:
        raise ValueError(f"{label}: interval is outside the reviewed source range")


def _reference(ref: EvidenceReference, log: SessionLog, interval: Interval) -> None:
    if ref.session_id != log.session_id:
        raise ValueError("Evidence references another session")
    if ref.sequence >= len(log.events):
        raise ValueError(f"Evidence event {ref.sequence} does not exist")
    if not interval.start <= ref.sequence <= interval.end:
        raise ValueError("Evidence is outside its episode interval")
    event = log.events[ref.sequence]
    if event.event != ref.event:
        raise ValueError(f"Evidence event {ref.sequence} has type {event.event}, not {ref.event}")
    if ref.message is not None:
        messages = event.data.get("messages")
        if not isinstance(messages, list) or ref.message.index >= len(messages):
            raise ValueError(f"Message index is outside event {ref.sequence}'s batch")
        message = messages[ref.message.index]
        if not isinstance(message, dict) or (
            message.get("sender") != ref.message.sender
            or message.get("recipient") != ref.message.recipient
        ):
            raise ValueError("Message sender/recipient does not match the selected evidence")


def _source_and_evidence(annotation: Annotation, source: Source, log: SessionLog) -> None:
    if annotation.source.session_id != source.session_id:
        raise ValueError("Annotation session ID does not match the source journal")
    if annotation.source.sha256 != source.sha256:
        raise ValueError("Source journal SHA-256 does not match the annotation")
    if annotation.source.status != source.status:
        raise ValueError("Source journal status does not match the annotation")
    whole = Interval(0, len(log.events) - 1)
    for pair in annotation.pair_reviews:
        if pair.interval is None:
            continue  # Structural parsing permits this only for an unreviewed pair.
        _bounds(pair.interval, whole, "Pair review")
        if annotation.review_status == ReviewStatus.COMPLETE and pair.interval != whole:
            raise ValueError("Complete reviews must cover the entire saved journal for every pair")
        for episode in pair.episodes:
            _bounds(episode.interval, pair.interval, "Episode")
            for judgment in (episode.proposed, episode.accepted, episode.enacted):
                if judgment is not None:
                    for ref in (*judgment.supporting_evidence, *judgment.contradicting_evidence):
                        _reference(ref, log, episode.interval)


def validate_annotation(
    annotation: Annotation,
    log_path: str | Path,
    *,
    previous_path: str | Path | None = None,
) -> None:
    """Validate structure, references, and an optional immediate revision link.

    This does not establish semantic correctness, reviewer identity, human approval,
    or eligibility for a research analysis. Full game replay is a separate check.
    """
    annotation = annotation_from_json(annotation_to_json(annotation))
    source, log = source_for_log(log_path)
    _source_and_evidence(annotation, source, log)
    revision = annotation.supersedes
    if revision is None:
        if previous_path is not None:
            raise ValueError("A previous annotation was supplied but supersedes is null")
        return
    if previous_path is None:
        raise ValueError("A revision requires the previous annotation file")
    payload = Path(previous_path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != revision.sha256:
        raise ValueError("Previous annotation SHA-256 does not match supersedes")
    previous = annotation_from_json(payload)
    if previous.annotation_id != revision.annotation_id:
        raise ValueError("Previous annotation ID does not match supersedes")
    if previous.reviewer != annotation.reviewer:
        raise ValueError("A revision must preserve reviewer identity and kind")
    _source_and_evidence(previous, source, log)
    if datetime.fromisoformat(annotation.created_at) < datetime.fromisoformat(previous.created_at):
        raise ValueError("Revision creation time precedes the previous annotation")
