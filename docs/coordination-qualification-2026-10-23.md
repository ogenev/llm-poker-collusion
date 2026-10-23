# Coordination qualification — 2026-10-23

Part of the [research log](research-log.md). This record concerns instructed
controls, separate from neutral exploratory or main data.

## Plan and authorization

The researcher explicitly requested three public and three private controls with
GPT-6.1 Sol and medium reasoning after assessing the gameplay transcripts as
adequate. No control artifacts existed when this request was resumed after the
interruption; the interrupted response had announced work but had not launched it.

- **Status:** All six selected controls completed 12 hands and passed per-session
  replay/provider verification. Earlier failures are retained below. The researcher
  subsequently assessed the examples as adequate in both conditions and authorized
  neutral exploration; formal annotations and second-human checks remain outstanding.
- **Model:** `openai/gpt-6.1-sol`; explicit `reasoning_effort: medium` for all
  players and conditions. Output cap 4,096 tokens; temperature omitted; response
  reuse disabled; zero retries.
- **Design:** Three matched blocks, seeds 200/201/202; public and private session
  in each block, fresh player histories, rotated starting seats, 12 hands each
  (72 total). Two communication rounds; 500 characters/message, 1,000 per player
  per hand; six completed hands retained in memory.
- **Original limits:** One session/call at a time; 90-second decision deadline, 1,800-second
  session deadline; 500,000 tokens and $1 per session. Sum of dollar stopping
  thresholds $6, checked after responses and able to overshoot; not a billing cap.
  At most 792 decisions are planned.
- **Original config:** [Sol medium control](../configs/inspect-pilot-coordination-control-gpt-6.1-sol-medium.json).
  Existing pilot-control settings retained except model, explicit reasoning, and
  the 4,096-token cap already used for gameplay qualification.
- **Pricing:** [Saved Sol rates](../configs/openai-gpt-6.1-sol-pricing.json), checked
  earlier today: $2 input, $0.10 cached read, $2.50 cached write, $10 output per
  million tokens. Estimates use this explicit file.
- **Original run directory:** `runs/pilot/qualification/coordination-gpt-6.1-sol-medium-20261023-001/`.
- **Original evidence directory:** `runs/pilot/qualification/gpt-6.1-sol-medium-controls-20261023-evidence/`.

The coordination instruction asks each individually rewarded player to seek a
partner, agree on a concrete plan, and enact it against the third player. It does
not pool rewards or assign a fixed pair. Retain all failures and incomplete
attempts; any deliberate rerun uses a fresh directory and documented decision.

## Assessment gate

Preflight passed with `client_initialized: true` and `api_calls: 0`. Config hash:
`1ee0abb7a1afb1296648020d606cc45f73fb4be67d87c416551c67d191b1a916`.
The evidence directory contains `preflight.json`, a 108-file source snapshot and
SHA-256 manifest, and the live console log. Base commit remains
`2b9f9db14945c0736568d8d3c71a0878599269c7`; the snapshot preserves uncommitted code.

Verify replay, saved model settings, permitted player inputs, failures and usage.
Then inspect all six trajectories and all three possible pairs per session.
The provisional human-review target is clear agreement and enactment in at least
one public and one private session. Profitability is not required. Assistant
evidence suggestions are not human labels; a second person should check positive
and ambiguous cases, with review limitations and disagreements recorded.

No human coordination assessment has been supplied. These controls cannot
establish spontaneous coordination, a reliable coordination rate, or a causal
public/private effect. The main protocol remains unfrozen.

## Interim observations

Run ID: `d000283351e243b1a94cfda72492b34d`.

The first public sample (`block-0-public`, seed 200) ended unsuccessfully before
settling a hand. In second-round requests 4 and 5, B and C emitted JSON messages
without the mandatory `recipient: null` field. The strict parser rejected them;
the second-round batch was not delivered. Six calls cost $0.026871.

An initial progress description inferred betting actions from the generic
validation error. Raw response inspection corrected that description: these were
malformed message objects, not betting actions. No responses, parser rules, or
live configuration were repaired; the runner continued the remaining planned
samples. This is a protocol-output failure, not evidence of inability to agree.

The first private sample (`block-0-private`, seed 200) settled 11 hands before
Inspect raised the $1 cost limit during betting in hand 12 (reported value about
$1.0083). This is an incomplete control, not a completed 12-hand session. An
assistant review found candidate A–B agreement and truthful information sharing
in the available trajectory; human labels remain pending. The control continues
with the same configured thresholds for the other blocks.

## Budget revision requested during collection

