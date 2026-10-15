# Session recording protocol v1

This is Phase 1 framework preparation. It records the existing
[session protocol](session-protocol.md) without changing player observations,
communication opportunities, or game mechanics. No model experiment has been
run. Inspect integration, provider prompts, usage, and model provenance follow
this milestone; recovery and intervention execution remain Phase 2.

## File and durability contract

`JsonlRecorder(path, session_id=None, run_id=None, matched_block_id=None)` creates
one new UTF-8 JSONL file for one session attempt. The default session identifier
is a UUID; optional identifiers are trusted audit metadata. Use a new path and
session identifier for every rerun and retain the earlier attempt. The recorder
never appends another session to an existing file or silently replaces one.

Each event is serialized to one newline-terminated line, flushed, and fsynced
before the runner continues. The first event also syncs the containing directory.
Durability depends on the filesystem honoring these operations. Files are created
with mode 0600. The complete audit contains hidden cards, all private messages,
and all player histories; only `PlayerView` crosses the player boundary.

Audit serialization happens at the writer or replay verifier, with no intermediate
JSON round trips in the session runner. A run without a recorder performs no audit
serialization. Custom `EventSink` implementations receive protocol dataclasses and
live state mappings; they must serialize or copy each event synchronously before
returning, so later state changes cannot alter earlier evidence.

Persistence errors abort execution and raise `RecordingError`. They do not
become callback failures or trigger retries or substitute decisions. Prior
committed events remain available; no completion footer is fabricated. An
abrupt process exit can leave a prefix or torn last line. This is not a resume
mechanism or a guarantee that an in-flight external call returned nothing.

## Envelope and identifiers

Every line has exactly these fields:

| Field | Meaning |
| --- | --- |
| `kind`, `version` | `session_event`, integer `1` |
| `session_id` | Same nonempty identifier throughout the file |
| `sequence` | Contiguous zero-based event number |
| `event` | One of the event names below |
| `data` | Event-specific object |
| `metadata` | Optional `run_id` and `matched_block_id`, constant throughout |

The pair `(session_id, sequence)` identifies an event. Requests use contiguous
zero-based `request_id` values within the session. Hand indexes and request
views supply decision coordinates. These identifiers never enter player views
or delivered messages. Snapshot and branch identifiers are deferred to Phase 2.

The initial event contains protocol version 1, versioned `session_config` and
`deal_schedule` records, and SHA-256 hashes of their canonical JSON. Canonical
JSON sorts object keys, escapes non-ASCII characters, disallows nonfinite JSON
numbers, and uses compact separators. The exact saved schedule is authoritative;
replay does not regenerate it from its seed. Hashes detect configuration changes,
not authenticated authorship. Software/dependency versions must still be retained
with the run; the repository lockfile defines this implementation's environment.

## Events

| Event | Recorded evidence |
| --- | --- |
| `session_started` | Protocol, configuration, exact schedule, hashes |
| `phase_changed` | Phase and hand/round/player cursor |
| `hand_dealt` | Seat mapping, hidden poker snapshot, reset budgets |
| `decision_requested` | Request identifier and exact immutable player view |
| `decision_returned` | Exact supported callback response, including invalid output |
| `decision_resolved` | Validated decision or failure with source coordinates |
| `request_cancelled` | Request cancelled without a completed outcome |
| `messages_pending` | Accepted sends in identity order, including failed rounds |
| `messages_delivered` | Delivered messages and resulting sender budgets |
| `action_applied` | Acting identity, action, resulting poker snapshot |
| `rewards_settled` | Seat rewards and accumulated identity rewards |
| `memory_updated` | Completed-hand views, retained histories, completed-hand count |
| `session_failed` / `session_interrupted` | Primary failure and source coordinates |
| `session_ended` | Versioned terminal state, including configuration and schedule |

All round views are frozen and recorded before callbacks start. Responses are
recorded in arrival order as soon as each callback finishes. Validated decisions
are durable before any action, budget charge, or delivery. Delivery still waits
for the entire round and orders messages by sender identity. Failed rounds
retain valid pending messages without delivery or budget charges. Interrupted
rounds retain all observed responses, including those that have not reached the
pending-message collection step; cancellation before a callback starts is also
explicitly recorded. Timeouts and callback exceptions have failure outcomes
without invented responses. There are no automatic retries.

Response encoding preserves the exact decision classes, `Action` enums versus
invalid strings, malformed fields, JSON-like containers, and Unicode text.
Unsupported Python objects, cyclic references, nesting beyond 16 levels, and
integers exceeding Python's string-conversion limit retain a class name and
`repr` diagnostic (or an explicit unavailable marker). These values are marked
`unsupported`; they are invalid decisions and cannot be reconstructed exactly.
Valid protocol decisions need at most two nesting levels and are preserved
exactly. Validation precedes audit encoding, and malformed values yield explicit
failed sessions rather than serialization crashes. No pickle or executable class
loading is used. Future Inspect integration must separately preserve actual provider prompts and raw
model outputs; this increment captures the scripted callback boundary.

The audit retains all completed-hand observations even when `memory_hands=0`.
Retention only bounds what a player receives. The final state record is an audit
comparison target, not an independently loadable recovery checkpoint.

## Reading, replay, and result eligibility

`read_log(path)` checks envelope versions, identifiers, sequence continuity,
initial configuration and hashes, and request lifecycles. Duplicate JSON keys,
malformed committed lines, unsupported versions, and data after a terminal record
are errors. A final line without a newline is uncommitted: expose the preceding
events plus `trailing_bytes` and mark the journal incomplete. Never modify the
source during inspection. Structural status alone does not verify game semantics.

`await replay_session(path)` runs the same session engine using recorded outcomes
instead of callbacks. It reproduces response order and cancellation boundaries,
revalidates returned decisions, and compares every emitted event, including all
player views, delivery, actions, settlement, histories, and terminal state. It
makes no model calls, waits for no original timeout, and does not sample fresh
decisions. External exception details are retained as evidence, not re-created by
calling a provider. A mismatch raises `ReplayError`; corrupt input raises
`ValueError`. Missing terminal records raise `IncompleteLogError`.

| Status | Replay and analysis handling |
| --- | --- |
| `complete` | Must replay successfully before inclusion in complete-session results |
| `failed` | Replays to failed state; retain separately, never treat as a shorter success |
| `interrupted` | Replays a cleanly cancelled attempt to interrupted state; retain separately |
| `incomplete` | Inspect durable prefix only; exclude from complete-session results |

Replay of an interrupted log returns its partial state; live cancellation still
raises `SessionInterrupted`. Neither path resumes work. The CLI's successful
verification exit status means the recorded trajectory matches, including when
its session status is failed or interrupted. Pilot/evaluation handling of failures
must be frozen before collecting research results.
