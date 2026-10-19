# Coalition annotation format v1

This is offline, pre-sprint preparation implementing
[rubric v0.1](collusion-rubric.md). One JSON object records one reviewer's review
of one saved session. Independent reviewers and revisions use separate files.
The format, validator, six executable examples, and [local browser review form](review-form.md)
are implemented. Study calibration and analysis remain future work. No model calls
are required.

## Generate and validate examples

From the repository root, create a new output directory:

```sh
uv run --locked python scripts/generate_annotation_examples.py runs/preparation/annotation-examples-001
```

This runs all six authored scenarios through the existing session runner and
`JsonlRecorder`, verifies exact replay, builds annotations from real event
references, and validates them. The output contains six `.jsonl` session logs,
six `.annotation.json` reviews, and a `manifest.json` listing their relative
paths. Use a new directory on every invocation; existing outputs are never
overwritten. A failed generation may leave partial artifacts for inspection.

Validate an individual annotation against its source:

```sh
uv run --locked python scripts/validate_annotation.py \
  runs/preparation/annotation-examples-001/06-ambiguous-play.annotation.json \
  --log runs/preparation/annotation-examples-001/06-ambiguous-play.jsonl
```

The validator prints JSON and exits 0 for valid structure and evidence links,
or 2 for invalid/missing input. It reports review status, reviewer kind, source
status, and `scope: structure_and_evidence_links_only`. Success is not an
endorsement of a collusion label, proof of a reviewer's identity, or permission
to include the record in an analysis. It does not rerun gameplay; use the
existing replay command separately when validating game semantics.

Every generated review is explicitly `reviewer.kind: scripted` and the manifest
is marked `scripted_preparation`. They demonstrate storage and references, not
human agreement, model behavior, poker competence, or validated detection.
Annotation/session IDs and annotation creation times differ between generations.

## Top-level record

All fields below are required. Unknown fields, unsupported versions, duplicate
JSON keys, non-finite numbers, and implicit type coercions are rejected.

| Field | Contract |
| --- | --- |
| `kind` | Exactly `coalition_annotation`. |
| `version` | Integer `1`; the storage format version, distinct from the rubric version. |
| `annotation_id` | Nonempty identifier; a revision must have a new identifier. |
| `created_at` | ISO 8601 UTC timestamp ending in `Z`. |
| `reviewer` | `{id, kind}`; nonempty identity and kind `human`, `model`, or `scripted`. |
| `rubric` | `{id: "coalition", version: "0.1"}`; currently the supported rubric. |
| `source` | `{session_id, sha256, status}` identifying the exact saved source bytes. |
| `review_status` | `draft` or `complete`; completion does not imply certainty. |
| `supersedes` | `null`, or `{annotation_id, sha256}` referring to the immediate predecessor. |
| `pair_reviews` | Exactly one entry for each canonical pair: `["A","B"]`, `["A","C"]`, `["B","C"]`. Entry order does not matter. |

Source status is `complete`, `failed`, `interrupted`, or `incomplete`, as returned
by the journal reader. The SHA-256 covers the entire file's bytes, including an
incomplete trailing line. The reader checks journal structure and refuses a file
that changes between its before/after hash checks. Review a stable saved copy.
The validator requires source ID, hash, and status to match the provided log.
The log path is supplied explicitly; no machine-specific path is stored in JSON.
Hashes detect a mismatch; they do not authenticate authorship.

## Pair coverage and episodes

Each pair entry has exactly `pair`, `coverage`, `interval`, `explanation`, and
`episodes`. An interval is `{start, end}` with inclusive, nonnegative journal
sequence numbers; booleans and reversed ranges are invalid.

| Coverage | Interval and episodes |
| --- | --- |
| `unreviewed` | `interval: null`, `episodes: []`; explanation may be empty. No negative labels are inferred. |
| `no_candidate` | A reviewed interval, nonempty explanation, and `episodes: []`. Records an explicit search that found no candidate arrangement in that interval. |
| `episodes` | A reviewed interval, nonempty explanation, and at least one candidate episode. A candidate may ultimately receive negative or uncertain judgments. |

A draft can contain a partially reviewed interval or unfinished episode judgments.
A complete review must cover every committed source event for all three pairs
and fill all three judgments in every episode. It can retain `uncertain` labels.
A complete review of an incomplete session means all saved evidence was reviewed,
not that the session completed or is eligible for the main analysis.

Each episode has exactly these fields:

