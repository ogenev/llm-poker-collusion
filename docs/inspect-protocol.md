# Inspect execution v1

This is increment 2 of Phase 1 milestone 6. Inspect now executes the existing
session engine and records model-call evidence. Verification uses Inspect's real
task, solver, model, and logging APIs with an offline scripted model. No live
provider has been qualified and no research data has been collected. A bounded
live compatibility check remains increment 3; recovery and branching remain Phase 2.

## Execution and player inputs

`run_experiment(config, output_dir)` creates an exclusive run directory, builds
`poker_task`, and calls `inspect_ai.eval_async`. One sample and one epoch represent
one complete session attempt. Each seed defines a matched block: all its channels
use the same saved deals and seat rotation, with fresh player histories. Initial
seats rotate across blocks; seats also rotate between hands as specified by the
[game protocol](game-protocol.md). Failed samples remain in the run; there are no
automatic retries or resumes.

The custom solver calls the ordinary session runner. Its decision adapter renders
the [model protocol](model-protocol.md), then calls Inspect's model with exactly
two messages: the system prompt and the permitted player view as user JSON.
No tools, shared sample conversation, earlier raw outputs, or audit labels are
added to player input. All persistent memory belongs to the session engine.
Concurrent communication requests keep the session's simultaneous delivery barrier.

The session and poker modules have no Inspect dependency. A task-local request ID
connects the decision callback to the audit without adding identifiers to player
views or changing the decision-callable interface.

## Configuration and limits

`ExperimentConfig` is strict versioned JSON containing a `ModelConfig`, a
`SessionConfig` template, distinct seeds and channels, and these execution limits:

| Field | Default | Scope |
| --- | --- | --- |
| `max_samples` | 1 | Concurrent sessions in the Inspect task |
| `max_connections` | 3 | Concurrent calls to the single model across sessions |
| `token_limit` | 100,000 | Inspect's metered tokens per session |
| `cost_limit` | `null` | Optional Inspect-metered dollars per session |
| `session_time_limit` | 600 seconds | Entire session solver execution |

All specified limits must be finite and positive. The session template uses
`channel: none`; the runner replaces it with each selected condition. The
coordination-control instruction requires communication-enabled channels.
The number of planned sessions is `len(seeds) * len(channels)`.

Each request also uses the model's output-token cap and the session's decision
timeout. Queuing for a connection counts toward that timeout. Transport retries,
sample retries, response caching, fallback models, and batch execution are disabled.
Provider-side prompt caching is distinct from reusing a sampled answer. We make
no claim that live sampling is reproducible from a seed: seeds determine deals.

Token and dollar limits are checked by Inspect after responses arrive. Concurrent
in-flight calls may exceed them, and usage absent from a provider response cannot
be metered reliably. A configured dollar limit is rejected if Inspect has no
pricing for that model. These are per-session stopping limits, not a prepaid cap
on the whole run. Live validation must check supported settings, returned model
identity, usage, pricing, and transport behavior before fixing an evaluation budget.

## Durable artifacts and links

```text
run-directory/
  run.jsonl
  inspect/*.eval
  sessions/<session_id>/
    session.jsonl
    model.jsonl
```

`run.jsonl` saves configuration/hash, run ID, Python/platform/package versions,
and a digest of installed package source and prompt files. Its final record lists
Inspect log locations and evaluation IDs. An absent final record leaves an
incomplete run manifest; inspect individual attempts before classifying them.

`session.jsonl` retains the unchanged version 1 [game journal](recording-protocol.md).
It is authoritative for player observations, decisions, messages, actions, and
rewards. `model.jsonl` records the additional model boundary:

| Event | Evidence |
| --- | --- |
| `model_audit_started` | Model config/hash, session config/schedule hashes, provenance, run/block/sample/epoch references |
| `call_started` | Session request ID, Inspect span ID, timestamp, exact prompt/hash, requested model/settings, messages |
| `call_finished` | Returned/error/cancelled status, elapsed time, model output or exception, Inspect model events |
| `model_audit_ended` | Session status, completed hands, rewards, and failure |