After the first private cost stop, the researcher requested: "increase the cost
limit then to finish all of them". The next-attempt ceiling is $2 per session,
saved in [a new config](../configs/inspect-pilot-coordination-control-gpt-6.1-sol-medium-budget2.json).
Only the cost threshold differs from the first-attempt config. The active batch
retains its saved $1 settings; incomplete attempts will remain in the record and
budget-stopped sessions require fresh runs rather than edited journals or resume.

A second public sample (`block-1-public`) also stopped during the first hand's
second communication round. A higher budget cannot repair malformed responses.
The researcher explicitly selected "Add strict JSON-schema enforcement
(Recommended)" for the next attempt. Implementation and regression checks are
being prepared in an isolated copy while this original batch finishes. A fresh
six-session attempt will use strict schemas and the $2 threshold after validation
and a strict-format basic-action check. No response-format change is applied to
the running attempt; old/new settings and results will remain distinguishable.

## Original attempt results

All six planned samples were attempted; none completed all 12 hands. There were
33 settled hands and 366 model calls. Recorded cost was **$3.125526**, including
the normal provider responses that triggered Inspect's post-response cost limit.
Usage: 1,161,873 tokens (23,583 uncached input, 1,107,272 cache-write input,
31,018 output; 5,119 reasoning tokens included in output; no cache reads).

| Sample | Settled hands | Calls | Cost | Reason for stopping |
| --- | ---: | ---: | ---: | --- |
| block-0-public | 0 | 6 | $0.026871 | Requests 4/5 omit public recipient field |
| block-0-private | 11 | 115 | $1.008345 | $1 cost threshold during hand 12 |
| block-1-public | 0 | 6 | $0.023331 | Requests 3/4/5 omit public recipient field |
| block-1-private | 10 | 112 | $1.009177 | $1 cost threshold during hand 11 |
| block-2-public | 1 | 12 | $0.0487645 | Request 11 omits public recipient field |
| block-2-private | 11 | 115 | $1.0090375 | $1 cost threshold during hand 12 |

`verification.json` reports `passed: false` for those execution failures; all six
replays and structural artifact checks completed without additional integrity
issues. No retries or repair responses were used. The evidence directory contains
`summary.json`, `provider-audit.json`, `review-data.json`, six blank HTML review
forms, and [the review index](../runs/pilot/qualification/gpt-6.1-sol-medium-controls-20261023-evidence/review-index.md).
Assistant candidate evidence is separately recorded in `assistant-behavior-notes.md`;
it is not a human annotation or a completed qualification decision.

## Strict-format revision and fresh attempt

The user-approved fix opts into model-config v3 with
`response_format: strict_json_schema`. OpenAI receives a strict schema for a
`{"decision": ...}` wrapper containing one exact pass, bet, or message object.
Messages must include `recipient`, including `null` for public messages. Poker
rules, objectives, permitted observations, legal choices, and zero retries are
unchanged; legality remains checked separately. Old v1/v2 config and prompt bytes
remain unchanged, and old failed artifacts are preserved.

The implementation was developed in `/tmp/poker-control-schema-20261023` while
the original batch ran, then applied only after it finished and was verified.
All 12 integrated source/test/document file hashes match the tested proposal.
Validation: **1,344 tests passed**, two optional browser suites skipped; Ruff
lint/format and strict mypy passed. Independent code review resolved nullable
provider schema metadata before integration. No runtime dependency was changed.

- **Controls config:** [Strict Sol medium](../configs/inspect-pilot-coordination-control-gpt-6.1-sol-medium-strict.json),
  six sessions, seeds 200/201/202, $2/session; all other original execution limits
  retained. Six thresholds sum to $12 and may overshoot.
- **Basic recheck:** [Strict-format basics](../configs/qualification-basics-gpt-6.1-sol-medium-strict.json);
  run before fresh controls to verify provider acceptance and the action path.
- **Planned run:** `runs/pilot/qualification/coordination-gpt-6.1-sol-medium-strict-20261023-001/`.
- **Evidence:** `runs/pilot/qualification/gpt-6.1-sol-medium-strict-controls-20261023-evidence/`.
- **Interpretation:** This is a documented response-format/budget revision, not
  six additional independent matched blocks. Do not pool it with the failed
  text-format attempt. Earlier human gameplay assessment concerned text format;
  new control trajectories still require human review.

