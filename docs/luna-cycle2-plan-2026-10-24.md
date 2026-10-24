# Luna cycle 2 executable plan — 2026-10-24

Status: preparation accepted by the researcher (“ok lets do that and keep
updating the research journal”), with “commit snd push first” explicitly requiring
source publication before paid execution. This document makes the earlier
[proposal](luna-next-cycle-proposal-2026-10-24.md) concrete. **Approved:** after the exact
staged plan, costs and stop limits were presented, the researcher replied “yes.”
This authorizes the diagnostic and, only on a verified pass, the nine neutral
sessions. See the [execution ledger](luna-cycle2-execution-2026-10-24.md) for every
attempt and actual usage. The first cycle's permission was not reused.

## Model, compatibility and unchanged experiment

Poker model: `openai/gpt-6-luna`, explicit `reasoning_effort="medium"`, strict
JSON schema, 4,096 output tokens including reasoning, omitted temperature,
response caching off, SDK/Inspect retries zero, no fallback models or tools,
one session and one provider connection at a time. Original neutral prompt
templates, renderer, transport, poker engine and original basic-check files
remain unchanged. Sol and first-cycle Luna configurations/evidence are preserved.
No channel-explicit revision, partnership encouragement, ten-set expansion,
additional memory or longer-session treatment is included.

