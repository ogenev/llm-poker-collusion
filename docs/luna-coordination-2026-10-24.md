# Luna coordination controls — 24 October 2026

Part of the [research log](research-log.md) and [approved Luna plan](luna-replication-plan-2026-10-24.md).
These are instructed controls, separate from spontaneous neutral coalition evidence.

## User amendment of the gameplay review gate

After receiving the gameplay packet, the researcher instructed:

> do assistant verification of the gameplay and process with coordination control if everything is ok

This authorizes proceeding on assistant gameplay verification instead of waiting
for the previously requested human gameplay assessment. It is a procedural
authorization, not a human judgment that the transcripts are adequate. The
original pause record and qualification archive are preserved. No independent
human gameplay assessment is claimed. The human coordination gate before the
neutral pilot remains unchanged.

The assistant reran the repository's full gameplay evidence verifier, rechecked
all saved provider-audit hashes, and confirmed unchanged runtime, script,
configuration and lockfile bytes. All 36 hands and 133 decisions still pass.
All nine ace-facing-bet actions called and all 20 jack-facing-bet actions folded;
no elementary error flags were found. The full-session review and examples in the
[qualification record](luna-qualification-2026-10-24.md) support an assistant
assessment of **adequate for exploratory coordination controls**. Bluffs,
middling-card calls and king checks are not automatically errors; optimality and
exploitability remain unmeasured. This review made no paid calls.

Evidence: `runs/pilot/qualification/luna-coordination-20261024-001-evidence/`,
including `gate-amendment.json`, `assistant-gameplay-assessment.json`, and the
fresh `gameplay-reverification.json`. Human gameplay assessment remains null.

## Fixed control plan and existing authorization

1. Three public sessions, seeds 200/201/202, then verify the run.
2. Three private sessions, the same seeds/deals/rotations, then verify the run.
3. Prepare all six transcripts, blank human forms and assistant candidate notes;
   pause for the human coordination assessment before any neutral session.

Each session has 12 hands, two pre-betting message rounds, 500 characters per
message, 1,000 per player per hand, and six retained hands. Use the original
instructed-control objective, with individual rewards. Model is
`openai/gpt-6-luna`, explicit medium, strict JSON schema, 4,096 output tokens,
omitted temperature, no response reuse, no fallback, and zero retries.
One session and one provider connection at a time. Original neutral prompts
remain unchanged and are not used as instructed-control objectives.

| Stage | Config suffix after `inspect-pilot-coordination-control-` | Expected USD from reported Sol usage | Stop per session | Token stop per session |
| --- | --- | ---: | ---: | ---: |
| Public, three sessions | `gpt-6-luna-medium-strict-public.json` | 0.20642085 | 0.10 | 1,000,000 |
| Private, three sessions | `gpt-6-luna-medium-strict-private.json` | 0.16626270 | 0.10 | 500,000 |

Expected combined cost at the reported Sol usage is $0.37268355. Luna's gameplay
used more reasoning than that baseline, so this conditional projection can
underestimate actual control cost. The approved limits are unchanged: summed
dollar thresholds $0.60 and token thresholds 4.5m; 90-second decision and
1,800-second session deadlines. Limits are checked after responses and can
overshoot; they are not hard billing caps. No unapproved retry, replacement,
limit increase, or sample expansion is included.

Use the existing `configs/openai-gpt-6-luna-pricing.json`: $0.10 input, $0.50
output (including reasoning), $0.01 cache read, and $0.125 cache write per million
tokens. Stage attempts use fresh directories:

- `runs/pilot/qualification/luna-control-public-20261024-001/`
- `runs/pilot/qualification/luna-control-private-20261024-001/`

If a run is incomplete, fails verification, or has unreliable usage/settings,
stop before the next run and investigate. Retain every fixed attempted session
and all partial/failed evidence. No selective response repair or replacement.

## Execution ledger

Preparation is complete; public-control attempt 001 is next. Cloud policy and
credential readiness report enforced/ready with current observations. Source
and config hashes, commands, timestamps, actual usage, failures and verification
will be saved with each attempt. Controls are not yet qualified; no neutral
pilot has started.