Each envelope has `kind: model_event`, integer `version: 1`, `session_id`,
contiguous `sequence`, `event`, and `data`. The span ID is
`<session_id>-request-<request_id>`. Inspect model events retain their UUIDs,
effective settings, returned model identifiers, usage, retry information, and
available raw API request/response payloads. Attachment references are resolved
before writing the model journal. A provider that supplies no raw payload cannot
have one reconstructed; its absence remains visible. Credentials are supplied
through the provider's environment variables, never experiment configuration.

Both journals use exclusive files, mode 0600, newline framing, flush, and fsync.
`call_started` is durable before invoking Inspect; `call_finished` is durable
before parsing or applying game effects. An audit write failure aborts execution
and leaves the attempt incomplete. Process death during a request cannot establish
whether a provider completed or billed the call; the journal is not a recovery
checkpoint. Keep complete audit artifacts out of player inputs and retain the
source checkout and lockfile with any research release.

Inspect sample metadata links both journals and exposes `session_status` and
`session_result`; the sample output is a synthetic game summary. It is never used
as a player response. Inspect's overall `success` status alone is insufficient:
a task can finish with failed samples. The CLI exits nonzero unless every session
is complete and every Inspect evaluation succeeded.

## Failures and verification

Malformed or illegal decisions, provider errors, and decision timeouts follow the
existing session policy. Refused, truncated, tool-call, fallback, or missing-choice
responses are invalid even if their completion happens to contain valid JSON.
The session deadline records an interrupted trajectory and an explicit Inspect
sample error. Token/cost limit exceptions are recorded as agent failures; an
output already received by Inspect remains in its model event even if the limit
prevents `generate` from returning it. No repair or substitute action is sampled.

`read_model_log(path)` validates the envelope, configuration and prompt hashes,
request lifecycle, and terminal status. Missing footers and torn final lines are
incomplete; malformed committed lines are errors. It does not validate arbitrary
provider payload schemas.

`verify_model_links(model_path, session_path)` checks session IDs, config/schedule
hashes, request links, permitted observations, spans, and terminal summaries. Call
`await replay_session(session_path)` separately to validate every game effect.
Replay uses recorded decisions, with no model calls or dependence on Inspect log
formats. Only complete, linked, replay-verified sessions qualify for complete-session
results; preserve failed, interrupted, and incomplete attempts separately.

## Offline commands and control templates

Run the full offline pipeline in a new directory:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-offline.json --offline --output runs/preparation/inspect-001
```

The command prints session statuses and Inspect log paths. Open a returned `.eval`
path with `uv run --locked inspect view PATH`. For a selected session directory:

```python
import asyncio
from pathlib import Path

from poker_collusion.model_log import verify_model_links
from poker_collusion.replay import replay_session

directory = Path("runs/preparation/inspect-001/sessions/SESSION_ID")
audit = verify_model_links(directory / "model.jsonl", directory / "session.jsonl")
state = asyncio.run(replay_session(directory / "session.jsonl"))
print(audit.status, state.completed_hands, state.rewards)
```

All three shipped configurations use `mockllm/model` and three hands:

- `inspect-offline.json`: neutral none/public/private matched sessions.
- `inspect-competence.json`: separate neutral no-communication sessions for the
  future competence check; no automatic competence score is implemented.
- `inspect-coordination-control.json`: separate instructed public/private control.

Use the latter files with the same command and distinct output directories.
The offline policy passes on messages and checks/calls. Its token counts are
explicitly synthetic, supplied to avoid a tokenizer download and exercise usage
metering. It does not demonstrate competence or enacted coordination, even when
run under the control instructions. The model and budget for live runs remain
to be selected and verified; these templates are preparation defaults.

Ordinary tests require no credentials or external network. Inspect needs local
event-loop sockets and writable XDG data/cache directories. Restricted sandboxes
must allow those local operations; integration tests reject external IP connections.
