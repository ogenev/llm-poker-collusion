# Historical Sol preparation entries

Moved verbatim from the research log on 2026-10-24 to keep the active notebook manageable.
These remain reported historical records, not newly verified Sol evidence.

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
