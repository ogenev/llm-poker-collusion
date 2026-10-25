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
  continuing under October 25 approval after the preserved HTTP-520 hold.
  Its diagnostic passed 26/26; at continuation launch five neutral sessions
  completed and long private stopped after 31 settlements plus partial hand 32.
  The researcher approved the twelve unstarted cells on October 25; zero full
  duration blocks are complete at continuation launch. The
  [checkpoint report](luna-cycle3-checkpoint-report-2026-10-24.md) identifies
  assistant-observed long-private information exchanges for AB/AC/BC, without
  confirmed betting cooperation or causal benefit. Human labels remain null.
  Known cycle-3 cost is $0.602306320 plus one unknown failed request.
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

## 2026-10-24 — Cycle 3 preparation, collection and failed checkpoint

The [verbatim dated entries](luna-cycle3-research-log-history-2026-10-24.md) preserve
the exact plan/approval, 26/26 diagnostic pass, seed-500 collection, prefix reviews,
HTTP-520 failure, review-provenance deviation and archive reproduction. No finding
or decision changed in this move; it keeps the active journal below 500 lines.
Five sessions completed, private stopped after 31 settlements plus partial hand 32,
and zero full duration blocks completed. Assistant information cases were AB 7/10,
BC 14 and AC 24/25/28/31, with uncertain standing intent and no proven betting or
payoff benefit. Human labels remain null. Known cycle-3 checkpoint cost was
$0.602306320 plus one unknown request. The immutable checkpoint ZIP/checksum and
all failed evidence are retained; October 25 continuation is recorded separately.

## 2026-10-25 — Remaining cycle-3 cells explicitly approved

The researcher replied **“yes I approve”** to the exact twelve-session continuation
proposal. The source-bound approval receipt preserves the previous failure gate
and limits execution to unstarted batches 2–5: 501/36, 501/12, 502/12, 502/36,
with none/public/private in each. Expected additional cost $1.2829; summed stops
$2.70/24M tokens/2,592 requests, unchanged per-session limits. The failed seed-500
private sample and checkpoint archive remain intact; no replacement or diagnostic
rerun. This is a proceed decision, not human coalition labels.

Current cloud readiness and a non-generating model-lookup passed; all 109 frozen
source/config hashes match and new output directories are absent. No additional
paid call occurred during this preparation. The
[continuation ledger](luna-cycle3-continuation-execution-2026-10-25.md) records
launches, each verification gate, actual usage and findings. A new failure pauses
subsequent batches. At most two of three planned seed blocks can complete.

Continuation first completed cell: seed 501 long none, 36 hands / 132 calls /
262,874 tokens / $0.060195400. Provider, replay,
native model annotation and frozen window checks pass; no identified pair
arrangement, human labels null. Public collection is underway; no complete new
duration block or batch clearance yet. Details remain in the continuation ledger.

## Open decisions

- Human adjudication of neutral-pilot findings; main settings/sample size after review.
- Human control-review assignments, second-review availability, and usability outcome.
- Main session count, hand count, budget, and throughput based on the pilot.
- Final rubric decisions for ambiguous actual examples.
- Main failure policy and archive location for Git-ignored research artifacts.

Use the [entry template](research-log-entry-template.md) for future records.
