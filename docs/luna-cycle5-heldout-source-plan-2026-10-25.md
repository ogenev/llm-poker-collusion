# Luna cycle5: prospectively selected private-message contexts

Status: prepared; no cycle5 paid generation approved or performed. Human
adjudication remains deferred. This is exploratory mechanism work, not main
coalition collection or a human qualification decision.

Cycle4 found context-dependent wording and recipient effects in four previously
positive contexts from one session. The next step is to collect fresh contexts
before observing their replies. This reduces selection on successful disclosure;
it does not establish coalition formation, payoff benefit or a channel effect.

## Frozen source collection

Run three private sessions, seeds600–602 in that order, 36 hands each. Preserve
the cycle3 neutral prompt, game, seed-generated deals and original block-index
seat rotations0/1/2. Use `openai/gpt-6-luna`, explicit `medium`, strict JSON schema,
4,096 maximum completion tokens including reasoning, no temperature override,
no response caching and no retries. There are two communication rounds,
500 characters per message, 1,000 characters per player/hand, six-hand memory,
90 seconds per decision, one connection and one active session. No channel-explicit
prompt revision is introduced. Existing Sol/Luna configurations remain unchanged.

These are three new, unmatched private source sessions, not matched public/private
sets, replacements for interrupted older cells, or an expansion to ten sets.

Configuration: `configs/inspect-source-private-gpt-6-luna-medium-strict-cycle5.json`.
Its session template channel is `none`; its experiment channel list is exclusively
`private`, as required by the native experiment format. Relative to cycle3's
36-hand config, only seeds and the channel list differ.

## Selection before replies

The exact rule is `configs/selection-heldout-cycle5.json`, SHA-256
`14c7bb8073d874e4a3b31143f196ced244fd05eda83e5602ea84897871d7fe0d`.

1. Consider the frozen views before the second communication round, from hand7
   onward. The recipient has six prior hands available in memory.
2. Require a first-round incoming private message asking for the recipient's
   current card. Match only the three frozen, case-insensitive regular expressions
   in the policy. They cover forms such as “What card do you have?”, “Tell me your
   card”, and “What's your card?”. Honesty wording is not required. Normalize a
   curly apostrophe only for matching; retain the original message bytes.
3. Select the first two eligible hands per session, at most one context per hand.
   After all three views have been emitted, rotate A/B/C candidate priority by
   `(2 * seed + 2 * zero-based hand_index) % 3`. Within a view, choose the first
   eligible incoming message in saved observation order. No current reply, true
   card, payoff or favorable outcome enters this rule.
4. Synchronously persist and fsync each selected view, focal message, request ID,
   timestamp and source-prefix hash before any current-round decision callback.
   Verification recomputes the rule and checks the prefix and timing against all
   three current-round calls. The observer does not alter player inputs/actions.
5. Keep zero or fewer-than-two selections as observed yield. Do not widen the
   matcher/window, backfill a quota, replace a session, or select after replies.

The matcher is a narrow operational definition. It can miss paraphrases or match
quoted questions. Eligibility is not proof of cooperative intent. Candidate
availability can still produce uneven recipients, seats and card histories.
Neither prior lies nor prior truthful disclosures are balanced by design; report
these descriptively without filtering on subsequent responses.

The initial offline draft used `(seed + hand_index) % 3`, which always prioritized
seat0 when all players qualified. Before any paid collection, revised the rule
above and added a regression test. Both draft source snapshots and rehearsals are
preserved. The revised six-context scripted fixture prioritizes each identity and
seat twice; this does not guarantee balance in naturally occurring questions.

## Exact stages, estimates and stop limits

| Stage | Work | Expected API cost | Cost stop | Token stop | Maximum calls |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | Locked installation, tests, client preflight, availability GET | $0 | $0 | 0 generated | 0 generation |
| 1 | Seed600: private, 36 hands, initial rotation0 | $0.215770925 | $0.35 | 3,000,000 | 396 |
| 2 | Seed601: private, 36 hands, initial rotation1 | $0.215770925 | $0.35 | 3,000,000 | 396 |
| 3 | Seed602: private, 36 hands, initial rotation2 | $0.215770925 | $0.35 | 3,000,000 | 396 |
| 4 | Verify evidence, seal selected inputs, export transcripts/forms | $0 | $0 | 0 generated | 0 |
| Total requested | 108 hands in three source sessions | **$0.647312775** | **$1.05 summed** | **9,000,000 summed** | **1,188** |

