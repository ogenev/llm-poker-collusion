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
| `runs/pilot/exploratory/luna-neutral-cycle2-20261024-001` | Interrupted; one complete, one partial session | Known: 110 responses / 213,404 tokens / $0.049954175; 2 unresolved requests |

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

## Neutral attempt started

The fixed nine-session attempt began at 15:02:02 UTC from clean published source
`9d18fe2`. The launch guard checked the diagnostic pass and that the neutral
configuration differs from cycle 1 only in seeds. Fresh output; unchanged
limits; serial session/provider execution. The runner preserves all samples,
including failures, without replacement. See `attempt-start.json` in the
[neutral evidence directory](../runs/pilot/exploratory/luna-neutral-cycle2-20261024-001-evidence/).

## Interruption and continuation of unstarted sessions

On returning after the researcher reported a usage-limit reset, the original
process ID no longer existed and its Python/uv processes were defunct. The last
saved public response began at 15:16:53 UTC and returned about 5.36 seconds later.
There is no process exit receipt or run footer. The pause and interruption
coincide; the exact termination cause is not independently recorded.

Seed 400 none completed 12 hands / 40 calls / 72,085 tokens / $0.01637955 and
passed the native saved-sample verifier, replay, provider audit and assistant
annotation validation. The original whole-run verifier correctly fails with
“Incomplete run manifest.” It is not a completed nine-session run.

Seed 400 public contains seven settled hands and part of hand eight, 72 started
requests and 70 saved responses: 141,319 known tokens, $0.033574625 recorded cost.
Requests 70 and 71 have no saved response. Dispatch/billing is unknown, not zero;
the recorded original-neutral total $0.049954175 is a lower bound. Preserve the
entire original directory unchanged. Do not retry those requests, fabricate a
terminal record or replace the partial public session.

The researcher said “usage limit is reset, continue where you left off.” The
approved plan already permits retaining a failed session while completing the
other fixed samples. Continue **only seven never-started sessions**, in their
original order, without increasing any approved limit:

| Selection | Fresh output suffix | Calls maximum | Cost/token stops |
| --- | --- | ---: | --- |
| Seed 400, rotation 0, private only | `luna-neutral-cycle2-20261024-002-private400` | 132 | $0.10 / 1m |
| Seed 401, rotation 1, none/public/private | `luna-neutral-cycle2-20261024-003-seed401` | 324 | $0.10 / 1m per session |
| Seed 402, rotation 2, none/public/private | `luna-neutral-cycle2-20261024-004-seed402` | 324 | $0.10 / 1m per session |

All outputs are under `runs/pilot/exploratory/`. Use the existing `--block-index`
selection, retaining the original three-element seed list so rotations are not
renumbered. The separate private-only config changes only the selected channel
list; runtime, model, prompts, deals, memory and all limits stay identical.
No experiment code change or new diagnostic/controls are required.

The remaining seven-session forecast is **$0.377162**, using the corresponding
first-cycle sessions, with unchanged summed stops **$0.70 / 7m tokens** and
at most **780 calls**. Keep the original public session's full $0.10 allocation
reserved for its recorded and unknown usage. The original total allocations
remain $0.95 / 9.1m tokens; post-response overshoot caveats still apply. This is
continuation of the authorized fixed stage, not authorization for repetitions.

If the remaining sessions complete, there will be eight complete sessions plus
one partial, and only **two fully completed matched sets out of three planned**.
Report that loss explicitly. Seed 400's incomplete public evidence cannot become
a negative coalition label or a complete matched comparison. New collection to
replace it would require a separately approved amendment; none is launched here.
