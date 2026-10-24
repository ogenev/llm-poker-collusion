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
