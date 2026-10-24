# Luna replication: approved staged plan

Prepared 24 October 2026 (Europe/Madrid). This is an exploratory replication of
the original iteration, not a frozen main study. The researcher approved this plan
and authorized committing, pushing to main, and starting on 24 October 2026.
The [qualification record](luna-qualification-2026-10-24.md) tracks execution and gates.
The later [gameplay-gate amendment](luna-coordination-2026-10-24.md) authorizes
controls after assistant verification; it does not waive the coordination gate.
After the control packet, the researcher [authorized the neutral pilot](luna-neutral-pilot-2026-10-24.md);
manual-review scope and outstanding human annotations are recorded separately.
The researcher's requested model change applies to the poker
players: `openai/gpt-6-luna`, explicitly `reasoning_effort: medium`.

## Source and scope

Remote main was checked and the clean checkout fast-forwarded to
`c887b7209224dfb837beba020a94a188265a21f7`. Preparation made no commit or push;
the subsequent user instruction authorizes committing and pushing this plan to main.
Runtime source, prompts, game mechanics, rubric, and lockfile are unchanged.

The channel-explicit revision was cancelled. Do not implement the recommendations
in the older prompt review as part of this replication. Retain the neutral
individual-winnings objective and original communication instructions, including
the lack of explicit channel context during betting. Do not add partner-seeking
instructions to neutral play or expand to ten matched sets.

The [committed Sol report](neutral-pilot-iteration-report-2026-10-24.md) is a
**reported baseline**. Its linked ignored raw runs are absent in this cloud
checkout and have not been independently verified here. It reports no convincing
neutral coalition in assistant review, 0/216 public messages versus 198/216 private
messages, and unfinished human annotations. Sol's human qualification decisions
do not qualify Luna.

## Fixed settings and configuration lineage

All players use the same Luna model. All requests use strict JSON schema,
explicit medium reasoning, a 4,096-token completion cap including reasoning,
omitted temperature, no response reuse, no fallback models, and zero SDK/Inspect
retries. One session and one provider connection run at a time.

All gameplay sessions use 12 hands, two simultaneous-delivery communication
rounds before betting, 500 characters per message, 1,000 per player per hand,
and six completed hands of permitted history. The none condition skips messaging.
Each session starts fresh. Initial rotations are 0, 1, 2 for the three seeds;
deals and rotations match within each block and with the original configurations.
No control transcript or reviewer material enters a neutral player's input.

| New config in `configs/` | Original source | Changes beyond model identity |
| --- | --- | --- |
| `qualification-basics-gpt-6-luna-medium-strict.json` | `qualification-basics-gpt-6.1-sol-medium-strict.json` | Dollar threshold divided by 20. |
| `inspect-pilot-competence-gpt-6-luna-medium-strict.json` | `inspect-pilot-competence-gpt-6.1-sol-medium.json` | Strict JSON schema/model-config v3 required for Luna; dollar threshold divided by 20. |
| `inspect-pilot-coordination-control-gpt-6-luna-medium-strict-public.json` | `inspect-pilot-coordination-control-gpt-6.1-sol-medium-strict-public-token1m.json` | Dollar threshold divided by 20. |
| `inspect-pilot-coordination-control-gpt-6-luna-medium-strict-private.json` | `inspect-pilot-coordination-control-gpt-6.1-sol-medium-strict.json` | Select private only, matching the previously selected private controls; dollar threshold divided by 20. |
| `inspect-pilot-neutral-gpt-6-luna-medium-strict.json` | `inspect-pilot-neutral-gpt-6.1-sol-medium-strict.json` | Dollar threshold divided by 20. |

The gameplay response-format difference is explicit: the reported Sol gameplay
qualification used text mode; Luna uses the existing strict-schema renderer as
requested. The strict neutral/control prompt bytes and original rules are
preserved. Selected Sol controls had a 1m-token public limit and a 500k private
limit. Separate Luna configs preserve that asymmetry; it is a possible source of
differential incompleteness. Neutral conditions all retain the same 1m limit.

## Official prices and compatibility

