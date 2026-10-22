"""Versioned coalition reviews. Parsing checks structure, never scientific judgments."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import cast

from poker_collusion.durable_jsonl import DurableJsonl
from poker_collusion.event_log import EVENT_TYPES

PAIRS = (("A", "B"), ("A", "C"), ("B", "C"))
RUBRIC_ID = "coalition"
RUBRIC_VERSION = "0.2"


class Verdict(StrEnum):
    OBSERVED = "observed"
    NOT_OBSERVED = "not_observed"
    UNCERTAIN = "uncertain"


class ReviewerKind(StrEnum):
    HUMAN = "human"
    MODEL = "model"
    SCRIPTED = "scripted"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    COMPLETE = "complete"


class Coverage(StrEnum):
    UNREVIEWED = "unreviewed"
    NO_CANDIDATE = "no_candidate"
    EPISODES = "episodes"


@dataclass(frozen=True)
class Interval:
    start: int
    end: int  # Inclusive journal sequence bounds.


@dataclass(frozen=True)
class MessageReference:
    index: int  # Zero-based position within this event's batch.
    sender: str
    recipient: str | None


@dataclass(frozen=True)
class EvidenceReference:
    session_id: str
    sequence: int
    event: str
    message: MessageReference | None = None


@dataclass(frozen=True)
class Judgment:
    verdict: Verdict
    supporting_evidence: tuple[EvidenceReference, ...]
    contradicting_evidence: tuple[EvidenceReference, ...]
    explanation: str


@dataclass(frozen=True)
class Episode:
    episode_id: str
    interval: Interval
    arrangement: str
    proposed: Judgment | None
    accepted: Judgment | None
    enacted: Judgment | None


@dataclass(frozen=True)
class PairReview:
    pair: tuple[str, str]
    coverage: Coverage
    interval: Interval | None
    episodes: tuple[Episode, ...]


@dataclass(frozen=True)
class Source:
    session_id: str
    sha256: str
    status: str


@dataclass(frozen=True)
class Reviewer:
    id: str
    kind: ReviewerKind


@dataclass(frozen=True)
class Rubric:
    id: str
    version: str


@dataclass(frozen=True)
class RevisionReference:
    annotation_id: str
    sha256: str


@dataclass(frozen=True)
class Annotation:
    annotation_id: str
    created_at: str
    reviewer: Reviewer
    rubric: Rubric
    source: Source
    review_status: ReviewStatus
    supersedes: RevisionReference | None
    pair_reviews: tuple[PairReview, ...]


def _record(value: object, fields: str, path: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(f"{path}: expected exactly these fields: {fields}")
    return cast(dict[str, object], value)


def _text(value: object, path: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{path}: expected {'a' if empty else 'a nonempty'} string")
    return value


def _integer(value: object, path: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{path}: expected a nonnegative integer")
    return value


def _hash(value: object, path: str) -> str:
    text = _text(value, path)
    if re.fullmatch(r"[0-9a-f]{64}", text) is None:
        raise ValueError(f"{path}: expected a lowercase SHA-256 digest")
    return text


def _items(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{path}: expected an array")
    return cast(list[object], value)


def _interval(value: object, path: str) -> Interval:
    row = _record(value, "start end", path)
    result = Interval(_integer(row["start"], path), _integer(row["end"], path))
    if result.start > result.end:
        raise ValueError(f"{path}: reversed interval")
    return result


def _evidence(value: object, path: str) -> EvidenceReference:
    row = _record(value, "session_id sequence event message", path)
    name = _text(row["event"], path)
    if name not in EVENT_TYPES:
        raise ValueError(f"{path}: unknown event type")
    message = None
    if row["message"] is not None:
        msg = _record(row["message"], "index sender recipient", path + ".message")
        sender = _text(msg["sender"], path)
        recipient = None if msg["recipient"] is None else _text(msg["recipient"], path)
        if sender not in "ABC" or len(sender) != 1 or recipient not in (None, "A", "B", "C"):
            raise ValueError(f"{path}: invalid message identities")
        if recipient == sender:
            raise ValueError(f"{path}: self-message is not supported")
        message = MessageReference(_integer(msg["index"], path), sender, recipient)
    if (name in {"messages_pending", "messages_delivered"}) != (message is not None):
        raise ValueError(
            f"{path}: message batches require a message selector; other events forbid it"
        )
    return EvidenceReference(
        _text(row["session_id"], path), _integer(row["sequence"], path), name, message
    )


def _judgment(value: object, path: str) -> Judgment | None:
    if value is None:
        return None
    row = _record(value, "verdict supporting_evidence contradicting_evidence explanation", path)
    verdict = Verdict(_text(row["verdict"], path + ".verdict"))
    evidence = []
    for field in ("supporting_evidence", "contradicting_evidence"):
        refs = tuple(
            _evidence(item, f"{path}.{field}[{index}]")
            for index, item in enumerate(_items(row[field], path + "." + field))
        )
        if len(set(refs)) != len(refs):
            raise ValueError(f"{path}.{field}: duplicate evidence reference")
        evidence.append(refs)
    if verdict == Verdict.OBSERVED and not evidence[0]:
        raise ValueError(f"{path}: observed requires supporting evidence")
    return Judgment(
        verdict,
        evidence[0],
        evidence[1],
        _text(row["explanation"], path + ".explanation"),
    )


def _episode(value: object, path: str) -> Episode:
    row = _record(value, "episode_id interval arrangement proposed accepted enacted", path)
    return Episode(
        _text(row["episode_id"], path),
        _interval(row["interval"], path + ".interval"),
        _text(row["arrangement"], path + ".arrangement"),
        _judgment(row["proposed"], path + ".proposed"),
        _judgment(row["accepted"], path + ".accepted"),
        _judgment(row["enacted"], path + ".enacted"),
    )


def _pair(value: object, path: str) -> PairReview:
    row = _record(value, "pair coverage interval episodes", path)
    pair = tuple(_text(item, path) for item in _items(row["pair"], path + ".pair"))
    if pair not in PAIRS:
        raise ValueError(f"{path}: expected a canonical pair: A-B, A-C, or B-C")
    coverage = Coverage(_text(row["coverage"], path + ".coverage"))
    interval = None if row["interval"] is None else _interval(row["interval"], path)
    episodes = tuple(
        _episode(item, f"{path}.episodes[{index}]")
        for index, item in enumerate(_items(row["episodes"], path + ".episodes"))
    )
    if coverage == Coverage.UNREVIEWED:
        if interval is not None or episodes:
            raise ValueError(f"{path}: unreviewed requires null interval and no episodes")
    elif interval is None or (coverage == Coverage.EPISODES) != bool(episodes):
        raise ValueError(f"{path}: reviewed coverage requires an interval and consistent episodes")
    return PairReview(pair, coverage, interval, episodes)


def annotation_from_dict(value: object) -> Annotation:
    """Reject unknown fields, implicit coercion, and inconsistent review states."""
    row = _record(
        value,
        "kind version annotation_id created_at reviewer rubric source review_status "
        "supersedes pair_reviews",
        "annotation",
    )
    if (
        row["kind"] != "coalition_annotation"
        or type(row["version"]) is not int
        or row["version"] != 2
    ):
        raise ValueError("Unsupported annotation schema")
    reviewer = _record(row["reviewer"], "id kind", "reviewer")
    rubric = _record(row["rubric"], "id version", "rubric")
    if rubric != {"id": RUBRIC_ID, "version": RUBRIC_VERSION}:
        raise ValueError("Unsupported rubric; expected coalition version 0.2")
    source = _record(row["source"], "session_id sha256 status", "source")
    status = _text(source["status"], "source.status")
    if status not in {"complete", "failed", "interrupted", "incomplete"}:
        raise ValueError("Unknown source status")
    created = _text(row["created_at"], "created_at")
    if "T" not in created or not created.endswith("Z"):
        raise ValueError("created_at: expected an ISO 8601 UTC timestamp ending in Z")
    datetime.fromisoformat(created)
    previous = None
    if row["supersedes"] is not None:
        prior = _record(row["supersedes"], "annotation_id sha256", "supersedes")
        previous = RevisionReference(
            _text(prior["annotation_id"], "supersedes.annotation_id"),
            _hash(prior["sha256"], "supersedes.sha256"),
        )
    result = Annotation(
        _text(row["annotation_id"], "annotation_id"),
        created,
        Reviewer(
            _text(reviewer["id"], "reviewer.id"),
            ReviewerKind(_text(reviewer["kind"], "reviewer.kind")),
        ),
        Rubric(RUBRIC_ID, RUBRIC_VERSION),
        Source(
            _text(source["session_id"], "source.session_id"),
            _hash(source["sha256"], "source.sha256"),
            status,
        ),
        ReviewStatus(_text(row["review_status"], "review_status")),
        previous,
        tuple(
            _pair(item, f"pair_reviews[{index}]")
            for index, item in enumerate(_items(row["pair_reviews"], "pair_reviews"))
        ),
    )
    if len(result.pair_reviews) != 3 or {p.pair for p in result.pair_reviews} != set(PAIRS):
        raise ValueError("Exactly one review entry is required for each of the three pairs")
    ids = [e.episode_id for p in result.pair_reviews for e in p.episodes]
    if len(set(ids)) != len(ids):
        raise ValueError("Episode identifiers must be unique within the annotation")
    if previous is not None and previous.annotation_id == result.annotation_id:
        raise ValueError("A revision requires a new annotation identifier")
    if result.review_status == ReviewStatus.COMPLETE:
        for pair in result.pair_reviews:
            if pair.coverage == Coverage.UNREVIEWED:
                raise ValueError("A complete review cannot contain an unreviewed pair")
            if any(j is None for e in pair.episodes for j in (e.proposed, e.accepted, e.enacted)):
                raise ValueError("A complete review requires all three judgments per episode")
    return result


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    raise ValueError(f"Non-finite JSON number: {value}")


def annotation_from_json(payload: str | bytes) -> Annotation:
    try:
        value = json.loads(
            payload, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        return annotation_from_dict(value)
    except (UnicodeError, RecursionError) as error:
        raise ValueError(f"Invalid annotation JSON: {error}") from error


def annotation_to_json(annotation: Annotation) -> str:
    """Revalidate even programmatically constructed records before serialization."""
    payload = (
        json.dumps(
            {"kind": "coalition_annotation", "version": 2, **asdict(annotation)},
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
    annotation_from_json(payload)
    return payload


def read_annotation(path: str | Path) -> Annotation:
    return annotation_from_json(Path(path).read_bytes())


def write_annotation(path: str | Path, annotation: Annotation) -> None:
    """Create an exclusive, durable JSON file; never overwrite an earlier review."""
    payload = annotation_to_json(annotation)
    with DurableJsonl(path) as writer:
        writer.write(json.loads(payload))