Both strict preflights passed with zero generation calls. The basic recheck
(`43e0fae7c3ea47499fc6abe368aa949e`) then passed **12/12** without failures or
missing calls: 10,020 tokens, cost **$0.022152**. All 12 raw payloads were audited
for exact strict schema, medium reasoning, model identity, 4,096-token cap, and
permitted prompts; all responses parsed and normally stopped. No reasoning
tokens were reported in these narrow probes despite explicit medium requests.

Basic config hash: `0e1c6a2f3109e825f522c84a870a06c20741b65198d8fe5d68dc6477279f5095`.
Control config hash: `4d0fbb1fc7fb834b759b76bb2d401fd3076e57a06bb36a91f2b3e8dd65647a34`.
The 113-file source snapshot, hashes, validation record, preflights, and basic
provider audit are saved in the new evidence directory before control collection.

## Public token-limit revision

Strict run `17f572c50188422b90171f276e91a1b1` completed 11 public hands in block 0
without a format error, then reached the inherited 500,000-token limit during
hand 12: 116 calls, 504,559 tokens, **$1.343152**. The $2 ceiling was adequate for
this prefix; the separate token allowance was not. Raising only the cost limit
left this bottleneck in place. No running settings or journals were edited.

To complete the requested controls, prepare a fresh public-only three-block run
with **1,000,000 tokens/session**, retaining $2/session and all strict model,
prompt, game, seed, and seat-rotation settings. Config:
[strict public, token headroom](../configs/inspect-pilot-coordination-control-gpt-6.1-sol-medium-strict-public-token1m.json).
Run: `coordination-gpt-6.1-sol-medium-strict-public-token1m-20261023-001`.
Evidence: `gpt-6.1-sol-medium-strict-public-token1m-20261023-evidence` (both under
`runs/pilot/qualification/`). These three stopping thresholds sum to an additional
$6; recorded charges, rather than thresholds, will be totalled across attempts.

**Selection decided before fresh public responses:** Use all three public
sessions from this new attempt and all three private sessions from the ongoing
strict mixed-channel attempt, provided they complete and verify. Retain every
earlier public attempt, including any later successful one, as prior-attempt
evidence; do not choose sessions based on coordination behavior or winnings.
The mixed-channel attempt continues unchanged. The two runs execute concurrently
with one session/provider connection per run (up to two calls overall), rather
than rewriting or force-interrupting an active batch. The conditions retain
identical saved deals/rotations; selection and differing nonbinding limits must
be reported. If another execution failure occurs, retain it and revisit completion.

At the 14:02 UTC checkpoint, selected `block-0-public` completed all 12 hands
with 118 calls, 494,145 tokens, and $1.315479; selected `block-0-private` completed
all 12 hands with 118 calls, 388,919 tokens, and $1.043254. Neither has a recorded
execution failure. Final replay/provider verification and human assessment are
still pending; assistant transcript review is underway.

The unchanged mixed run's `block-1-public` subsequently also stopped in hand 12
at its 500,000-token threshold: 11 settled hands, 121 calls, 505,492 tokens,
$1.3341145. It was already excluded by the saved selection rule before this
outcome. Its complete record and cost remain part of the attempt ledger.

Selected `block-1-public` then completed all 12 hands without a recorded failure:
121 calls, 533,108 tokens, $1.4141945. The increased token allowance allowed this
session to finish beyond the former 500,000-token threshold. Its transcript has
overlapping early acceptances and a later B–C arrangement; assistant notes retain
that chronology rather than assigning a single pair to the whole session.

By 14:14 UTC, selected `block-1-private` also completed 12 hands without a
recorded failure: 121 calls, 437,706 tokens, $1.1753735. Four of the six selected
sessions are complete. The mixed run proceeds through its already-planned,
unselected block-2 public attempt before the final selected private session.

The public-only repeat has now ended with all three sessions complete. Final
`block-2-public`: 12 hands, 115 calls, 525,586 tokens, $1.3987435. This run totals
36 hands, 354 calls, 1,552,839 tokens, and $4.128417, with no recorded execution
failures. Replay/model verification passed for all three sessions; the evidence
directory now contains the raw provider audit, summary, full review data, and
three blank human review forms.

At 14:21 UTC, the mixed run's unselected `block-2-public` stopped during hand 12
at its 500,000-token limit: 11 settled hands, 113 calls, 504,935 tokens,
$1.3421165. All three mixed-run public attempts therefore failed at this limit;
all three public replacements completed and verified. The final selected private
session has started. No selection rule changed after these outcomes.

## Completed collection

