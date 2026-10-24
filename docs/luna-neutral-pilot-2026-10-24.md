# Luna neutral exploratory pilot — 24 October 2026

Part of the [research log](research-log.md) and [approved replication plan](luna-replication-plan-2026-10-24.md).
This stage tests spontaneous coordination under the original individual-winnings
objective, separately from the [instructed controls](luna-coordination-iteration-report-2026-10-24.md).

## Researcher decision and review limitations

After the control report and assistant recommendation, the researcher instructed:

> process with the neutral pilot now

This is the researcher's decision to proceed past the coordination gate. The
scope of manual review was not specified. It is not a completed human annotation
of the six sessions or evidence of an independent second review. Preserve that
limitation, the assistant/control findings, and the earlier pending-gate records.
Sol's prior human assessment is not used to qualify Luna. No new permission is
needed for the already-approved fixed neutral workload and limits.

All six Luna controls completed and passed full evidence and provider checks.
Current control source hashes were rechecked before launch; all six game/model
journals match the verified packet. Basics passed 12/12 and the three gameplay
sessions were verified and assessed by the assistant under the user's earlier
gate amendment. Formal human judgments and independent review remain outstanding.

## Exact fixed execution

- Poker model `openai/gpt-6-luna`, explicit medium reasoning, strict JSON schema,
  4,096 output-token cap, omitted temperature, no response reuse/fallback/retries.
- One run, three matched sets, seeds 300/301/302 in order. Each set contains
  none, public, private sessions in that order: **nine sessions, 108 hands**.
- Twelve hands/session; original deals and rotations; two communication rounds,
  500 characters/message, 1,000/player/hand, six retained hands, fresh histories.
- One session and one provider connection at a time. Decision deadline 90 seconds;
  session deadline 1,800 seconds. No control/reviewer material enters player input.
- Original neutral prompts and mechanics remain unchanged. The cancelled
  channel-explicit revision is not reintroduced. No ten-set expansion.
- Same predeclared fixed-attempt failure policy: keep all scheduled attempts and
  partial/failed evidence; no selective repair, retries, replacements or expansion.
  Stop after the run and investigate any incompleteness, verification/settings
  failure or missing usage before another paid command.

Config: `configs/inspect-pilot-neutral-gpt-6-luna-medium-strict.json`; canonical
hash `f915cf26d1f27c74711c0efd5bfe0101eb110217d700db5ec140cfb1af409b03`.
Direct comparison with the original strict Sol neutral config confirms only
model identity and the previously approved dollar-threshold scaling differ.

```sh
uv run --locked python scripts/run_experiment.py \
  configs/inspect-pilot-neutral-gpt-6-luna-medium-strict.json \
  --model-cost-config configs/openai-gpt-6-luna-pricing.json \
  --output runs/pilot/exploratory/luna-neutral-20261024-001
uv run --locked python scripts/verify_run.py \
  runs/pilot/exploratory/luna-neutral-20261024-001
```

## Costs and stops, unchanged from approval

Original expected cost: **$0.203986825–$0.211002365**, conditional on the reported
Sol neutral usage. That range only reflects uncertainty about the Sol cache-read
category; it is not a forecast interval for Luna. Luna qualification/control use
already differed from the Sol projections, so actual neutral usage can differ too.

Each session stops at **$0.10 or 1,000,000 tokens**: sums are **$0.90 and 9m
tokens** across the fixed nine sessions. Limits are checked after responses and
can overshoot, including queued communication calls; they are not hard billing
caps. No increase or additional paid attempt is authorized. Saved Standard prices
remain $0.10 input, $0.50 output including reasoning, $0.01 cache read, and $0.125
cache write per million tokens. Official prices/compatibility were checked today;
actual earlier Luna calls independently verified medium and strict-schema support.
Earlier Luna spending is $0.488056275 and remains separate from this run's usage.

## Preparation and attempt ledger

Started from latest committed main `7bdd8c36a459bcf8ae99ca0c933f26e060deac33`.
During read-only preparation the exec server briefly disconnected; three commands
could not start. No neutral paid call or run directory existed. The runtime then
reconnected; source and prior evidence remained available. This was an environment
preparation failure, not a model response failure or a paid retry.

`uv sync --locked` passed. Current cloud observations report enforced policy and
ready credential binding; no credential values were read or printed. Zero-call
preflight passed: nine sessions, at most 972 decisions, one session/connection,
and the exact limits above. Runtime/config/lock bytes are unchanged; prior
transport tests and full offline validation remain applicable.

Fresh evidence directory:
`runs/pilot/exploratory/luna-neutral-20261024-001-evidence/`. It holds the exact
authorization, interruption record, readiness/hash checks, zero-call preflight,
source/config snapshot, attempt commands/times, redacted console, and subsequent
verification/usage/review artifacts. No neutral response existed at this entry.

## Review, analysis and archive

Verify every completed session and inspect raw provider settings, prompts and
usage. Export exact transcripts/views, source-linked blank forms and separate
assistant notes. Review all three pairs in each full session before aggregate
winnings; retain ambiguity, unsupported claims and failed/incomplete trajectories.
Do not turn missing human judgments into negative coalition labels.

The experimental sample is **three matched sets**, not 108 independent hands or
27 independent pair/session units. Keep instructed-control evidence separate.
Compare with the committed Sol report only as a reported baseline; its ignored
raw runs remain unavailable here. The final iteration report will address
coalition evidence, public/private differences, limitations and next steps.
Package all new evidence, transcripts, usage records and report with checksum
manifests, exclude credentials, and verify the extracted archive. Preserve earlier
qualification/control archives. No further data collection follows automatically.
