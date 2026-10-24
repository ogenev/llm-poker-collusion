# Luna cycle 3: proposed continuation after the failure hold

Date: 2026-10-24. **Prepared, not approved or started.** The original approved
plan says “pause subsequent batches on a failure” and “no replacement or automatic
resume/restart.” The [checkpoint report](luna-cycle3-checkpoint-report-2026-10-24.md)
preserves the HTTP-520 failure and available findings. This proposal continues only
the twelve still-unstarted cells; it cannot convert the failed seed-500 private
sample into a complete one. At most two of three planned seed blocks can finish.

## Exact stages, expected costs and stops

Every paid batch runs none/public/private in that order, with one connection,
original neutral prompts, original deals/rotations/memory/communication mechanics,
`openai/gpt-6-luna`, explicit medium, strict JSON schema, 4,096 maximum output
including reasoning, temperature omitted, response reuse off and retries zero.
No diagnostic rerun, failed-cell retry, additional seed or prompt revision.

| Stage | Seed / rotation / hands | Sessions | Expected additional API cost | Summed batch thresholds |
| --- | --- | ---: | ---: | --- |
| Offline hold/source/connectivity check | Existing evidence | 0 | $0 | Zero generation calls |
| Original batch 2 | 501 / 1 / 36 | 3 | $0.4894 | $1.05 / 9M tokens / 972 requests |
| Zero-call evidence/review gate | Batch 2 | 0 | $0 | Stop on failure |
| Original batch 3 | 501 / 1 / 12 | 3 | $0.1521 | $0.30 / 3M tokens / 324 requests |
| Zero-call evidence/review gate | Batch 3 | 0 | $0 | Stop on failure |
| Original batch 4 | 502 / 2 / 12 | 3 | $0.1521 | $0.30 / 3M tokens / 324 requests |
| Zero-call evidence/review gate | Batch 4 | 0 | $0 | Stop on failure |
| Original batch 5 | 502 / 2 / 36 | 3 | $0.4894 | $1.05 / 9M tokens / 972 requests |
| Verification/review/report/new archive | All available cells | 0 | $0 | Zero generation calls |

The rounded batch costs sum to $1.2830; using the original unrounded per-session
forecast gives approximately **$1.2829** for six short plus six long sessions.
This is an arithmetic forecast, not a confidence interval. The total additional
configured thresholds are **$2.70 / 24,000,000 tokens / at most 2,592 requests**
for 288 planned hands. Limits are per session, checked after responses, and may
overshoot; no separate global limiter or hard billing cap is claimed.

Each 12-hand session stops at **$0.10 or 1M tokens or 1,800 seconds**; each 36-hand
session at **$0.35 or 3M tokens or 5,400 seconds**. Every decision has a 90-second
timeout. Keep the original zero-retry failure policy and inspect each batch before
the next; a new failure pauses later batches again. No unused budget is spent on
replacements. Known spend already incurred remains $0.602306320 plus one unknown
cycle-3 failed request; the two older unknown requests remain separate.

Official compatibility/pricing was checked on 2026-10-24 and is preserved in the
[original plan](luna-cycle3-plan-2026-10-24.md#current-pricing-costs-and-explicit-stops):
per-million input $0.10, output $0.50, cache read $0.01, cache write $0.125.
A non-generating connectivity check may precede collection; it authorizes no
extra model-generation probe. Credentials must never enter commands or artifacts.

## Commands and fresh destinations

Run from the repository root only after the new researcher confirmation and
source-bound continuation approval receipt. The exact command arrays also remain
in `runs/pilot/exploratory/luna-duration-cycle3-20261024-001-evidence/execution-commands.json`.
The output root below already contains seed 500; **all four named child directories
are absent and must still be absent at launch**. Each has its own new attempt
receipts/console, without changing batch 1's false clearance or original launcher.

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle3-36hands.json --block-index 1 --model-cost-config configs/openai-gpt-6-luna-cycle3-pricing.json --output runs/pilot/exploratory/luna-duration-cycle3-20261024-001/seed-501-36hands
```

After batch-2 evidence review passes:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle3-12hands.json --block-index 1 --model-cost-config configs/openai-gpt-6-luna-cycle3-pricing.json --output runs/pilot/exploratory/luna-duration-cycle3-20261024-001/seed-501-12hands
```

After batch-3 evidence review passes:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle3-12hands.json --block-index 2 --model-cost-config configs/openai-gpt-6-luna-cycle3-pricing.json --output runs/pilot/exploratory/luna-duration-cycle3-20261024-001/seed-502-12hands
```

After batch-4 evidence review passes:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-pilot-neutral-gpt-6-luna-medium-strict-cycle3-36hands.json --block-index 2 --model-cost-config configs/openai-gpt-6-luna-cycle3-pricing.json --output runs/pilot/exploratory/luna-duration-cycle3-20261024-001/seed-502-36hands
```

Use the supervised launcher prepared in the evidence directory, which checks
approval hashes and writes redacted console/process receipts. The direct commands
above define the concrete paid work; do not bypass the approval or evidence gates.
All review/report code remains offline with the API credential unset. Review the
first-12 prefix before later hands, retain failures and contrary cases, and keep
human labels null until actual human annotations exist. Preserve the current
checkpoint archive and publish a separate archive after any continuation.
