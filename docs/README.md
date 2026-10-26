# Documentation

Start with the [submitted paper](poker-collusion-report.pdf) and
[reviewer guide](reviewer-guide.md). The guide maps the paper's figures,
tables, and behavioral examples to supporting records and configurations.
The [repository README](../README.md) gives the findings and a runnable demo.

## Results and evidence

| Question | Read this |
| --- | --- |
| What did the complete review find? | [Final evidence audit, 26 October](reviewer-audit-2026-10-26.md) |
| How do messages connect to actions? | [Three worked examples with source references](evidence-examples.md) |
| How did Sol use public and private messages? | [Sol neutral pilot](neutral-pilot-iteration-report-2026-10-24.md) |
| How did Luna compare? | [Luna initial neutral pilot](luna-neutral-iteration-report-2026-10-24.md) |
| Were Luna's initial private disclosures truthful? | [Detailed private-message review](luna-private-message-review-2026-10-24.md) |
| Did the pattern recur with fresh deals? | [Luna fresh replication, cycle 2](luna-cycle2-iteration-report-2026-10-24.md) |
| What changed with announced session length? | [Final duration report, cycle 3](luna-cycle3-continuation-report-2026-10-25.md) |
| Which duration-study hands support or complicate the findings? | [Continuation transcript review](luna-cycle3-continuation-transcript-review-2026-10-25.md), [seed 502 long-private review](luna-cycle3-seed502-long-private-review-2026-10-25.md) |
| Did asking for honesty change replies? | [Honesty probe, cycle 4](luna-cycle4-iteration-report-2026-10-25.md) |
| What was collected prospectively? | [Fresh private sources, cycle 5](luna-cycle5-source-report-2026-10-25.md) |
| What happened under explicit coordination instructions? | [Sol controls](coordination-qualification-2026-10-23.md), [Luna controls](luna-coordination-iteration-report-2026-10-24.md) |

The dated reports retain the review status at the time they were written.
Use the final audit for subsequent findings and review provenance. Raw journals,
generated tables, and archives under `runs/` require separately supplied evidence;
see [availability and bundle names](reviewer-guide.md#evidence-availability).

## Methods

| Topic | Reference |
| --- | --- |
| Poker rules and disclosure | [Game protocol](game-protocol.md) |
| Repeated hands, delivery timing, memory, and failures | [Session protocol](session-protocol.md) |
| Prompts, model settings, and JSON responses | [Model interface](model-protocol.md), [historical prompt review](prompt-review-2026-10-24.md) |
| Proposed, accepted, and enacted arrangements | [Coalition rubric](collusion-rubric.md) |
| Review records, citations, and revisions | [Annotation format](annotation-format.md) |
| Session-level summaries and payoffs | [Analysis protocol](analysis-protocol.md) |
| Matching, exclusions, and uncertainty | [Comparison protocol](comparison-protocol.md) |
| Qualification and separate controls | [Basic qualification checklist](qualification-checklist.md), [control review guide](coordination-review-guide-2026-10-23.md) |
| Fresh replication coding | [Cycle 2 coding guide](luna-cycle2-coding-guide-2026-10-24.md) |
| Duration-study measurement | [Cycle 3 measurement guide](luna-cycle3-measurement-guide-2026-10-24.md) |

The analysis tools support workflows broader than the submitted study. Their
capabilities do not imply that a confirmatory analysis or independent human
annotation study was completed. For methods actually used, follow §3 of the
paper and its [evidence map](reviewer-guide.md#paper-to-evidence-map).

## Reproduction and review tools

- [Offline review guide](offline-review.md): inspect the demo, verify a matched
  run, and open a real source session.
- [Complete workflow](workflow-walkthrough.md): scripted gameplay through
  annotations, analysis, and an HTML comparison report.
- [Review form](review-form.md): inspect evidence and save or revise an assessment.
- [Report viewer](report-viewer.md): read generated comparisons and uncertainty.
- [Human usability checklist](usability-check.md): evaluate the review workflow.

## Technical reference

- [Framework reference](framework-reference.md): OpenSpiel integration, Python
  examples, and dated implementation checks.
- [Recording protocol](recording-protocol.md): journal contents, integrity,
  replay, and incomplete records.
- [Inspect integration](inspect-protocol.md): execution, model-call evidence,
  limits, and verification.
- [Live smoke record](live-smoke.md): pre-sprint compatibility checks and their
  limitations. Its live commands make provider calls.

## Historical plans and execution records

These records explain what was planned, approved, attempted, changed, or stopped.
They preserve failures and contemporaneous interpretations. Proposed next steps
are not completed experiments. The channel-explicit prompt revision and ten-set
expansion were canceled; the cycle 5 follow-up intervention was not run.

| Stage | Plans and execution |
| --- | --- |
| Original design and preparation | [Research overview](../llm-poker-collusion-research-project.md), [development roadmap](../TODO.md), [scientific runbook](scientific-runbook.md), [pilot preparation](pilot-preparation.md) |
| Sol pilot | [Attempt ledger](neutral-pilot-2026-10-23.md) |
| Luna initial iteration | [Replication plan](luna-replication-plan-2026-10-24.md), [qualification](luna-qualification-2026-10-24.md), [control execution](luna-coordination-2026-10-24.md), [neutral ledger](luna-neutral-pilot-2026-10-24.md), [assistant adjudication](luna-assistant-adjudication-2026-10-24.md) |
| Luna follow-up choices | [Findings and next iteration](luna-findings-and-next-iteration-2026-10-24.md), [next-cycle proposal](luna-next-cycle-proposal-2026-10-24.md) |
| Fresh replication, cycle 2 | [Plan](luna-cycle2-plan-2026-10-24.md), [execution](luna-cycle2-execution-2026-10-24.md) |
| Duration study, cycle 3 | [Initial plan](luna-cycle3-plan-2026-10-24.md), [initial execution](luna-cycle3-execution-2026-10-24.md), [checkpoint report](luna-cycle3-checkpoint-report-2026-10-24.md), [initial transcript review](luna-cycle3-transcript-review-2026-10-24.md), [continuation plan](luna-cycle3-continuation-plan-2026-10-24.md), [continuation execution](luna-cycle3-continuation-execution-2026-10-25.md) |
| Honesty probe, cycle 4 | [Plan](luna-cycle4-honesty-probe-plan-2026-10-25.md), [execution](luna-cycle4-execution-2026-10-25.md) |
| Prospective sources, cycle 5 | [Plan](luna-cycle5-heldout-source-plan-2026-10-25.md), [execution](luna-cycle5-execution-2026-10-25.md) |

## Research chronology

The [research log](research-log.md) is the central timeline. Older entries are
also preserved in these supporting notebooks:

- Sol: [preparation](research-log-sol-preparation-2026-10-23.md),
  [gameplay and neutral pilot](research-log-sol-gameplay-neutral-2026-10-23.md),
  [qualification history](sol-research-log-history-2026-10-24.md), and
  [original model recommendation](model-recommendation-history-2026-10-23.md).
- Luna: [initial history](luna-research-log-history-2026-10-24.md),
  [duration-study history](luna-cycle3-research-log-history-2026-10-24.md), and
  [duration continuation](research-log-cycle3-continuation-2026-10-25.md).
- [Log-entry template](research-log-entry-template.md) for future work.
