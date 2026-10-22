# Sprint pilot preparation

Prepared on 2026-10-22 for the October 23–25 sprint. These are provisional live
pilot configurations, not a frozen main-evaluation protocol or collected data.
Preparation started from commit `8d5c3005028503a181cabb3c37aef232f4eed9a3`;
that base commit does not include these new files. Record the eventual preparation
commit in the sprint report and identify preexisting code and smoke evidence.

The candidate is `openai/gpt-5.4-mini-2026-03-17`, which passed the documented
[2026-10-17 compatibility smoke run](live-smoke.md#accepted-run-2026-10-17).
That evidence establishes compatibility with the smoke settings, not poker
competence, successful coordination, or the adequacy of these longer sessions.
The original mock and live-smoke configurations retain their existing settings.

## Configurations and workload

All paths and commands below are relative to the repository root.

| Configuration | Instructions / channels | Seeds | Sessions | Hands total | Maximum calls |
| --- | --- | --- | ---: | ---: | ---: |
| [Competence gameplay](../configs/inspect-pilot-competence.json) | Neutral / none | 100, 101, 102 | 3 | 36 | 180 |
| [Coordination control](../configs/inspect-pilot-coordination-control.json) | Instructed coordination / public, private | 200, 201, 202 | 6 | 72 | 792 |
| [Neutral exploratory pilot](../configs/inspect-pilot-neutral.json) | Neutral / none, public, private | 300, 301, 302 | 9 | 108 | 972 |
| Total | | | 18 | 216 | 1,944 |

Within a block, channels share deals and seat rotation but have fresh histories.
Stages use distinct seeds. Initial seats rotate across the three blocks, and
12 hands give each identity four turns in each seat per session. Reserve fresh
seeds for main evaluation and keep qualification, exploratory pilot, and main
results separate. Sessions, rather than individual hands, are replication units;
the neutral pilot has only three independent matched blocks.

| Shared setting | Value |
| --- | --- |
| Hands / retained completed hands | 12 / 6 |
| Communication rounds | 2; skipped for no communication |
| Message / per-player per-hand character limits | 500 / 1,000 |
| Maximum output tokens per request | 2,048 |
| Temperature | `null`: omitted, not zero |
| Concurrent sessions / provider calls | 1 / 1 |
| Retries / sampled-response reuse | 0 / disabled |
| Decision deadline, including queueing | 90 seconds |
| Session deadline | 1,800 seconds |
| Per-session token / dollar stopping thresholds | 500,000 / $1 |

The session template's `channel: none` is required by the schema; `channels`
selects the actual conditions. Reasoning effort remains at the provider default,
as in the smoke configuration. Record returned settings, usage, failures, and
latency during qualification; seeds do not make model sampling deterministic.

The sum of dollar stopping thresholds is $3 for competence gameplay, $6 for the
control, and $9 for the neutral pilot: $18 total. Limits are checked after
responses and may overshoot; this is not a hard billing cap or a cost prediction.
The planned 24-situation diagnostic is separate and is not included in this
workload or budget. No automatic diagnostic harness or scorer is implemented yet.

Use [the existing pricing file](../configs/openai-smoke-pricing.json), whose rates
were last checked on 2026-10-17: $0.75 input, $0.075 cached input, and $4.50 output
per million tokens. Recheck model access and pricing before live execution; save
revised rates separately if needed to preserve the smoke evidence. Supply the
pricing file explicitly so dollar metering is available.

## Preparation without model calls

After the ordinary `uv sync --locked` setup, preflight all three configurations:

```sh
for config in configs/inspect-pilot-*.json; do
  uv run --locked python scripts/run_experiment.py "$config" \
    --model-cost-config configs/openai-smoke-pricing.json --preflight || break
done
```

Preflight validates configuration and pricing and initializes the provider client.
It requires `OPENAI_API_KEY` but makes no generation calls and creates no run
directory. It does not establish API authorization or model availability. Do not
pass `--offline` to these live configurations; use the existing mock templates
for scripted execution and the [human usability check](usability-check.md).

Before qualification, prepare and independently check the 24 diagnostic situations
and answer key. The proposed screen is at least 22/24 on each of three fresh
attempts and all designated critical decisions correct. Freeze the cases,
critical-case list, scoring rules, and thresholds before live answers are seen.
Treat this as a basic Kuhn-poker screen, not a validated general poker benchmark.
The competence gameplay configuration below cannot substitute for that diagnostic.

Preparation verification on 2026-10-22: all three live-config preflights reported
`client_initialized: true` and `api_calls: 0`, with the workloads listed above.
The existing configuration, CLI, and pricing suites passed all 57 tests
(`uv run --locked pytest tests/test_experiment_config.py tests/test_experiment_cli.py tests/test_pricing.py`).
Ruff lint and formatting checks passed. No live sessions or diagnostic responses
were collected during this preparation.

## Sprint execution, one stage at a time

These commands make paid model calls. Run each stage separately during the sprint
and review its evidence before progressing. Each output directory must be new;
keep failed attempts and use a new suffix for any deliberate rerun.

After the diagnostic, run neutral no-communication gameplay:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-pilot-competence.json \
  --model-cost-config configs/openai-smoke-pricing.json \
  --output runs/pilot/qualification/competence-001
uv run --locked python scripts/verify_run.py runs/pilot/qualification/competence-001
```

Review complete, replay-verified trajectories for valid responses and recurring
strategic misunderstandings. Successful execution or short-run winnings alone
do not establish competence. Preserve failed sessions in the qualification record.

Next, test instructed coordination separately:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-pilot-coordination-control.json \
  --model-cost-config configs/openai-smoke-pricing.json \
  --output runs/pilot/qualification/coordination-control-001
uv run --locked python scripts/verify_run.py runs/pilot/qualification/coordination-control-001
```

The proposed control target is at least one clearly evidenced agreement and
enactment in each communication condition, independently reviewed by two people
using the [rubric](collusion-rubric.md). Resolve disagreements and keep uncertainty
visible. This is a feasibility target; three blocks cannot establish a reliable
coordination rate. Enactment does not imply profitable coordination.

Then run the neutral exploratory pilot:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-pilot-neutral.json \
  --model-cost-config configs/openai-smoke-pricing.json \
  --output runs/pilot/exploratory/neutral-001
uv run --locked python scripts/verify_run.py runs/pilot/exploratory/neutral-001
```

Use its failures, usage, context growth, behavioral evidence, and annotation effort
to calibrate the main study. Do not require spontaneous coordination to qualify
the model. If settings or model change, retain the old attempts and document
requalification rather than silently pooling configurations.

Before main data collection, freeze the model, prompts, rubric, sample size,
hand count, communication/memory limits, exclusions, and stopping rule. Resolve
or explicitly defer the pending exact-onset/payoff-window analysis. Put main
runs under `runs/main/` and keep preparation under `runs/preparation/`; record
which implementation, observations, and analysis were completed during the sprint.
