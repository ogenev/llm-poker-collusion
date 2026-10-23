# Neutral exploratory pilot — 2026-10-23

Part of the [research log](research-log.md). This is exploratory pilot evidence,
separate from instructed controls and from any later frozen main study.

## Human assessment and authorization

The researcher stated: "I reviewed the examples: coordination looks adequate in
both public and private" and explicitly requested the neutral pilot with
GPT-6.1 Sol and medium reasoning. Recorded at 16:52:07 Europe/Madrid.
The [human assessment](../runs/pilot/qualification/gpt-6.1-sol-medium-strict-public-token1m-20261023-evidence/human-coordination-assessment.json)
preserves the full message and binds the six selected control identities.

The reported scope is review of examples. Complete human transcript/all-pair
annotations and independent second-human checks have not been supplied. The
researcher's explicit authorization advances exploratory collection with those
limitations recorded; it does not fabricate formal annotation coverage or a
second review. Earlier machine-generated artifacts retain their pre-review state.

## Fixed pilot plan before collection

- **Status:** Attempt 001 failed before completing any hand because the API
  organization had reached its enforced spend limit. Collection awaits an account
  limit change; no automatic repeat is running.
- **Question:** Does communication visibility change observable pair coordination
  when players receive only an individual-winnings objective? Absence of
  spontaneous coordination is a valid pilot result, not a failed qualification.
- **Config:** [Neutral Sol medium, strict format](../configs/inspect-pilot-neutral-gpt-6.1-sol-medium-strict.json).
- **Workload:** Seeds 300/301/302, each with none/public/private conditions; nine
  sessions, 12 hands each, 108 hands total. Deals and seat rotations match within
  each seed; every session starts with fresh histories. These seeds are disjoint
  from gameplay seeds 100–102 and coordination-control seeds 200–202.
- **Model:** `openai/gpt-6.1-sol`, explicit `reasoning_effort: medium`, strict JSON
  schema, output cap 4,096; temperature omitted, response reuse disabled, zero retries.
- **Objective:** The existing neutral instruction maximizes individual winnings;
  no assigned partner or instruction to seek coordination. No control messages,
  reviews, or research conclusions enter player inputs.
- **Communication:** Two rounds before betting; 500 characters/message and 1,000
  per player per hand; six completed hands of permitted memory. No communication
  opportunities in the none condition.
- **Execution:** One session/connection at a time. All conditions have identical
  1,000,000-token and $2/session stopping thresholds, a 90-second decision deadline,
  and a 1,800-second session deadline. Limits are checked after responses and can
  overshoot. This avoids the earlier public token bottleneck without different
  stopping thresholds across neutral conditions.
- **Failure policy:** Attempt all nine fixed samples once. Retain every failure;
  do not repair responses, selectively retry based on behavior, or change runtime
  source/settings mid-run. Any necessary new attempt requires a documented decision.
- **Run:** `runs/pilot/exploratory/neutral-gpt-6.1-sol-medium-strict-20261023-001/`.
- **Evidence:** `runs/pilot/exploratory/gpt-6.1-sol-medium-strict-neutral-20261023-evidence/`.

## Cost estimate saved before collection

| Condition | Three-session empirical estimate | Basis |
| --- | ---: | --- |
| None | $0.510151 | Today's three medium-reasoning gameplay sessions |
| Public | $4.128417 | Three completed strict-format public controls |
| Private | $3.325254 | Three completed strict-format private controls |
| **Expected pilot total** | **$7.963822** | Same session/hand counts; new behavior may differ |

Communicated estimate: **about $8**, with **$6–$10** as a planning range, not a
statistical interval. Neutral messages may be shorter, fewer, or longer than
control messages; the none reference used text format while this pilot uses
strict schemas. Failed replacements are not priced into the forecast.
The nine $2 stopping thresholds total **$18**; this is neither the forecast nor
a hard billing cap. No extra model calls were made to estimate cost.

The [saved estimate](../runs/pilot/exploratory/gpt-6.1-sol-medium-strict-neutral-20261023-evidence/cost-estimate.json)
includes source hashes and scope. The existing [Sol pricing file](../configs/openai-gpt-6.1-sol-pricing.json)
was checked earlier today; usage will be valued at those same recorded rates.
Prior qualification/control costs are separate from this new pilot.

## Preflight and provenance

The first preflight did not load credentials and failed before any generation
call. Its empty output and failure record are preserved. Repeating with the
existing project environment passed: `client_initialized: true`, `api_calls: 0`.
See `preflight-attempts.json` and `preflight-env.json` in the evidence directory.
Config hash: `1a8abd0602ac1504f36ca333029c4d9f3483730f4ff8f6f72be32a095a3a2d93`.
The plan permits at most 972 decisions across all nine sessions.

A 118-file source/config/document snapshot and SHA-256 manifest were saved before
collection. All 89 runtime/script/test/lock files checked against the completed
strict controls are unchanged, so the prior 1,344 passing tests, lint, formatting,
and strict mypy validation still apply. Only configuration and research records
changed. Base commit: `2b9f9db14945c0736568d8d3c71a0878599269c7`; uncommitted source
bytes are preserved in the archive. Credentials are excluded from that archive.

## Attempt 001: organization spend limit

Launched at approximately 16:54:15 Europe/Madrid; run ID
`f7bb49e2e1064113bfb306e075ac6871`. The fixed batch attempted all nine sessions,
and all failed in their first hand. None completed a hand or delivered a
communication round. All 21 initial decision requests received HTTP 429 with
code **`organization_spend_limit_exceeded`**, type **`insufficient_quota`**.
The provider explicitly states that the organization's configured enforced
spend limit has been reached. The separate $2/session experiment threshold did
not cause these failures. `max_retries: 0` remained configured.

The runner and offline verifier both exited 2. Saved replay/artifact checks
describe failed sessions and unusable calls; raw provider rejection evidence is
preserved in [account-limit-failure.json](../runs/pilot/exploratory/gpt-6.1-sol-medium-strict-neutral-20261023-evidence/account-limit-failure.json).
The evidence directory also contains `verification.json`, `summary.json`,
`provider-audit.json`, `review-data.json`, and blank source-bound forms. Failed
empty trajectories are execution evidence, not examples of absent coordination.

No usage or cost values were supplied for these rejected requests. The saved
metered sum is $0 with `usage_complete: false` and `cost_complete: false`; that
is not proof of a zero bill. The prospective estimate for completing the actual
pilot remains about $8, with the $6–$10 planning range and $18 sum of thresholds.

The required external action is to increase the enforced organization spending
limit at the [settings URL returned by the API](https://platform.openai.com/settings/organization/limits).
No organization setting was changed, and no repeated paid probe or replacement
run was started. After the limit is updated, use a fresh attempt directory and
retain this entire failed attempt; the fixed neutral settings remain prepared.

## Review and interpretation plan

Verify all saved trajectories, model settings, raw provider payloads, permitted
observations, usage, and failures. Generate blank human review forms and separate
assistant evidence notes; review all sessions and all three pairs per session.
Preserve offers, acceptance timing, truthful/false disclosures, actual betting,
contrary evidence, and ordinary-play alternatives. No human labels are inferred.

Only three matched blocks exist. Hands and pairs are not independent replication;
whole-session winnings cannot establish a causal benefit of coordination. Assess
cost, runtime, context growth, and review burden to choose main-study settings.
Record negative/ambiguous findings. Formal comparison reports need valid human
annotations; the main protocol and sample size remain unfrozen.
