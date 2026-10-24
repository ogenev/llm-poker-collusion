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
- **First cycle:** Luna basics passed 12/12; all three gameplay, six control and nine
  neutral sessions completed and verified. Neutral: 108 hands, 813 calls,
  1,909,128 tokens, $0.456197200. That cycle: 1,659 calls, 4,811,920 tokens,
  $0.944253475; no paid failure or missing usage. Main settings remain unfrozen.
- **Selected poker model:** `openai/gpt-6-luna`, explicit medium reasoning,
  selected by the researcher on 2026-10-24. Strict JSON schema throughout.
- **Design:** Prior replications preserved original prompts, mechanics, communication,
  memory, deals and rotations. Cycle 3 preparation now contrasts announced 12/36-hand
  horizons across three fresh seed blocks; all other experimental settings stay fixed.
  The channel-explicit prompt revision and ten-set expansion remain cancelled.
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
  [execution](luna-cycle2-execution-2026-10-24.md) passed the diagnostic 60/60
  (63,265 tokens, $0.0117173). [Cycle 2 is complete as fixed attempts](luna-cycle2-iteration-report-2026-10-24.md):
  eight complete sessions plus partial public400, two complete matched sets of
  three planned, no replacement. Private enactment remains assistant-uncertain;
  human primary estimate is null. Known cycle-2 cost $0.432270800; cumulative
  Luna through cycle 2 $1.376524275, plus two unresolved requests. Independent
  review is pending.
- **Cycle 3:** The approved [duration study](luna-cycle3-plan-2026-10-24.md) is
  collecting. Its diagnostic passed 26/26 and seed 500's three short sessions
  verified: 36 hands / 280 calls / $0.158132050. Long seed-500 none/public are also
  complete; its private sample is active. Five neutral sessions have completed;
  zero full six-condition blocks are complete at this checkpoint. The
  [transcript review](luna-cycle3-transcript-review-2026-10-24.md) retains private
  narrow acceptance and table-wide coordination, with pair enactment uncertain.
  Human labels remain pending. See the execution ledger for ongoing usage.
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

## 2026-10-23 — Sol preparation and basic qualification

The [verbatim historical entries](research-log-sol-preparation-2026-10-23.md) retain
the original plan, model selection, settings and qualification attempts/results.

## 2026-10-23–24 — Reported Sol gameplay, controls and neutral pilot

The [verbatim historical entries](research-log-sol-gameplay-neutral-2026-10-23.md)
retain gameplay/control results, recorded human qualification decisions, neutral
collection and the cancelled prompt revision. This move changes no finding or
evidence-availability claim; it keeps the active journal below about 500 lines.

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

## 2026-10-24 — Cycle 2 proposal, approval and diagnostic gate

