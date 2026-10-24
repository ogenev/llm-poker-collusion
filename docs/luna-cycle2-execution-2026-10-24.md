# Luna cycle 2 execution ledger — 2026-10-24

## Authorization and fixed scope

The researcher replied “yes” to the concrete staged plan and budget, after
requesting commit/push first. Source/configs were published as `6e6e1ab`, with
preparation archive closeout at `7c568cc`. This entry records approval before
paid execution. The [plan](luna-cycle2-plan-2026-10-24.md) and
[coding guide](luna-cycle2-coding-guide-2026-10-24.md) are fixed for this cycle.

Diagnostic: 60 decisions maximum, $0.05 / 100,000 tokens whole-check stops,
90s/decision and 1,200s overall. Neutral, conditional on a verified 60/60 pass:
seeds 400/401/402 with none/public/private each, rotations 0/1/2, 12 hands/session,
nine sessions. Stops $0.10 / 1m tokens per session, 90s/decision and 1,800s/session.
Combined forecast $0.47–$0.49; summed stops $0.95 / 9.1m tokens, checked after
responses with possible overshoot. Maximum 1,032 calls; no replacement attempts.
Luna/medium, strict JSON, original neutral settings; no main-study expansion.

Rechecked locked sync, clean source, configured credential readiness and enforced
API host access. Both paid output destinations were absent. Pricing was checked
during same-day preparation; no settings or rate changes were introduced.

## Attempts

| Stage / fresh directory | Status | Calls / tokens / metered cost |
| --- | --- | --- |
| `runs/pilot/qualification/luna-context-20261024-001` | Passed 60/60; started 14:57:36 UTC, source `f70267c` | 60 / 63,265 / $0.0117173 |
| `runs/pilot/exploratory/luna-neutral-cycle2-20261024-001` | Diagnostic gate passed; launch pending | Pending |

All attempts, partial records and failures will be preserved. No human labels
or independent calibration results are inferred from approval. Review remains
assistant-descriptive unless genuine human annotations are supplied. The new
experimental sample is three matched sets; keep this cycle separate from the
first pilot and from the reported Sol baseline.

First repetition completed 30/30 correctly. At the interim check, 33/33 finished
responses were correct, with complete usage and no interruption. This is not the
final gate result; neutral remains blocked pending all 60 and offline verification.

## Diagnostic gate passed

All 60 fixed decisions passed, 12/12 in each context, with no failed, invalid,
interrupted, retried or missing-usage response. Run ID:
`a726c647cea544d7ac1c3d1effda6228`. Native diagnostic verification and the saved
Luna provider audit both passed, including raw request/prompt/schema/medium
settings, response identity, standard service tier, cost and Inspect linkage.
Usage: 49,788 input + 13,477 output = 63,265 tokens; 11,791 reasoning tokens are
already inside output. No cached input. Metered cost $0.0117173.

[Evidence and full decision transcript](../runs/pilot/qualification/luna-context-20261024-001-evidence/review.md)
retain every prompt, response and usage record. This short no-history screen
does not reproduce the first pilot's long-context jack error or estimate its
rare-error probability. It adds no coalition observation and changes no prior
labels. The conditional neutral stage is now authorized without another prompt.
