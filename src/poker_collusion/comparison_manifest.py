"""Explicit dataset/review selection for offline matched comparisons, schema v1."""

from dataclasses import dataclass
from pathlib import Path

from poker_collusion.annotations import ReviewerKind, _items, _record, _text
from poker_collusion.model_adapter import _read_object
from poker_collusion.records import require_int


@dataclass(frozen=True)
class Bootstrap:
    replicates: int
    seed: int
    confidence: float


@dataclass(frozen=True)
class ReviewSelection:
    sample_id: str
    annotation: Path
    previous: Path | None


@dataclass(frozen=True)
class RunSelection:
    directory: Path
    reviews: tuple[ReviewSelection, ...]


@dataclass(frozen=True)
class ComparisonManifest:
    dataset_role: str
    reviewer_kind: ReviewerKind
    bootstrap: Bootstrap
    runs: tuple[RunSelection, ...]


def parse_manifest(payload: str, base: Path) -> ComparisonManifest:
    row = _record(
        _read_object(payload), "kind version dataset_role reviewer_kind bootstrap runs", "manifest"
    )
    if (
        row["kind"] != "session_comparison"
        or type(row["version"]) is not int
        or row["version"] != 1
    ):
        raise ValueError("Unsupported comparison manifest")
    role = _text(row["dataset_role"], "dataset_role")
    if role not in ("preparation", "pilot", "evaluation"):
        raise ValueError("Unknown dataset_role")
    kind = ReviewerKind(_text(row["reviewer_kind"], "reviewer_kind"))
    if kind == ReviewerKind.MODEL or (role != "preparation" and kind != ReviewerKind.HUMAN):
        raise ValueError("Pilot/evaluation require human reviews; scripted reviews are preparation")
    settings = _record(row["bootstrap"], "replicates seed confidence", "bootstrap")
    replicates = require_int(settings["replicates"], "replicates")
    seed = require_int(settings["seed"], "seed")
    confidence = settings["confidence"]
    if not 100 <= replicates <= 10000:
        raise ValueError("bootstrap replicates must be between 100 and 10000")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, int | float)
        or not 0 < confidence < 1
    ):
        raise ValueError("bootstrap confidence must be between zero and one")
    runs = []
    for value in _items(row["runs"], "runs"):
        run = _record(value, "directory reviews", "run")
        directory = base / _text(run["directory"], "directory")
        reviews = []
        for item in _items(run["reviews"], "reviews"):
            review = _record(item, "sample_id annotation previous", "review")
            reviews.append(
                ReviewSelection(
                    _text(review["sample_id"], "sample_id"),
                    base / _text(review["annotation"], "annotation"),
                    None
                    if review["previous"] is None
                    else base / _text(review["previous"], "previous"),
                )
            )
        if len({review.sample_id for review in reviews}) != len(reviews):
            raise ValueError("Select at most one review per sample")
        runs.append(RunSelection(directory, tuple(reviews)))
    if not runs or len({run.directory.resolve() for run in runs}) != len(runs):
        raise ValueError("runs must be nonempty and distinct")
    return ComparisonManifest(
        role, kind, Bootstrap(replicates, seed, float(confidence)), tuple(runs)
    )
