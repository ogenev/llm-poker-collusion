# Luna cycle 3 continuation execution — 2026-10-25

This ledger continues the [approved remaining-cell plan](luna-cycle3-continuation-plan-2026-10-24.md)
and preserves the [October 24 checkpoint](luna-cycle3-checkpoint-report-2026-10-24.md).
The researcher explicitly replied **“yes I approve”** on October 25 to the exact
four-batch proposal. This is spending/proceed authorization, not human coalition
adjudication. Human annotations and the primary human estimate remain absent/null.

## Approval and zero-call preparation

`continuation-approval.json` binds the approved document, commands, duration plan,
frozen runtime manifest, prior failure clearance, checkpoint verification and
supervised launcher by SHA-256. The false template and original failed batch-1
clearance are unchanged. Only original batches 2–5 may start; seed-500 private
remains partial and cannot be retried or replaced. All four new output directories
were absent at preparation. The existing immutable checkpoint ZIP is preserved.

Current cloud observations report enforced HTTP policy and a ready configured API
credential. The normal SDK's non-generating `GET /v1/models/gpt-6-luna` succeeded
at 06:12 UTC. No credential value was printed or saved. All 109 runtime/config
hashes match; the existing locked environment and previously passing tests remain
applicable, with no runtime change or paid diagnostic rerun.

| Original batch | Seed / rotation / hands | Expected cost | Summed cost / token / request stops |
| --- | --- | ---: | --- |
| 2 | 501 / 1 / 36, none/public/private | $0.4894 | $1.05 / 9M / 972 |
| 3 | 501 / 1 / 12, none/public/private | $0.1521 | $0.30 / 3M / 324 |
| 4 | 502 / 2 / 12, none/public/private | $0.1521 | $0.30 / 3M / 324 |
| 5 | 502 / 2 / 36, none/public/private | $0.4894 | $1.05 / 9M / 972 |

Expected additional spend is about $1.2829; total configured thresholds are
$2.70 / 24M tokens / 2,592 maximum requests. Each short session stops at
$0.10/1M tokens/1,800s; each long at $0.35/3M/5,400s; every decision has 90s.
These are post-response thresholds with possible overshoot, not hard billing caps.
Original neutral prompts, deals, rotations, six-hand memory and communication
limits are frozen; poker model is Luna, explicit medium, strict JSON, output cap
4,096 including reasoning, no temperature override, zero retries/response reuse.

Inspect and verify each batch before starting the next. Another failure holds
later batches again. Review all fixed pairs and freeze first-12 assessments before
reading later hands; keep aggregate payoff tables closed until available reviews
are complete. Record receipt/memory links, contrary evidence and uncertain cases.
The three planned seed blocks are the replication units; at most two can now
complete, and additional hands/windows/pairs do not create replications.

## Batch 2 launch

Prepared to launch seed 501 / rotation 1 / 36 hands using the approved supervised
command and fresh `seed-501-36hands` directory. Actual launch/process/finish receipts
live under `runs/pilot/exploratory/luna-duration-cycle3-20261024-001-evidence/batch-2/`.
Results, costs and findings will be recorded as they become available.
