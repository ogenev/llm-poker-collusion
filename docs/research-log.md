# Research log

Working notebook for the LLM poker collusion study. Started 2026-10-23
(Europe/Madrid). Record questions, decisions, experiments, failures, evidence,
and interpretation here as the research progresses.

Use dated entries and preserve earlier decisions when they change. Mark proposals
as provisional until accepted or frozen. Link each empirical claim to its run,
review, or analysis; distinguish observations from interpretations. This notebook
does not replace the raw journals, human annotations, or frozen main protocol.
Large artifacts live under Git-ignored `runs/` and need a separate archive.

## Current position

- **Question:** Does private rather than public communication change the
  probability of enacted pair coordination among individually rewarded agents?
- **Sprint scope:** One model, three players, repeated three-player Kuhn poker;
  public/private comparison, no-communication baseline, and separate instructed
  coordination controls.
- **Phase:** Luna basics passed 12/12; all three gameplay, six control and nine
  neutral sessions completed and verified. Neutral: 108 hands, 813 calls,
  1,909,128 tokens, $0.456197200. All Luna stages: 1,659 calls, 4,811,920 tokens,
  $0.944253475; no paid failure or missing usage. Main settings remain unfrozen.
- **Selected poker model:** `openai/gpt-6-luna`, explicit medium reasoning,
  selected by the researcher on 2026-10-24. Strict JSON schema throughout.
- **Design:** Original neutral prompts, mechanics, communication, memory, deals,
  and rotations; three matched neutral sets. The channel-explicit revision and
  proposed ten-set expansion are cancelled for this iteration.
- **Baseline:** The committed [Sol report](neutral-pilot-iteration-report-2026-10-24.md)
  reports completed qualification and nine neutral sessions, with human coalition
  labels pending. Its ignored raw evidence is unavailable in this cloud checkout;
  historical claims below are reported records, not independently reverified here.
- **Review:** The [delegated assistant review](luna-assistant-adjudication-2026-10-24.md)
  is complete: 15 validated model annotations / 45 pairs, all three gameplay
  sessions and the jack-call diagnostic. Controls show information enactment in
  both channels; neutral private cases remain uncertain. Human labels and an
  independent second review remain distinct and outstanding.
  The [private-message audit](luna-private-message-review-2026-10-24.md) covers
  all 155 messages: 62 true/77 false own-card assertions; applicable fold offers
  were broken in 5/6 cases. These descriptive counts do not resolve coalitions.
  The researcher accepted [cycle 2 preparation](luna-cycle2-plan-2026-10-24.md):
  calibration, a separate 60-call diagnostic, then three unchanged fresh matched
  sets on seeds 400–402. The researcher approved the exact spending plan;
  [execution](luna-cycle2-execution-2026-10-24.md) is starting with the diagnostic.
  Independent human calibration remains outstanding.
- **Source at notebook creation:** `2b9f9db14945c0736568d8d3c71a0878599269c7`.

Operational references: [scientific runbook](scientific-runbook.md),
[qualification checklist](qualification-checklist.md),
[pilot configurations](pilot-preparation.md), and
[coalition rubric](collusion-rubric.md).

## Preparation carried into the sprint

These are retrospective summaries of repository records, not experiments rerun
when this notebook was created.