Each source has a 5,400-second session deadline. The call bound is36×(six
communication decisions + five maximum betting decisions). Stop before starting
another source if an earlier source fails execution/evidence checks or frozen
files change. A lack of eligible messages is not an execution failure and does not
stop the fixed source schedule. No behavioral success criterion gates collection.

Cost/token stops are checked after responses, not hard billing caps. The original
communication phase schedules three decisions together; queued calls from that
phase may finish after one fails. The failure test retains all three such calls.
Preserve partial logs, unknown usage and failures; do not silently retry, restart,
replace or increase thresholds. Any continuation after failure needs an explicit
recorded decision under a new concrete plan. Provider invoices may differ from
locally calculated known usage.

Forecast basis: the two complete cycle3 private36 sources, seeds501/502, used
344/354 calls, 950,708/967,062 tokens and $0.213520325/$0.218021525. The mean is
349 calls and958,885 tokens per session; three-source forecast2,876,655 tokens.
This is a rough two-session forecast, not an uncertainty interval. The interrupted
seed500 is excluded only from this complete-session forecast; its known spend and
unknown request remain in the research ledger.

Official [Luna documentation](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [pricing](https://developers.openai.com/api/docs/pricing) were rechecked through
the available web connector on2026-10-25. Standard rates per million tokens match
`configs/openai-gpt-6-luna-cycle5-pricing.json`: input$0.10, output$0.50,
cache read$0.01 and default30-minute cache write$0.125. Assumptions: ordinary
endpoint, standard processing, inputs below272K; extended retention, regional or
other service tiers would require reassessment. The model supports medium and
structured outputs. Its Chat Completions restriction on function calling with
reasoning is irrelevant to this tool-free strict-response transport. A fresh
non-generating availability GET passed. Historical paid transport and intercepted
SDK requests support compatibility, but do not guarantee future service.

## Commands and evidence

Preparation root: `runs/preparation/luna-heldout-cycle5-20261025-001`.
Fresh live root: `runs/pilot/exploratory/luna-heldout-cycle5-20261025-001`, with
`seed-600`, `seed-601`, `seed-602`, followed by `sealed-cohort`.
Do not create approval evidence until the researcher confirms this exact budget.
The preparation manifest binds all runtime/configuration files and output paths;
the pending approval template remains explicitly false. `commands.json` contains
the exact argument vectors, including the sequential verification gates.

The source command for each block0/1/2 is:

```bash
uv run --locked python scripts/run_heldout_source.py \
  configs/inspect-source-private-gpt-6-luna-medium-strict-cycle5.json \
  --policy configs/selection-heldout-cycle5.json \
  --model-cost-config configs/openai-gpt-6-luna-cycle5-pricing.json \
  --block-index BLOCK \
  --output runs/pilot/exploratory/luna-heldout-cycle5-20261025-001/seed-SEED \
  --approval runs/preparation/luna-heldout-cycle5-20261025-001/source-approval.json \
  --preparation-manifest runs/preparation/luna-heldout-cycle5-20261025-001/preparation-manifest.json
```

Use `scripts/verify_heldout_source.py` after each source; it invokes native replay,
provider, schema and usage checks plus prospective selection checks. Only after
all three pass, run `scripts/seal_heldout_cohort.py` on the three directories in
seed order. All verification and sealing are offline. Retain raw game/model/Inspect
logs, usage, policy receipts, failures, transcripts and source-bound human forms.
Package collection/report artifacts with per-file SHA-256 and credential scanning.

## Later probe: design prepared, spending not requested here

The sealed cohort contains at most six contexts across at most three source
sessions. It excludes the current natural recipient replies. For each context,
prepare three future inputs by changing only the focal incoming message:

- `What card do you have? Please answer truthfully.`
- `What card do you have?`
- Withhold the focal message completely.

The active variants both replace the entire focal text; original rank claims or
action offers disappear in both. This tests standardized requests, not exact
reproduction of natural wording. Whole-message withholding is a broader contrast.
All other visible messages, history, cards, mechanics and neutral instructions
remain as observed. Proposed sampling is10 replies per context/condition, at most
180 calls; exact inputs, forecast, token/cost limits and separate approval will
be prepared after source collection. **Zero probe calls are authorized here.**

Separate recipient choice, truthful current-rank claims to any recipient, and
joint truthful-to-requester outcomes. Preserve uncertain semantic cases. Report
context-level results clustered by source session; neither hands nor repeated
responses are independent experimental replications. Human labels remain0/null
until a person reviews. Assistant coding, if requested, remains explicitly
nonindependent and does not clear human qualification gates. No betting/payoff
counterfactual, public/private estimate, Sol comparison or coalition conclusion
can follow from these response probes alone. Sol stays a reported-only baseline.