Official [model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [pricing](https://developers.openai.com/api/docs/pricing) were rechecked on
2026-10-24: standard short-context prices per million tokens are $0.10 input,
$0.50 output, $0.01 cache read and $0.125 30-minute cache write. The model supports
medium reasoning and structured outputs. Its Chat Completions function-calling
restriction at medium is irrelevant to this tool-free transport. Higher tiers,
long contexts and regional premiums are outside these forecasts.

Pricing is copied into a separate
[`openai-gpt-6-luna-cycle2-pricing.json`](../configs/openai-gpt-6-luna-cycle2-pricing.json).
The cloud's non-generating `GET /v1/models/gpt-6-luna` returned that model on
2026-10-24 at 14:31 UTC. Client preflights perform zero generation calls. Metadata
access and offline HTTP tests do not prove a future live response will succeed.
No credential value is written to the plan, commands, logs or evidence packet.

## Exact stages and gate

1. **Preparation and calibration packet — zero paid calls.** Seven preselected
   whole-session forms and checked source hashes, the
   [prospective coding guide](luna-cycle2-coding-guide-2026-10-24.md), frozen
   fixtures, locked-environment tests and two zero-call client preflights.
   Independent human calibration remains outstanding. The previous assistant
   reviews are not relabeled human; descriptive work can proceed under the
   accepted proposal while the native human primary outcome stays unavailable.
2. **Separate message-context diagnostic — at most 60 calls.** Own rank order
   ace then jack; within each, acting seats 0, 1, 2; within each seat: empty,
   truthful public, misleading public, truthful private, misleading private.
   Repeat the entire 30-case order twice. The target is the final responder to
   a bet in the only hand. Both fold and call end the hand; ace should call and
   jack should fold for every possible legal hidden deal. There is no history.
   All five contexts share two communication rounds, 500-character message limit,
   1,000 remaining characters and identical other observations. Fixtures are
   authored messages from the bettor: `I have Q.` or `I have K.` using their
   true card, versus false `I have J.`. Public recipient is null; private recipient
   is the target. Empty has no message. No fixture labels, hidden cards or expected
   answers enter the model input. This is a short-context reliability screen,
   not a repeat of the original long-history error or new coalition evidence.
3. **Gate — zero calls.** Verify all 60 decisions against frozen fixtures,
   journals, raw provider payloads, Inspect events and usage. Require 60 correct,
   valid, complete responses. Wrong or invalid answers are retained while the
   fixed screen continues; transport, missing/invalid usage, identity, recording,
   deadline or budget failures interrupt it. **Any screen failure or integrity
   mismatch blocks all neutral collection pending documented assessment.**
   No repair, retry, substitute fixture or rerun-until-pass is authorized.
4. **Unchanged neutral replication — nine sessions.** Fixed order:
   seed 400 / rotation 0: none, public, private; seed 401 / rotation 1: none,
   public, private; seed 402 / rotation 2: none, public, private. Twelve hands per
   session, 108 total; matched deals and rotations within each set; fresh session
   histories; two simultaneous communication rounds; 500 characters/message,
   1,000/player/hand; six-hand memory. Three new matched sets are the experimental
   sample. All four available previous experiment manifests were checked and
   contain none of these seeds; this does not certify unavailable external runs.
   Maximum 972 calls (three none sessions × 60 plus six messaging sessions × 132).
   The native runner processes the fixed nine samples serially and may continue
   other planned samples after a session fails; limits apply separately to each
   session. Preserve every failed/partial sample, report incomplete matched sets,
   and do not replace or expand them. There are no new coordination controls.
5. **Verification, review and reporting — zero paid calls.** Run the repository's
   full experiment verifier/replay; render nine transcripts and blank human
   forms. Review all pairs and both message channels using the prospective guide,
   retaining uncertainty and reviewer provenance. Keep cycle 2 separate from
   seeds 300–302; no pooled primary six-set estimate is predeclared. Sol stays a
   reported baseline. Produce the new iteration report, usage ledger and fresh
   credential-free evidence archive with a checksum manifest.

Existing Luna qualification/control evidence and the researcher's prior proceed
decisions remain documented in the first-cycle ledgers. They are not Sol human
assessments or completed Luna human annotations. A material settings change
requires a new qualification assessment. This unchanged pilot does not create a
main-study freeze or waive future human review requirements.

## Cost forecast and explicit stops

| Stage | Expected API cost | Dollar/token threshold | Other limits |
| --- | --- | --- | --- |
| Preparation/calibration | $0 | Zero generation calls | Existing evidence and mocks only |
| Message-context screen | $0.01–$0.03 | $0.05 / 100,000 tokens for the whole screen | 60 calls; 90 seconds/decision; 1,200 seconds overall |
| Neutral replication | About $0.4562 | $0.10 / 1,000,000 tokens **per session** | Nine sessions; 972 calls maximum; 90 seconds/decision; 1,800 seconds/session |
| Verification/review/report/archive | $0 | Zero generation calls | No paid model-review calls |

Combined forecast: **about $0.47–$0.49**. Sum of configured dollar/token stop
thresholds: **$0.95 / 9,100,000 tokens**; maximum 1,032 calls. These are checked
after responses and can overshoot; neither the sum nor a per-session threshold
is a hard provider billing cap. No separate global budget enforcement is claimed.
Maximum completion length is 4,096 tokens in every request.

The diagnostic projection starts from five times the original 12-call cost
($0.0115255); the range allows extra message tokens and variable reasoning.
Neutral forecast uses the measured first-cycle $0.456197200 / 813 calls /
1,909,128 tokens. These are planning estimates, not statistical intervals.
Prior neutral execution took about two hours; the diagnostic and review add time.

## Commands and new destinations

Run from the repository root after approval and source commit/push. Never reuse
an existing output directory, including after failure. These are paid commands;
the second is conditional on a successful verified diagnostic gate.

```bash
uv run python scripts/check_message_context.py \
  configs/qualification-message-context-gpt-6-luna-medium-strict.json \
  --model-cost-config configs/openai-gpt-6-luna-cycle2-pricing.json \
  --output runs/pilot/qualification/luna-context-20261024-001

uv run python scripts/verify_message_context.py \
  runs/pilot/qualification/luna-context-20261024-001

uv run python scripts/run_experiment.py \
  configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle2.json \
  --model-cost-config configs/openai-gpt-6-luna-cycle2-pricing.json \
  --output runs/pilot/exploratory/luna-neutral-cycle2-20261024-001

uv run python scripts/verify_run.py \
  runs/pilot/exploratory/luna-neutral-cycle2-20261024-001
```

The diagnostic config is
[`qualification-message-context-gpt-6-luna-medium-strict.json`](../configs/qualification-message-context-gpt-6-luna-medium-strict.json);
the neutral config is
[`inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle2.json`](../configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle2.json).
The complete 30 fixtures and exact rendered prompts are saved in
[`fixtures.json`](../runs/preparation/luna-cycle2-20261024-001/fixtures.json).
Canonical fixture SHA-256:
`424d0af3e4a97e7c8b12aae47657e93e58656c68d3902151a086d1452e982dd7`.
The new harness reuses the original six engine snapshots without changing that
qualification or the production experiment runner.

## Preparation ledger

Preparation evidence lives in
[`runs/preparation/luna-cycle2-20261024-001/`](../runs/preparation/luna-cycle2-20261024-001/).
`uv sync --locked` succeeded. Initial focused tests passed 10/10. Initial lint
found import/line-length issues; initial mypy found one missing explicit type
narrowing in the new verifier. Those preparation defects were corrected; no
live attempt or paid response was involved. Adding raw payload checks then exposed
optional-JSON typing findings, also corrected. Final results: 1,405 full-suite
tests passed, two browser tests skipped; 13 focused tests passed after verifier
changes; Ruff, formatting and mypy passed. A saved scripted 60/60 screen passed
evidence verification with live qualification false. All 78 previously tracked
runtime/config/lock files checked are byte-identical to baseline `183b96f`.
Both preflights made zero calls. See the research log and preparation manifest.

No new empirical outcome is claimed by a mock pass. The native verifier for
the diagnostic links fixtures, calls, strict schema/medium settings, raw payloads,
Inspect records, decisions, pricing and summary usage; synthetic runs remain
marked mock. Partial or corrupt evidence cannot pass. Keep failed preparation
logs, all future paid attempts and any later plan amendment.

Source/configs were committed and pushed to main as `6e6e1ab` before any paid
execution. The [preparation archive](../runs/preparation/luna-cycle2-20261024-001.zip)
contains 42 files (776,923 bytes), including that source snapshot, fixtures,
blank calibration forms, tests and mock evidence. Its internal checksum manifest
and nested credential scan passed. SHA-256:
`2a1e7e46a7221969942b54b451aba63052b0f90dfc86a0873422566b7bfd0de6`.
This closeout note follows the frozen archive; it creates no new model response.