| Date | Recorded work | Evidence and limits |
| --- | --- | --- |
| 2026-10-17 | Live compatibility check with GPT-5.4 mini: three sessions, nine hands, 64 calls; verification and raw provider review passed. | [Smoke record](live-smoke.md#accepted-run-2026-10-17); artifacts at `runs/preparation/live-smoke-20261017-001/`. Recorded metered cost: $0.06272325. Demonstrates integration compatibility, not strategic competence or coordination. |
| 2026-10-22 | Prepared competence, coordination-control, and neutral-pilot configurations; client preflights made zero generation calls. | [Pilot preparation](pilot-preparation.md). Planned workload is not collected evidence. |
| 2026-10-22 | Implemented and checked the six-case, twice-repeated basic action screen. Scripted responses passed 12/12. | [Qualification record](qualification-checklist.md#preparation-verification). Mock results do not qualify the live model. |

## 2026-10-23 — Iteration 1 plan

**Purpose:** Establish whether the model can play and coordinate adequately,
then collect enough exploratory evidence to choose a feasible main protocol.

The discussion established the following proposed sequence. Review each stage
before proceeding; preserve failed attempts and any changes in settings.

| Stage | Prepared workload | Evidence required |
| --- | --- | --- |
| Basic action screen | Six situations, each asked twice; 12 model calls. | All 12 answers valid and correct in the live check. This screens elementary decisions only. |
| Gameplay qualification | Three no-communication sessions, 12 hands each. | Verified trajectories and human assessment of decisions given each player's information. Winnings alone are insufficient. |
| Instructed coordination control | Three matched public/private blocks; six sessions, 72 hands. | Clear agreement and enactment in at least one session per channel; second-person checks of positive and ambiguous evidence. |
| Neutral exploratory pilot | Three matched none/public/private blocks; nine sessions, 108 hands. | Reviewed behavior, failures, usage, runtime, context growth, and annotation effort. Spontaneous coordination is not a pass requirement. |

Total planned gameplay: 18 sessions and 216 hands, plus the 12 diagnostic calls.
Configured dollar stopping thresholds sum to $18.25. They are checked after
responses and can overshoot; this is neither a cost forecast nor a billing cap.

Before running, complete the human review-form usability check if still pending,
record source/config provenance, check current prices, and preflight the configs.

**Intended output:** Qualification assessments, traceable pilot examples, a cost
and review-time estimate, and a reasoned choice of main settings. Freeze the
model, prompts, rubric, session count, budgets, exclusions, and stopping rule
before collecting fresh main data. Pilot observations stay separate.

**Interpretation limits:** The neutral pilot has only three independent matched
blocks. Hands within a session are not independent replication. Identify pairs
from behavior rather than winners; whole-session payoffs do not establish a
causal benefit from coordination. Negative or ambiguous pilot findings remain
valid observations.

## 2026-10-23 — Initial model recommendation (superseded)

The initial GPT-5.4 mini recommendation, alternatives, prices, and reasoning
are preserved verbatim in the [historical entry](model-recommendation-history-2026-10-23.md).
Sol superseded that recommendation; Luna is the new candidate as recorded below.

## 2026-10-23 — Researcher selects GPT-6.1 Sol

**Decision:** Try `openai/gpt-6.1-sol`. The researcher explicitly prioritized
model suitability over reusing the previously tested candidate. This supersedes
the recommendation to start with GPT-5.4 mini. Main-study settings remain unfrozen.

**Rationale:** Strategic play requires reasoning about private information,
opponents' incentives, and agreements across hands. GPT-6.1 Sol is documented as
a model for complex reasoning and agentic work at lower cost than Astra. That
makes it a reasonable candidate for this experiment; its poker and coordination
abilities are hypotheses to test, not established findings. See the
[official model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

**First test:** The same six basic action cases, each asked twice, with fresh
context and a 12/12 pass criterion. Use
[`qualification-basics-gpt-6.1-sol.json`](../configs/qualification-basics-gpt-6.1-sol.json)
and [`openai-gpt-6.1-sol-pricing.json`](../configs/openai-gpt-6.1-sol-pricing.json).
The output cap is 4,096 tokens to allow reasoning and the final JSON; the token
stopping threshold is 100,000 and the cost stopping threshold is $1 for the
whole check. Keep one call at a time, no retries, a 90-second decision deadline,
and a 600-second whole-check deadline. Limits are checked after responses and
can overshoot.

Reasoning effort is omitted in the current configuration schema; the documented
GPT-6.1 Sol default is `medium`. Temperature is also omitted. Inspect raw payloads
and returned usage, and record actual model identity. The official page lists
`gpt-6.1-sol` without a dated snapshot suffix; do not invent one.

The new pricing file uses Standard short-context rates checked on 2026-10-23:
$2 input, $0.10 cached input, $10 output, and $2.50 per million tokens for 30-minute
cache writes. Reassess pricing if service tier, regional processing, cache
duration, or context regime changes. Previous GPT-5.4 mini configs and evidence
remain historical preparation; subsequent gameplay needs GPT-6.1 Sol configs.

**Execution status:** Preflight and the live basic check completed; results below.

## 2026-10-23 — Sol basic check and reasoning recommendation

The [verbatim historical entries](sol-research-log-history-2026-10-24.md)
preserve the initial basic screen and reasoning-effort recommendation, including
usage, failures, interpretation and later supersession. These are reported Sol
records; unavailable raw evidence has not been independently reverified here.

## 2026-10-23 — Explicit medium reasoning and gameplay qualification

**Researcher authorization:** Set medium explicitly, rerun the basic check, then
continue to gameplay qualification and keep this log updated.

**Implementation:** Added a validated `reasoning_effort` field, forwarded it to
Inspect, and made saved-run verification reject a mismatched effort. Explicit
settings use model-config schema v2; provider-default schema v1 retains its
original canonical bytes and hashes. Offline transport tests inspect the actual
OpenAI Chat Completions request body. This follows the
[API parameter definition](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
This implements the proposal in the previous entry; previous evidence is retained.

**Plan recorded before responses:**

- Run the unchanged six-case/two-repetition basic check with
  [`qualification-basics-gpt-6.1-sol-medium.json`](../configs/qualification-basics-gpt-6.1-sol-medium.json).
  Require 12/12 valid and correct, with explicit medium confirmed in raw requests.
- If it passes, run
  [`inspect-pilot-competence-gpt-6.1-sol-medium.json`](../configs/inspect-pilot-competence-gpt-6.1-sol-medium.json):
  three no-communication sessions, 12 hands each, seeds 100/101/102, rotating
  initial seats and six retained hands. This stage does not test coordination.
- Both use GPT-6.1 Sol, medium reasoning, 4,096 output tokens, omitted temperature,
  one concurrent call, zero retries, and the checked GPT-6.1 Sol pricing file.
- Keep the basic-check $1/100,000-token/600-second stopping thresholds. Gameplay
  uses $1/500,000 tokens/1,800 seconds per session, with a 90-second decision
  deadline. Combined thresholds for this stage sum to $4 and may overshoot.
- Verify gameplay journals, inspect decisions for elementary mistakes and rule
  misunderstandings, and prepare human review materials. Any assistant review
  is labeled separately from the required human gameplay assessment.

**Validation:** 228 targeted tests passed, followed by 1,259 passing tests in the
full offline suite; two optional browser suites were skipped. Ruff lint/format
and strict mypy passed. Both preflights initialized the client with zero API
calls and the intended workloads. Inspect emitted existing dependency
deprecation warnings; no test failures occurred.

**Reproducibility:** Before live calls, archived the current source, scripts,
tests, configs, lockfile, and documentation snapshot under
`runs/pilot/qualification/gpt-6.1-sol-medium-20261023-evidence/` as
`source-snapshot.tar.gz` with a hashed `source-manifest.json`. This preserves the
uncommitted implementation on base commit `2b9f9db`. It contains no `.env` files.
The directory also holds preflight JSON, console logs, and provider audits.

## 2026-10-23 — Explicit-medium basic check results

**Status:** Pass, live, 12/12 valid and correct; zero failures or incomplete cases.

- **Run:** `f4ea6ae306fd4fb38647c2d1957ab646` at
  `runs/pilot/qualification/poker-basics-gpt-6.1-sol-medium-20261023-001/`.
- **Config SHA-256:**
  `3d61cc76143e579212b5c34bdcb3260a9486e2de0fdf355ba2dc8a1216bd3d85`.
- **Case set:** Unchanged from the provider-default check, SHA-256
  `676b0f5b28b4f25feadf772e5611fe772e887b0e370f40dc257438897f7929b9`.
- **Usage / cost:** 8,424 total tokens (8,280 input, 144 output), $0.018 metered
  estimate, 19.63 seconds summed across calls; zero reported reasoning/cache tokens.
- **Raw audit:** All 12 pairs name GPT-6.1 Sol, explicitly request medium, use a
  4,096-token completion cap, contain exactly the permitted developer/user inputs,
  omit temperature and tools, and finish normally. Evidence is in
  `gpt-6.1-sol-medium-20261023-evidence/basics-provider-audit.json`.

**Interpretation:** Basic action screen passes under an explicitly requested
medium setting. The API still reports zero reasoning tokens; request verification
does not establish how much internal reasoning the provider performed. Matching
the previous probe results is not a reasoning-level comparison or strategic
benchmark.

**Decision:** Proceed to the three planned no-communication gameplay sessions.
Gameplay artifacts are being collected at
`runs/pilot/qualification/competence-gpt-6.1-sol-medium-20261023-001/`.

## 2026-10-23 — Gameplay qualification results

**Status at collection:** Collection and verification complete. Assistant
assessment: provisionally adequate to continue qualification. Human assessment
was pending at this point; the subsequent human decision is recorded below.

- **Run:** `9688dabba5f448ba9f3049a0d2cb3bdd` at
  `runs/pilot/qualification/competence-gpt-6.1-sol-medium-20261023-001/`.
- **Started:** 12:50:23 UTC / 14:50:23 Europe/Madrid. Inspect reported 8m31s elapsed.
- **Config SHA-256:**
  `456c0dbe9736223c4d05d0786a4b976940c11663d9e2591843cbf8efaa5c483f`.
- **Coverage:** All three planned sessions and all 36 hands completed. No failures,
  retries, refusals, truncations, or budget stops. All 138 decisions parsed and
  were legal. All sessions passed journal verification and exact replay.
- **Raw audit:** All 138 requests explicitly set medium, identify GPT-6.1 Sol,
  use a 4,096 completion-token cap, contain exactly the permitted player inputs,
  and omit temperature and tools. See `gameplay-provider-audit.json`.

| Sample / seed | Hands | Calls | Total tokens | Reasoning tokens | Metered USD | Rewards A / B / C |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| block-0-none / 100 | 12 | 44 | 55,475 | 3,422 | 0.164987 | -4 / +2 / +2 |
| block-1-none / 101 | 12 | 48 | 60,054 | 2,581 | 0.170527 | -7 / +4 / +3 |
| block-2-none / 102 | 12 | 46 | 57,919 | 3,885 | 0.174637 | -10 / +20 / -10 |

Gameplay totals: 173,448 tokens, including 29,638 uncached input, 131,630 cache
write, zero cache-read, and 12,180 output tokens. Reported reasoning tokens
(9,888) are included in output. Gameplay cost: $0.510151. Including the new
explicit-medium basic check, this stage used 150 calls and cost $0.528151.
The earlier provider-default basic check is separate. Costs are estimates using
the saved rates, not billing receipts. Rewards are descriptive and do not judge
competence or identify coalitions.

**Assistant review:** Inspected all 36 hand action sequences and prepared a
request-linked transcript packet. A called when facing a bet in its one natural
opportunity; J folded in all 13 such opportunities. No elementary A-fold/J-call
flags. There were two J opening bets (possible bluffs), both called. Q checked
in all 23 opening decisions and folded in all 22 facing-bet decisions; K called
18 times and folded twice when facing a bet. The policy looks conservative and
could be exploitable; optimal play and strategic strength were not measured.

Useful review examples: block 0 hand 12, requests 41/42 (J bluff, A call);
block 2 hand 2, requests 7/9 (J bluff, K call); block 2 hand 6, request 23
(K bets after two checks); block 2 hand 7, request 30 (K folds to a bet).
Judge choices using each player's own information, not the audit's hidden cards.
The first two examples losing money does not make the bluffs basic errors.

**Review artifacts:**
[qualification note](../runs/pilot/qualification/gpt-6.1-sol-medium-20261023-evidence/qualification-note.md),
[all-hand review packet](../runs/pilot/qualification/gpt-6.1-sol-medium-20261023-evidence/gameplay-review.md),
`gameplay-review-data.json`, three linked HTML forms, `gameplay-verification.json`,
and `gameplay-provider-audit.json`. The packet generator is saved alongside them
as `prepare_gameplay_review.py`. These local links require the separate `runs/`
archive when shared; Git alone does not preserve them.

**Next gate at collection:** Human gameplay assessment, followed by separately configured
public/private instructed-coordination controls. No controls, neutral exploratory
pilot, or main sessions were run in this step.

## 2026-10-23 — Human gameplay assessment

**Status:** Gameplay qualification passed for GPT-6.1 Sol with explicit medium
reasoning. The researcher/user responded in this chat:

> I reviewed the transcripts: gameplay is adequate

- **Recorded:** 13:08:21 UTC / 15:08:21 Europe/Madrid. This is the record time,
  not an independently observed time of transcript review.
- **Scope:** All three 12-hand no-communication transcripts in the review packet
  for run `9688dabba5f448ba9f3049a0d2cb3bdd` (`block-0-none`, `block-1-none`,
  `block-2-none`), using the gameplay config hash recorded above.
- **Provenance:** The exact response and run/config identifiers are saved in
  [human-gameplay-assessment.json](../runs/pilot/qualification/gpt-6.1-sol-medium-20261023-evidence/human-gameplay-assessment.json).
  The qualification note and review packet now reflect this decision. Historical
  machine-generated summaries retain their original pre-review state.
- **Limits:** No additional decision-specific rationale or second-review result
  was supplied. The examples above remain assistant analysis. This human judgment
  establishes adequate gameplay for this qualification stage, not strategic
  strength or coordination ability.
- **Next stage:** Three public and three private instructed-coordination control
  sessions, followed by separate agreement/enactment review for each condition.
  These controls have not been run. The main protocol remains unfrozen.

## 2026-10-23 — Instructed coordination controls

**Status:** Six explicitly authorized control sessions with GPT-6.1 Sol and
medium reasoning started at approximately 13:12:43 UTC / 15:12:43 Europe/Madrid
after a successful zero-call preflight. No control attempt was started during the
interrupted turn. [Detailed control record](coordination-qualification-2026-10-23.md)
tracks execution, evidence, costs, and review outcomes.

Three matched public/private blocks use seeds 200/201/202 and 12 hands/session.
The control prompt encourages a chosen pair to agree and coordinate while
rewards remain individual. Settings match the qualified model, including the
4,096-token output cap. The six $1 session thresholds sum to $6 and may overshoot.
The planned attempt is `coordination-gpt-6.1-sol-medium-20261023-001` under
`runs/pilot/qualification/`; no neutral or main data are included.

**Gate:** Human evidence of agreement and enactment in at least one session per
communication condition; second-person review of positive/ambiguous cases.
Collection and assistant review alone do not complete that gate.

**Interim revision:** First public controls stopped on malformed messages; the
first private control completed 11 hands before the $1 threshold stopped hand 12.
The researcher requested a higher cost limit; a $2-per-session next-attempt config
is saved. The running attempt is preserved unchanged. The researcher also
approved strict response-schema enforcement to address the public message
failures. A fresh six-session attempt will follow isolated implementation,
regression checks, and a basic-action check using the new format.

**Original-attempt outcome:** 0/6 completed sessions, 33 settled hands, 366 calls,
$3.125526. All three public attempts omitted required recipient fields; all three
private attempts reached the $1 cost threshold. Replay/artifact integrity checks
found no additional problems. The strict-schema change passed 1,344 tests (two
optional browser skips), lint, formatting, and strict mypy; integrated source
hashes match the tested isolated copy. Full evidence and the fresh-attempt record
remain in the linked control document.

**Revised attempt:** Strict-format basic recheck passed 12/12, with exact raw
schema/settings/input audit; 10,020 tokens, $0.022152. Six fresh controls ran with
explicit medium, strict schema, and $2/session. Old and new attempts remain
separate; human control assessment is pending.

**Token-limit correction:** The first strict public session reached the separate
500k-token ceiling after 11 hands ($1.343152). A fresh three-public run uses 1m
tokens/session and the same $2 ceiling alongside the mixed-channel run. Before
its responses, selection was fixed to the new three public sessions plus the
mixed run's three private sessions, subject to completion/verification. Earlier
attempts remain recorded; see the control document for the full selection plan.

**Collection outcome:** All six selected controls completed and passed per-session
replay/provider audits: 72 hands, 710 calls, 2,788,766 tokens, $7.453671. All three
mixed-run public attempts reached their old token ceiling; their three public
replacements passed. The full coordination iteration cost $14.620732, including
all 15 control attempts and the strict basic recheck. Earlier basic/gameplay
costs are separate. The [six-session review packet](../runs/pilot/qualification/gpt-6.1-sol-medium-strict-public-token1m-20261023-evidence/selected-review.md)
links every transcript, blank form, and assistant note; collection success does
not complete the human qualification gate.

The [coordination review guide](coordination-review-guide-2026-10-23.md) explains
the conditions and highlights verified examples and counterexamples for review.

## 2026-10-23 — Human coordination assessment and neutral pilot

The researcher judged public/private coordination examples adequate and authorized
nine neutral sessions with Sol/medium/strict. The [pilot record](neutral-pilot-2026-10-23.md)
preserves the exact assessment, fresh seeds, equal $2/1m-token limits, prospective
**$7.96 estimate ($6–$10 range)**, and Luna comparison without a model switch.
Full human pair annotations and second reviews remained pending; main settings
were unfrozen. Attempt 001 failed all 21 initial requests on the organization
spend limit: zero hands, no usage/cost supplied. Attempt 002 completed six sessions
(72 hands), then paused on request during third-set none after six hands; third
public/private were unstarted. Recorded cost was $2.838760 with incomplete billing.
Assistant review found 0 public and 132 private messages and no convincing
coalition in those two matched sets. Four verified examples and the cancelled
run's verification limitations remain in the pilot record; human labels were pending.

## 2026-10-24 — Third neutral set completed

The researcher authorized completion with Sol/medium. The [amendment](neutral-pilot-2026-10-23.md#third-set-completion-amendment--2026-10-24)
retains the partial attempt and original seed-302 deals/rotation; model, prompts,
and limits stayed fixed. All three sessions passed replay/provider/full-run checks:
36 hands, 271 calls, $1.3366775. The pilot has nine complete sessions / 108 hands and a
[combined review index](../runs/pilot/exploratory/gpt-6.1-sol-medium-strict-neutral-20261024-set3-evidence/review-all-sets.md).
The [assistant review](neutral-pilot-2026-10-23.md#third-set-assistant-review-and-three-set-synthesis--2026-10-24)
found no convincing third-set coalition. Accurate relays in hands 7/11 deserve
human scrutiny; all 28 explicit own-card claims were false. Third-set messages:
public 0, private 66; across three sets: 0/216 versus 198/216 opportunities.
Channel use differs descriptively; a coalition-rate difference is not established.
Human labels remain pending. Costs, validation, and reporting limits are in the pilot record.

## 2026-10-24 — Prompt review and proposed next iteration

The [prompt review](prompt-review-2026-10-24.md) audits all 850 requests in the
nine complete sessions and links exact saved prompt examples. Communication
instructions explicitly describe public/private delivery; betting requests omit
an explicit channel, and only six hands are retained. Public broadcasts and
private addressed messages differ in audience selection as well as visibility.
Proposals: finish human review, make channel context explicit throughout a new
version, then collect ten fresh matched sets with Sol/medium; test directed-public
messaging, duration, and memory separately. These choices remain provisional.
Only offline review and documentation were performed; no experiment was launched.

## 2026-10-24 — Neutral iteration report

Created the [iteration report](neutral-pilot-iteration-report-2026-10-24.md),
covering the nine-session design, message counts, key examples, costs, collection
provenance, limitations, and proposed follow-ups. Source hashes and aggregate
figures were rechecked. Coalition findings remain preliminary assistant judgments;
human labels are pending. No model calls or new experiment settings were applied.

## 2026-10-24 — Luna replication prepared; spending approval pending

The [verbatim checkpoint](luna-research-log-history-2026-10-24.md#2026-10-24--luna-replication-prepared-spending-approval-pending)
preserves model selection, prices, configs, tests, preparation failures and approvals.
The [approved plan](luna-replication-plan-2026-10-24.md) and ledgers retain every attempt.

## 2026-10-24 — Authorized Luna neutral pilot completed

The [verbatim completion entry](luna-research-log-history-2026-10-24.md#2026-10-24--authorized-luna-neutral-pilot-completed)
and [execution ledger](luna-neutral-pilot-2026-10-24.md) preserve approvals and usage.
Nine sessions/108 hands verified: 813 calls, 1,909,128 tokens, $0.456197200; no paid
failures. [Report and frozen archive](luna-neutral-iteration-report-2026-10-24.md).

## 2026-10-24 — Luna/Sol synthesis and next-iteration recommendation

The [verbatim historical entry](luna-research-log-history-2026-10-24.md#2026-10-24--lunasol-synthesis-and-next-iteration-recommendation)
and [synthesis](luna-findings-and-next-iteration-2026-10-24.md) preserve the comparison,
costs and unapproved next-iteration proposal. No new calls; Sol raw data unavailable.

## 2026-10-24 — Researcher delegates review step 1 to the assistant

Request: “do 1 for me as human assistant now.” Completed the substantive review;
the [verbatim checkpoint](luna-research-log-history-2026-10-24.md#2026-10-24--researcher-delegates-review-step-1-to-the-assistant)
and [report](luna-assistant-adjudication-2026-10-24.md) preserve judgments, provenance,
validation and the archive. Human/independent reviews remain separate.

## 2026-10-24 — Detailed neutral private-message review

The [verbatim checkpoint](luna-research-log-history-2026-10-24.md#2026-10-24--detailed-neutral-private-message-review)
and [report/audit packet](luna-private-message-review-2026-10-24.md) retain all 155
messages, coding, views, 36-hand review and validation; enactment stays uncertain.

## 2026-10-24 — Proposed next Luna cycle

Researcher requested a recommendation. The [proposal](luna-next-cycle-proposal-2026-10-24.md)
specifies calibration on existing evidence, a separately implemented 60-call
final-hand message-context screen, then nine unchanged neutral sessions on
proposed fresh seeds 400–402. Forecast ~$0.47–$0.49 using saved prices; proposed
stops sum to $0.95/9.1m tokens with post-response overshoot. Prices, fixtures,
new configs, seed inventory, preflight and spending approval remain pending.
No main-study freeze or ten-set expansion; a later duration study is separate.
This is a proposal, not execution or a new finding. **New calls/tokens/cost:
0 / 0 / $0**; recorded total stays $0.944253475. No runtime/config changes.

## 2026-10-24 — Cycle 2 preparation and authorization

The [verbatim preparation entry](luna-research-log-history-2026-10-24.md#2026-10-24--cycle-2-accepted-executable-preparation-and-publication)
preserves fixtures, pricing, tests, failures, source publication and the archive.
After the exact staged costs/limits were presented, the researcher replied
“yes,” approving the 60-decision diagnostic and nine new neutral sessions only
if it passes. Execution follows the [approved plan](luna-cycle2-plan-2026-10-24.md)
and [attempt/usage ledger](luna-cycle2-execution-2026-10-24.md). Runtime/source
is unchanged from published `7c568cc`; fresh directories, no retries/replacements.
This proceed decision does not supply independent human calibration or labels.

## Open decisions

- Human adjudication of neutral-pilot findings; main settings/sample size after review.
- Human control-review assignments, second-review availability, and usability outcome.
- Main session count, hand count, budget, and throughput based on the pilot.
- Final rubric decisions for ambiguous actual examples.
- Main failure policy and archive location for Git-ignored research artifacts.

Use the [entry template](research-log-entry-template.md) for future records.