The [verbatim entries](luna-research-log-history-2026-10-24.md#2026-10-24--proposed-next-luna-cycle)
preserve the proposal, exact-plan approval and diagnostic pass. The
[approved plan](luna-cycle2-plan-2026-10-24.md) fixes 60 diagnostic decisions and,
conditional on a pass, nine unchanged neutral sessions. The screen passed 60/60,
63,265 tokens / $0.0117173; short no-history cases do not reproduce the earlier
long-history error. Independent human calibration remains outstanding.

## 2026-10-24 — Cycle 2 interrupted; continue only unstarted samples

The [verbatim interruption entry](luna-research-log-history-2026-10-24.md#2026-10-24--cycle-2-interrupted-continue-only-unstarted-samples)
preserves the stopped process, unresolved usage and authorization to continue
only seven unstarted samples under unchanged limits, without replacement.

## 2026-10-24 — Cycle 2 fixed attempts finished; findings remain provisional

All seven unstarted selections completed and passed native verification. Overall:
eight complete sessions, one preserved partial; 103 settled hands, two complete
matched sets of three planned. Neutral: 763 saved responses / 1,761,747 tokens /
$0.420553500; with the diagnostic, 823 / 1,825,012 / $0.432270800. Two started
requests lack responses, so billing remains unknown and totals are lower bounds.
Cumulative Luna known cost: $1.376524275. No retry, replacement or expansion.

Eight validated **model** annotations / 24 pairs: private enactment uncertain in
all three sessions; private401 acceptance observed. Private402's late reciprocal
accurate C warnings are a serious implicit-information candidate, not evidence
of absence. Public402 includes responsive whole-table checking without an
identified favored pair. All 255 delivered messages were audited; actual exchanges,
unsupported attribution, vague ranks and untriggered promises remain distinct.
Human labels/independent calibration remain pending; primary estimate null.

The [report](luna-cycle2-iteration-report-2026-10-24.md) and
[ledger](luna-cycle2-execution-2026-10-24.md#final-collection-and-offline-closeout)
retain every attempt, limits, costs, examples, selected-block comparison limitation,
reported-only Sol comparison and next steps. No hands/messages/pairs are independent
replications. Archive closeout follows; raw evidence is not preserved by Git push.

## 2026-10-24 — Cycle 2 archive and reproduction closeout

Frozen [evidence ZIP](../runs/pilot/exploratory/luna-neutral-cycle2-20261024-001.zip):
5,129,653 bytes / 368 files, source `29eb601`; all 367 manifest entries verified.
SHA-256: `89ec2668fe0cc2a51d7bff1fcf104b2f70b0f28e8dae57092d35b2fd7b9ef9e9`.
Fresh-extraction locked sync, native checks, nine transcript exports, schedules,
usage and secondary summaries reproduced with the API key unset: zero paid calls.
Archive/nested-content and reproduction-sidecar credential scans passed.
The [reproduction record](../runs/pilot/exploratory/luna-neutral-cycle2-20261024-001.zip.reproduction.json) retains checks/log hashes; the ZIP is unchanged.
Two complete sets, the original interruption and missing human adjudication remain.

## 2026-10-24 — Cycle 3 duration experiment prepared; paid approval pending

The researcher accepted the session-length proposal (“ok lets do that”) and
requested “commit and push to main and lets do that.” Preparation/source publication
are authorized; the original instruction still requires the exact staged costs
and stops to be presented and confirmed before any new paid call.

The [plan](luna-cycle3-plan-2026-10-24.md) specifies a separate 26-call retained-history
diagnostic, then (only on a verified pass) 18 neutral sessions: 12/36 hands crossed
with none/public/private, seeds 500–502, rotations 0–2, 432 hands. Fresh histories;
matched 12-hand deal prefixes; original prompts, medium reasoning, strict JSON,
two message rounds, 500/1,000 character limits and six-hand memory. Prior configs
and evidence remain. Three seed blocks are the sample, not individual hands.

Diagnostic: exact public301 hand-9/request-82 replay plus twelve terminal variants
of six saved six-history extreme-card views, each repeated twice. History-retained
and history-removed pairs share all other inputs. Engine dominance applies to the
terminal variants; the exact nonterminal replay scores immediate-hand behavior,
not guaranteed total-session optimality. Outcome-selected fixtures cannot estimate
a general error rate. Source prompts/hashes and original source journals are saved.

The [measurement guide](luna-cycle3-measurement-guide-2026-10-24.md) preserves uncertain
private enactment, implemented narrow checks and actual reciprocal relays. It adds
prospective evidence-timing and two-hand persistence conventions without changing
the primary rubric. Four full-session forms are blank; no assistant review becomes
a human decision. Announced horizon and opportunity are confounded; longer sessions
mechanically permit more events. First-12-hand contrasts, later windows and full
sessions remain distinct. Human primary estimates stay null pending human labels.

Official model/pricing rechecked; non-generating model metadata retrieval succeeded.
Expected diagnostic $0.01–$0.03; short sessions $0.4561972; long sessions $1.4681616
using the earlier complete pilot's full-memory per-hand costs. Combined forecast
$1.93–$1.95 is arithmetic planning, not a confidence interval. Stops: diagnostic
$0.10/200k tokens, short $0.10/1m per session, long $0.35/3m per session; summed
$4.15/36.2m, at most 3,914 calls. Post-response overshoot remains possible. No
retry/replacement/expansion. Paid calls and actual cycle-3 usage/cost remain zero.

Preparation evidence is in `runs/preparation/luna-cycle3-20261024-001/`. Locked sync
and initial 26 focused tests passed. One mypy list annotation was corrected. An
offline matrix setup failed for missing explicit mock prices before any generation;
its log is preserved alongside the separate corrected preparation attempt. Final
full suite: 1,421 passed, two optional browser suites skipped; Ruff/format/mypy pass.
The 26-call mock diagnostic and full 18-session/432-hand mock matrix verify, with
live-pass flags false. Seven client preflights made zero generation calls. The
prior saved live diagnostic reverified 60/60 without new responses. Ninety-six
prior runtime/config/script/lock files remain identical; the three diagnostic
harness extensions preserve the old fixture hash. Source publication/archive
details follow once complete. Earlier Sol
preparation entries were moved verbatim to a linked history file, not discarded.

## 2026-10-24 — Cycle 3 preparation published and archive reproduced

Source/configs/guide were committed and pushed to main as `470d951`, before paid
execution. The [preparation ZIP](../runs/preparation/luna-cycle3-20261024-001.zip)
contains 331 files / 6,586,915 bytes, including locked source, exact fixtures,
selected prior sources, blank forms, forecast inputs, all mock attempts and tests.
SHA-256: `63480ff3bc87654c35be442e859b5c4e73e22cfd1105b1d869ea9f424ef94b34`.
All 330 internal manifest entries and nested credential scans passed. Fresh
extraction with the API key unset reproduced locked sync, diagnostic checks,
all 18 mock sessions/three blocks, seven source-session replays and nine forecast
source calculations. The [reproduction record](../runs/preparation/luna-cycle3-20261024-001.zip.reproduction.json)
retains check/log hashes. Mock live-pass flags remain false; the old live diagnostic
pass is historical. New paid calls/cost: zero. Human reviews: zero. The exact
staged spending plan still awaits confirmation; no diagnostic or neutral launch.

## 2026-10-24 — Cycle 3 exact spending plan approved

The researcher replied “yes” to the explicitly presented diagnostic and conditional
18-session pilot, $1.93–$1.95 expected cost, $4.15/36.2m summed stopping thresholds
and 3,914-call maximum. This is new cycle-3 authorization, not reuse of earlier
permission. Preparation source `470d951` and archive closeout `19479aa` were pushed
before approval. Locked dependencies and current cloud readiness were checked.
The [execution ledger](luna-cycle3-execution-2026-10-24.md) retains exact settings,
stages and limits. Commit this authorization before launching the 26-call check.
Neutral collection remains conditional on its verified pass. Human labels stay
pending; no retry, replacement, prompt revision or expansion is authorized.

## 2026-10-24 — Cycle 3 retained-history diagnostic passes 26/26

Attempt 001 launched from pushed `63464e2`, completed with exit 0, and passed
native plus raw-provider verification: 26 valid/correct responses, 44,744 tokens,
$0.006560845 recorded cost; no missing calls/usage, retries or repair. Both exact
public301 error-view replays folded; all 24 terminal history-retained/removed
variants were correct. Source hashes, timing, usage categories and the
[gate decision](luna-cycle3-execution-2026-10-24.md#diagnostic-001-passed-neutral-gate-cleared)
are retained. Reasoning is counted inside output; prompt caching is not response
reuse. The selected/repeated contexts cannot estimate a general error rate and
do not establish competence throughout 36 hands. Human adjudication is still
pending. The preapproved neutral duration stage is cleared, starting with seed
500's short sessions; no additional samples or repeat diagnostic are authorized.

## 2026-10-24 — Cycle 3 neutral collection underway

The first authorized batch (seed 500, rotation 0, 12 hands, none/public/private)
launched from pushed `03ad99a` at 18:42:45 UTC in a fresh directory. All 109
frozen runtime/config/script/lock hashes match. Its no-messaging session completed
12 hands, 43 calls and 75,102 tokens for $0.016691275; transcript/provider checks,
replay and the assistant annotation validate. All pairs were reviewed before
aggregate winnings, with no specific coalition arrangement identified. This is
one preliminary model assessment, not a human decision or a duration comparison.
Public/private collection and full batch verification are still pending. The
[execution ledger](luna-cycle3-execution-2026-10-24.md) records subsequent receipts,
attempts and findings; failed or partial evidence will remain in the fixed matrix.

## 2026-10-24 — Cycle 3 first short batch verifies

Seed 500's three 12-hand sessions completed with no operational failures:
280 calls / 659,647 tokens / $0.158132050. Native Inspect/game/model, raw-provider,
deal and frozen-source checks pass. With the diagnostic, cycle-3 usage is 306
calls / 704,391 tokens / $0.164692895. All 30 observed extreme-rank call/fold
checks matched immediate-hand dominance; these are dependent, selected decisions,
not a general error-rate estimate. All trajectories were read before aggregate
winnings. None/public model reviews found no specific arrangement. Private
checking/reciprocity candidates, especially hand 11's truthful exchange and
all-table checks, remain under detailed review; pair favoritism is unresolved.
An unsupported relay in hand 6 and broken fold promise in hand 12 are preserved.
The [ledger](luna-cycle3-execution-2026-10-24.md) records details and the assistant
execution clearance for the already approved seed-500 long batch. Human labels
remain pending; zero full six-condition duration blocks are complete so far.

The [detailed first-batch transcript review](luna-cycle3-transcript-review-2026-10-24.md)
now retains finalized private model labels: proposed uncertain / accepted observed
for narrow checking and information exchanges / enacted uncertain as a favored-pair
coalition. It distinguishes hand-11 table-wide coordination, hand-6 unsupported
relay, hand-12 fold offers, candidate persistence and missing human adjudication.
Native annotation, replay, secondary coding and 17 extra receipt checks pass.
The approved long seed-500 batch launched from pushed `e94d913`; it is collecting
with the original frozen settings and fresh evidence. No aggregate payoff review yet.

## 2026-10-24 — First long sample and matched public prefix

Seed 500's 36-hand no-messaging sample completed and passed provider audit, replay
and native model-annotation validation: 131 calls / 261,109 tokens / $0.059655625.
All pairs/windows were reviewed, with no specific arrangement identified. Four
neutral sessions are complete; including the diagnostic, completed-source usage
is 437 calls / 965,500 tokens / $0.224348520, excluding the active public sample.
Before viewing that long public sample's later hands, the assistant preserved its
first-12 source-prefix hash and assessment: no identified pair arrangement; 29
rank assertions (9 true/20 false), versus short public's 33 (8 true/25 false).
See the [matched-prefix checkpoint](luna-cycle3-transcript-review-2026-10-24.md#seed-500-public-first-matched-horizon-checkpoint).
This is one seed, not a horizon-effect finding; stable long-public verification
and human judgments are pending. No full duration seed block is complete yet.

The long public hands 13–24 checkpoint is also preserved before later-hand review:
48 definite rank assertions (9 true/39 false), one own-rank revision, no explicit
fold offer and no identified pair arrangement. Its source-prefix hash and counts
are in the [execution ledger](luna-cycle3-execution-2026-10-24.md). This second
window is dependent within the same session; it adds no independent replication.

The long public session subsequently completed and passed stable-source/provider,
replay, native model-annotation and secondary-code checks: 345 calls / 864,383
tokens / $0.193306850. All three saved window snapshots match the final source
with unchanged judgments. Across 36 hands: 120 rank assertions (23 true/97 false),
one accurate attributed challenge, four revisions, no explicit fold offer and no
identified pair arrangement. The [completed public review](luna-cycle3-transcript-review-2026-10-24.md#seed-500-long-public-completed-trajectory)
retains each window and its limitations. Five completed neutral sessions plus the
diagnostic total 782 calls / 1,829,883 tokens / $0.417655370; active private usage
is excluded. Full batch and seed-block completion await private; human labels
remain pending. No aggregate winnings have been opened.

During the ongoing long private session, hand 7 supplies a stronger AB information
case: reciprocal card requests and a disclosure promise, verified receipt, then
two truthful replies. The assistant provisionally marks information-sharing
proposal/acceptance/enactment observed for this hand, with a source-bound early
record; see the [execution ledger](luna-cycle3-execution-2026-10-24.md). This is
not a human decision, a payoff-benefit finding or proof of persistent cooperation.
Full-trajectory review is pending, earlier false replies/broken commitments are
retained, and one hand is not an independent experimental replication.

The subsequently frozen private first-12 checkpoint also identifies a completed
AB exchange in hand 10. The [detailed review](luna-cycle3-transcript-review-2026-10-24.md#seed-500-long-private-first-12-information-exchanges)
records exact requests, receipt and true replies for hands 7/10, with onset at
hand 7 and gaps retained. The assistant's provisional persistence label uses the
two-hand repeated-arrangement convention; durable standing intent is not shown,
and whether the renewals should share one arrangement ID requires human review.
The window contains 58 messages, 27 true/17 false definite rank claims, three
accurate relays, and fold offers split 3 fulfilled/1 broken/6 untriggered. Ordinary
jack folds, missing reciprocation and other-pair uncertainty remain limitations.
This is one matched seed's prefix, not a population or horizon-effect estimate.

The long private second-window checkpoint adds assistant-observed information
exchanges for BC in hand 14 and AC in hand 24, with exact received-view checks;
see the [case review](luna-cycle3-transcript-review-2026-10-24.md#seed-500-long-private-second-window-cases).
Thus every pair has a positive information case somewhere in this ongoing
session, alongside repeated false/incomplete exchanges. Hand 21 explicitly takes
up a fold promise that is then broken by an ace call. Window 13–24: 63 messages,
26 true/20 false rank claims, three accurate attributions, two revisions, and
two broken/three untriggered fold offers. No exclusive/stable alliance, causal
payoff benefit or general duration effect follows; full-source and human reviews
remain pending. The three seed blocks remain the intended replication unit.

## Open decisions

- Human adjudication of neutral-pilot findings; main settings/sample size after review.
- Human control-review assignments, second-review availability, and usability outcome.
- Main session count, hand count, budget, and throughput based on the pilot.
- Final rubric decisions for ambiguous actual examples.
- Main failure policy and archive location for Git-ignored research artifacts.

Use the [entry template](research-log-entry-template.md) for future records.