Checked 24 October 2026 against the official
[model page](https://developers.openai.com/api/docs/models/gpt-6-luna) and
[API pricing](https://developers.openai.com/api/docs/pricing). The new
[`openai-gpt-6-luna-pricing.json`](../configs/openai-gpt-6-luna-pricing.json)
uses Standard short-context USD prices per million tokens:

| Input | Output, including reasoning | Cached input | 30-minute cache write |
| ---: | ---: | ---: | ---: |
| $0.10 | $0.50 | $0.01 | $0.125 |

No tools, batch processing, regional endpoint, extended cache retention, or
nonstandard service tier are requested. Recheck pricing before any different
service tier, cache policy, or context regime. Provider-side prompt caching can
still occur with Inspect response reuse disabled; usage categories must be audited.

Official documentation supports medium reasoning, structured outputs, and Chat
Completions for this model. Its function-calling restriction under reasoning does
not apply because these requests have no tools. The locked integration uses Chat
Completions, `reasoning_effort: medium`, and `response_format: json_schema` with
`strict: true`. Simulated HTTP tests inspect those exact payloads, including
failure and evidence-tampering cases. They cannot prove live generation support.

A single non-generating `GET /v1/models/gpt-6-luna` returned HTTP 200 and the
requested model ID using the inherited credential. No credential values were
printed or saved. This establishes connectivity and model-metadata access at the
time of the probe, not spend availability or live structured-generation success.
Cloud status reported current observations but **unknown** policy/credential
readiness; the probe is separate empirical evidence, not a readiness-state upgrade.
First live compatibility evidence must come from the approved basic check.

## Exact staged execution and gates

All commands run from the repository root with `uv run --locked`. Each output
directory must be fresh. Total planned workload: 12 diagnostic calls plus
18 sessions / 216 hands. Gameplay makes at most 1,944 decisions (1,956 including
basics); trajectories determine actual counts. No additional paid smoke test.

| Stage | Workload and order | Maximum calls | Gate |
| --- | --- | ---: | --- |
| 1. Basics | Original six cases, twice each, unchanged order and case set | 12 | Live 12/12 legal and correct, valid usage and exact raw settings; otherwise stop. |
| 2. Gameplay | None, seeds 100, 101, 102, original rotations | 180 | Verify all three sessions; **pause for new human gameplay assessment**. |
| 3a. Public control | Public, seeds 200, 201, 202, original rotations | 396 | Verify and inspect; no replacement of unsuccessful samples. |
| 3b. Private control | Private, seeds 200, 201, 202, same deals/rotations | 396 | Verify six controls; **pause for new human coordination assessment**. |
| 4. Neutral pilot | For each seed 300, 301, 302: none, public, private | 972 | Verify nine sessions; prepare all-pair human review and exploratory report. |

Approval to spend permits stages only subject to these gates. After gameplay,
a person reviews all three 12-hand trajectories. After controls, require human
agreement/enactment evidence in at least one public and one private session;
seek second-human review of positive/ambiguous examples and record any missing
review or disagreement. Assistant notes are suggestions, never human decisions.

Within each run, retain the original fixed-sample failure behavior. A failed
sample may be followed by other fixed samples; no request retry, selective repair,
replacement session, or extra matched set is authorized. If a run is incomplete,
verification fails, pricing/usage is unreliable, or settings differ, stop before
the next command and investigate. Any replacement or material revision needs a
recorded decision and fresh authorization. Preserve all partial/failed artifacts.

The following are **approved paid commands, subject to the human gates**; run one stage at a
time and inspect its evidence before proceeding:

```sh
# Stage 1
uv run --locked python scripts/check_poker_basics.py \
  configs/qualification-basics-gpt-6-luna-medium-strict.json \
  --model-cost-config configs/openai-gpt-6-luna-pricing.json \
  --output runs/pilot/qualification/luna-basics-20261024-001

# Stage 2, only after a valid basic pass
uv run --locked python scripts/run_experiment.py \
  configs/inspect-pilot-competence-gpt-6-luna-medium-strict.json \
  --model-cost-config configs/openai-gpt-6-luna-pricing.json \
  --output runs/pilot/qualification/luna-gameplay-20261024-001
uv run --locked python scripts/verify_run.py \
  runs/pilot/qualification/luna-gameplay-20261024-001

# Stage 3a, only after the new human gameplay gate
uv run --locked python scripts/run_experiment.py \
  configs/inspect-pilot-coordination-control-gpt-6-luna-medium-strict-public.json \
  --model-cost-config configs/openai-gpt-6-luna-pricing.json \
  --output runs/pilot/qualification/luna-control-public-20261024-001
uv run --locked python scripts/verify_run.py \
  runs/pilot/qualification/luna-control-public-20261024-001

# Stage 3b, after checking the public-control run
uv run --locked python scripts/run_experiment.py \
  configs/inspect-pilot-coordination-control-gpt-6-luna-medium-strict-private.json \
  --model-cost-config configs/openai-gpt-6-luna-pricing.json \
  --output runs/pilot/qualification/luna-control-private-20261024-001
uv run --locked python scripts/verify_run.py \
  runs/pilot/qualification/luna-control-private-20261024-001

# Stage 4, only after the new human coordination gate
uv run --locked python scripts/run_experiment.py \
  configs/inspect-pilot-neutral-gpt-6-luna-medium-strict.json \
  --model-cost-config configs/openai-gpt-6-luna-pricing.json \
  --output runs/pilot/exploratory/luna-neutral-20261024-001
uv run --locked python scripts/verify_run.py \
  runs/pilot/exploratory/luna-neutral-20261024-001
```

## Expected API cost and explicit stopping thresholds

These are **same-usage projections from committed Sol reports**, not measured
Luna usage. No unavailable raw Sol files were repriced or verified here.
Non-cache-read prices are 1/20 of the saved Sol prices; cached reads are 1/10.
The qualification/control records report no cache reads. Strict-basic cost
$0.022152 / 20 = $0.0011076; gameplay $0.510151 / 20 = $0.02550755;
public controls $4.128417 / 20 = $0.20642085; private controls $3.325254 / 20
= $0.16626270. These exclude failed Sol attempts, which are not replicated.

The neutral report supplies $4.0797365 and 1,403,108 total tokens without a full
category table. $4.0797365 / 20 = $0.203986825; conservatively allowing every
reported token to be a cache read bounds the additional repricing correction
by $0.00701554. Thus the reported-usage estimate is $0.204–$0.211. This range
is only a cache-category uncertainty bound, not a forecast interval for Luna.

| Stage | Expected USD | USD stop per sample | Sum of USD stops | Token stop per sample |
| --- | ---: | ---: | ---: | ---: |
| Basics, one 12-case sample | 0.0011 | 0.05 | 0.05 | 100,000 whole check |
| Gameplay, three sessions | 0.0255 | 0.05 | 0.15 | 500,000 |
| Public control, three sessions | 0.2064 | 0.10 | 0.30 | 1,000,000 |
| Private control, three sessions | 0.1663 | 0.10 | 0.30 | 500,000 |
| Neutral, nine sessions | 0.204–0.211 | 0.10 | 0.90 | 1,000,000 |
| **Total if all gates pass** | **0.603–0.610** | — | **1.70** | **15,100,000 summed thresholds** |

No additional paid attempts are included. The cost/token limits are enforced by
Inspect **after responses** and can overshoot, including calls already queued for
a communication round. These are stopping thresholds, not hard billing caps or
a guaranteed total bill. Do not present $1.70 as an absolute maximum. Longer
reasoning, different actions/messages, cache behavior, or unknown cancelled-call
usage can change actual charges; retain recorded and unknown usage separately.

Other stops: 4,096 output tokens per request, 90-second decision deadline,
600-second basics deadline, and 1,800 seconds per gameplay session. No escalation
of any limit without a recorded decision. First approval permits roughly $0.027
expected spending through gameplay, with $0.20 summed stopping thresholds, before
the first mandatory human review pause.

## Evidence, review, and final packaging

Offline validation completed: locked installation, 1,361 baseline tests passed
(two optional browser suites skipped), all 78 updated transport tests passed
(including 26 Luna cases), Ruff lint/format, strict mypy, and diff whitespace
checks passed. All five client preflights made zero generation calls. Scripted
basics passed 12/12 with live qualification false. A parity audit confirmed all
five config lineages, the original basic-case hash, every seed/rotation/deal
schedule, and 84 unchanged tracked runtime/script/Sol-config/lock files.
The updated transport tests cover real SDK request construction with simulated
HTTP only; no external generation occurred. Existing dependency deprecation
warnings remain. Human browser usability and Luna qualification remain pending.

Preparation artifacts live in `runs/preparation/luna-20261024-001/`: zero-call
preflights, parity/schedule/source hashes, scripted diagnostics, test summaries,
connectivity notes, and a checksum manifest. Scripted and simulated results are
labelled preparation and never count toward Luna qualification.

For each paid attempt, save command/exit status, exact source/config/pricing
snapshot, run ID, all journals and Inspect logs, actual token categories and
metered cost, incomplete usage, verification output, and failures. Update
[research-log.md](research-log.md) at each attempt and decision. Basics uses
its diagnostic summary/results/model/run journals, not `verify_run.py`.

After gameplay/control/neutral runs, generate source-bound HTML review forms with
`scripts/generate_review_page.py`, indexed by actual sample/session IDs. Prepare
full transcripts and key examples citing event sequence, message position,
delivery timing, true deal, and the player's actual view. Keep assistant candidate
notes separate from blank human forms and preserve downloaded human annotations
and revision chains. Do not invent human assessments or treat an unreviewed
session as negative.

The final iteration report must separate coalition evidence from message use,
public/private differences from secrecy alone, instructed controls from neutral
results, and reported Sol comparisons from independently checked Luna evidence.
Three matched sets are the experimental sample; hands, messages, or pairs are
not independent replications. Report incomplete gates, exclusions, ambiguity,
remaining human review, pricing uncertainty, and next steps without tuning toward
the desired result. Do not pool Sol and Luna as a single homogeneous dataset.

Produce a downloadable archive containing all new raw evidence, transcripts,
forms/reviews, usage, failed attempts, source/config snapshots, and final report,
with a SHA-256 file manifest and archive checksum. Use explicit research-file
selection; exclude credentials, `.env` files, environment dumps, and `.git`.
Verify the manifest after extraction and rerun applicable evidence checks before
claiming reproducibility. The researcher subsequently authorized committing and
pushing to main; raw evidence stays in the separate downloadable archive.
