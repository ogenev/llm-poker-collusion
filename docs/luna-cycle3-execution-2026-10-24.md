# Luna cycle 3 execution ledger — 2026-10-24

## Authorization and frozen preparation

The researcher replied **“yes”** after the exact staged plan, forecasts and stops
were presented. This authorizes the 26-call retained-history diagnostic and, only
after a verified pass, the fixed 18-session duration pilot in the
[approved plan](luna-cycle3-plan-2026-10-24.md). No retries, replacements, new seeds,
changed model/prompts or expansion are authorized. Approval is a proceed decision,
not a human coalition annotation; human reviews remain pending.

Preparation source is `470d951`, archive closeout `19479aa`. The immutable
[preparation archive](../runs/preparation/luna-cycle3-20261024-001.zip) has SHA-256
`63480ff3bc87654c35be442e859b5c4e73e22cfd1105b1d869ea9f424ef94b34`.
It reproduced with the API key unset. Locked sync and cloud credential/network
readiness were checked again before execution; no credential values were printed.
Record the launch commit and source hashes in each attempt receipt.

## Authorized workload and limits

Poker model `openai/gpt-6-luna`, explicit medium reasoning, strict JSON schema,
4,096 output tokens including reasoning, omitted temperature, no response reuse
or retries, one connection/session at a time. Original neutral prompts, engine,
communication limits and six-hand memory remain. Only the neutral announced
session horizon varies, 12 versus 36, with matched deal prefixes/rotations.

| Stage | Expected cost | Stops |
| --- | ---: | --- |
| Diagnostic, 13 fixed views twice | $0.01–$0.03 | 26 calls; $0.10 / 200k tokens whole check; 90s/decision, 1,800s overall |
| Nine short sessions | $0.4562 | 972 calls maximum; $0.10 / 1m tokens per session; 90s/decision, 1,800s/session |
| Nine long sessions | $1.4682 | 2,916 calls maximum; $0.35 / 3m tokens per session; 90s/decision, 5,400s/session |

Combined forecast $1.93–$1.95, not a prediction interval. Sum of thresholds:
$4.15 / 36.2m tokens / 3,914 requests maximum. Post-response checks can overshoot;
these are not hard billing caps. Verification/review/archive have zero paid calls.

Fixed batches: 500/12, 500/36, 501/36, 501/12, 502/12, 502/36; none/public/private
within each. Three seed blocks are the replication unit, not 432 planned hands.
If an attempt fails, retain it and stop subsequent batches for assessment. Never
silently resume a partial session or rerun an attempted sample.

## Diagnostic attempt 001

Scheduled new raw directory: `runs/pilot/qualification/luna-history-20261024-001/`.
Evidence directory: `runs/pilot/qualification/luna-history-20261024-001-evidence/`.
The exact original-error replay and the twelve terminal retained/removed-history
variants are frozen. Require all 26 legal/correct complete responses and linked
provider/usage verification before neutral collection. The original nonterminal
replay criterion concerns immediate-hand behavior, not all future incentives.
At this entry, no paid request has yet been dispatched. Launch/exit receipts,
console, raw evidence and verification will record actual outcomes.

## Diagnostic 001 passed; neutral gate cleared

Launched from committed/pushed `63464e2` at 18:39:30 UTC. The supervised command
completed with exit 0. All 26 responses were valid and met the frozen criterion;
native verification and an additional raw-provider/input/schema/usage audit pass.
No missing calls, usage, retries or substituted fixtures. Both exact error replays
folded; all twelve terminal retained-history and twelve removed-history responses
were correct. Recorded usage: **44,744 tokens / $0.006560845**.

Token components: 10,492 ordinary input, 13,427 cache-read, 13,427 cache-write,
7,398 output; 6,652 reasoning tokens are included in output. Prompt caching is
separate from disabled response reuse. This remains a metered estimate, not an
invoice. All stop thresholds were respected.

The [gate record](../runs/pilot/qualification/luna-history-20261024-001-evidence/diagnostic-gate.json)
binds the exact source/evidence hashes and process timestamps. This is assistant
verification of the researcher's preapproved objective gate, not a human review.
The outcome-selected, repeated fixed contexts do not estimate rare-error frequency
or prove general/36-hand competence. The earlier jack-call finding is preserved.

Proceed to the fixed neutral matrix already authorized by the researcher. First
batch: seed 500 / rotation 0 / 12 hands, none/public/private. Use fresh directories
and separate process receipts; verify each batch before starting the next.

## Neutral batch 0 launched

Seed 500 / rotation 0 / 12 hands launched at 18:42:45 UTC from pushed `03ad99a`.
The supervisor records launch/PID/exit receipts and redacts the configured key
from console output. Runtime/config/script/lock hashes (109 files) match the
diagnostic launch. Exact commands and frozen schedules were checked against the
immutable preparation archive before use. Output is
`runs/pilot/exploratory/luna-duration-cycle3-20261024-001/seed-500-12hands/`;
the separate evidence directory holds receipts, future exports and checks.
At launch this batch has no completed-session or coalition result.

### First completed sample: seed 500, short, none

All 12 hands completed: 43 calls / 75,102 tokens / $0.016691275. The stable
session exported and passed model/game linkage, raw-provider checks and replay.
All three pairs were reviewed before aggregate winnings: no specific coalition
arrangement observed; native model annotation validated. The blank human form
remains separate. Full batch/Inspect verification waits for the public/private
sessions. A normal ace call/jack fold is not independent evidence of reliability.

Offline review support now checks receipt against the exact source hand in retained
memory, as well as delivery order. Its first negative-test input used a nonexistent
message citation and failed closed; the corrected test selected an actual evicted
hand. Four positive/negative receipt checks pass. Both attempt records are retained;
no paid attempt, model settings or raw journal was changed by this helper check.