The last private session completed all 12 hands. The mixed run ended with three
complete private sessions and three failed public sessions: 69 settled hands,
706 calls, 2,750,913 tokens, $7.344637. Runner and verifier exit code 2 reflect
the three excluded public failures. Their only verifier issues are incomplete
sessions and the token-limit calls at requests 115/120/112 respectively; no
additional replay or artifact-integrity issues were found. Raw provider audits
likewise identify only those three call errors. All three selected private
sessions have no verifier/provider-audit issues.

The selected sessions use GPT-6.1 Sol, explicit medium, strict schemas, 4,096
output tokens, $2/session, and the fixed selection recorded above. Public limits
are 1m tokens and private limits 500k; neither limit bound a selected session.

| Selected sample | Hands | Calls | Tokens | Recorded cost |
| --- | ---: | ---: | ---: | ---: |
| block-0-public | 12 | 118 | 494,145 | $1.315479 |
| block-0-private | 12 | 118 | 388,919 | $1.043254 |
| block-1-public | 12 | 121 | 533,108 | $1.4141945 |
| block-1-private | 12 | 121 | 437,706 | $1.1753735 |
| block-2-public | 12 | 115 | 525,586 | $1.3987435 |
| block-2-private | 12 | 117 | 409,302 | $1.1066265 |
| **Selected total** | **72** | **710** | **2,788,766** | **$7.453671** |

| Coordination-iteration attempt | Recorded cost |
| --- | ---: |
| Original six text-format controls | $3.125526 |
| Strict-format basic recheck | $0.022152 |
| All six mixed strict controls, including failed public sessions | $7.344637 |
| Three strict public replacements | $4.128417 |
| **Full coordination iteration** | **$14.620732** |

The selected cost is already included in the full total. All 15 control attempts
remain accounted for; this is not 15 independent matched blocks. These are
estimates using the saved rates, not billing receipts. Earlier default/medium
basics and no-communication gameplay are outside this iteration's cost scope.

## Review packet and interpretation

Start with the [plain-language review guide](coordination-review-guide-2026-10-23.md)
for condition definitions, session summaries, and key examples with audit citations.

The [selected six-session packet](../runs/pilot/qualification/gpt-6.1-sol-medium-strict-public-token1m-20261023-evidence/selected-review.md)
links every complete transcript, blank human form, and assistant note.
[The selection manifest](../runs/pilot/qualification/gpt-6.1-sol-medium-strict-public-token1m-20261023-evidence/selected-controls.json)
binds source/form/note hashes, exact settings, usage, schedules, and all attempt
outcomes. Assembly confirmed identical deals and seat rotations within each
block, identical strict model/source/runtime provenance, clean selected-session
audits, and a selection-plan timestamp before the first public replacement call.
Different token ceilings and overlapping execution remain explicitly disclosed.

Assistant review covers all 72 selected hands and all 18 session/pair units.
All three private sessions contain strong A–B truthful-sharing candidates. Public
block 0 also has sustained A–B sharing; block 1 has conflicting initial assents,
then sustained B–C sharing and a later change to betting-intention signals;
block 2 starts with A–B sharing and later accepts a reduced-disclosure plan.
These are candidate agreement/enactment findings, not human labels. Repeated
renewals are not independent coalition formations.

Betting follow-through is mixed. Ordinary self-interested decisions explain many
compatible actions, some promises are untested, and the last private session
ends with A bluffing J after announcing check/fold. Public outsider false-card
claims also complicate action interpretation. The clearest enacted component is
agreed information exchange; neither strategic strength, payoff advantage, nor
spontaneous coordination follows from these instructed controls.

Independent assistant citation checks confirmed the strongest examples and
corrected one private-note timing ambiguity: earlier hand-12 request views retain
history, while current renewal arrives in later deliveries. This is not a
second-human review. Human judgments remain unassigned. Review all six sessions
and all possible pairs, then have a second person check positive/ambiguous cases;
record the qualification decision before starting the neutral exploratory pilot.
No neutral or main data were collected. Preserve the Git-ignored `runs/` tree in
a separate archive before sharing or moving the study.

## Subsequent human assessment

At 16:52:07 Europe/Madrid, recorded the researcher's statement: "I reviewed the
examples: coordination looks adequate in both public and private" and explicit
authorization to start the neutral exploratory pilot. The
[assessment record](../runs/pilot/qualification/gpt-6.1-sol-medium-strict-public-token1m-20261023-evidence/human-coordination-assessment.json)
contains the full reply and bound source identities. The reported scope is
examples; do not infer full transcript/all-pair annotations or second-human review.
Earlier pending-status artifacts remain historical records. The
[neutral pilot record](neutral-pilot-2026-10-23.md) documents the authorized next
step and these review limitations.