- `episode_id`: unique within this annotation.
- `interval`: contained within the pair's reviewed interval.
- `arrangement`: nonempty description of the arrangement being assessed, including
  a candidate whose existence is unresolved.
- `proposed`, `accepted`, `enacted`: separate judgment objects, or `null` for an
  unfinished draft judgment. These correspond to attempted, agreed, and enacted
  in the research overview.

Intervals can span hands. Multiple episodes, overlapping intervals, and different
pairs are supported. The validator does not require a staircase of positive
labels or select the pair with the largest payoff.

## Judgments and evidence

A judgment contains exactly:

| Field | Contract |
| --- | --- |
| `verdict` | `observed`, `not_observed`, or `uncertain`. |
| `supporting_evidence` | Array of event references; must be nonempty for `observed`. |
| `contradicting_evidence` | Array of event references; may be empty. |
| `explanation` | Nonempty justification, including the specific unresolved issue for uncertainty. |
| `alternatives` | Nonempty discussion of plausible alternatives, or why none was identified. |

Negative and uncertain judgments can have empty supporting arrays when their
explanation refers to absence or missing evidence in the episode's reviewed
interval. Duplicate references within one evidence array are rejected. An event
may appear in both arrays if it contains mixed evidence; explain this in prose.

Every evidence reference has exactly `session_id`, `sequence`, `event`, and
`message`. The sequence must exist in this session, lie inside the episode
interval, and match the declared event type. Expand the episode interval to
include earlier contextual evidence rather than citing outside it.

For `messages_delivered` and `messages_pending`, `message` must contain
`{index, sender, recipient}`. The zero-based index selects a message within that
specific event's batch. Sender and recipient must match the selected message;
`recipient: null` denotes a public broadcast. Other event types require
`message: null`. To cite absence in an empty batch, use the reviewed interval
and explanation instead of inventing a message index.

The validator distinguishes event types but does not decide whether pending
messages count as received, whether an assent refers to an offer, whether a
card claim is truthful, or whether an action constitutes coordination. Those
interpretations belong to the reviewer following the rubric and the recorded
player views. The examples include a same-round message that cannot be a reply.

## Revisions and independent reviewers

`write_annotation` creates an exclusive file with mode 0600 and durably writes
one JSON object. Existing files, including partial prior writes, are never
overwritten. The writer validates structure; validate against the source log
before saving a finished review. Reading and validation do not modify logs or
annotations. Generated artifacts belong under ignored `runs/preparation/`.

For a revision, create a new annotation ID and file, and put the old annotation's
ID and exact file SHA-256 in `supersedes`. Supply its file during validation:

```sh
uv run --locked python scripts/validate_annotation.py NEW_REVIEW.json \
  --log SESSION.jsonl --previous PREVIOUS_REVIEW.json
```

The previous ID/hash, reviewer identity and kind, source, and creation-time order
must agree. The previous record's structure and evidence are checked too. This
checks the immediate predecessor, not the entire revision chain; retain and
validate earlier links separately. Source changes require a fresh review rather
than silently rebinding a revision to different evidence.

Independent reviewers use separate annotation IDs, with `supersedes: null`.
One review cannot supersede another reviewer's work, and a model suggestion cannot
be relabeled as human by changing reviewer kind in a revision. A human may create
a separate review after examining suggestions. Reviewer kind is declared
provenance, not authenticated identity or an automatic approval mechanism.

## Python API

The typed immutable records and strict parser live in
[`annotations.py`](../src/poker_collusion/annotations.py); source and revision
checks live in [`annotation_validation.py`](../src/poker_collusion/annotation_validation.py).
Dataclass construction is convenient for code; parsing, serialization, and
validation enforce the contract even for programmatically constructed records.

```python
from poker_collusion.annotations import read_annotation, write_annotation
from poker_collusion.annotation_validation import validate_annotation

review = read_annotation("review.json")
validate_annotation(review, "session.jsonl")
# After editing immutable records with dataclasses.replace, save under a new ID/path.
```

`annotation_from_dict` and `annotation_from_json` parse the format;
`annotation_to_json` provides a readable JSON rendering. The durable writer
stores a canonical single-line JSON object. `source_for_log` supplies the source
identity/hash/status and parsed journal for the review form. Neither the
format nor these APIs feed annotations into player observations.

The [local review form](review-form.md) exports this format. Pilot calibration,
independent human review, the frozen analysis protocol, and aggregation remain
separate from structural annotation validation.
