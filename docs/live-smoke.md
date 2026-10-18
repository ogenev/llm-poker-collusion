# Increment 3: live compatibility

The bounded OpenAI compatibility run passed on 2026-10-17, completing Phase 1
milestone 6. All three sessions completed, saved-run verification passed, and all
64 raw provider request/response pairs were reviewed. See the recorded result
below. This qualifies the tested model and settings for compatibility; poker
competence and coordination still require the milestone 7 pilot. Recovery,
interventions, and multiple-model research remain Phase 2.

## Accepted run: 2026-10-17

The unchanged smoke configuration ran against `gpt-5.4-mini-2026-03-17` from source
commit `1304380`. Run ID: `eb58eb45058148d6b228e71238e9b858`.
Artifacts are retained locally under
`runs/preparation/live-smoke-20261017-001/` (ignored by Git), including the Inspect
`.eval` log, run manifest, both journals per session, `console.log`,
`verification.json`, and `provider-review.json`.

| Channel | Completed hands | Calls / raw payload pairs | Total tokens | Metered cost (USD) |
| --- | ---: | ---: | ---: | ---: |
| None | 3 | 9 / 9 | 7,242 | $0.005859 |
| Public | 3 | 27 / 27 | 35,518 | $0.030051 |
| Private | 3 | 28 / 28 | 30,941 | $0.02681325 |
| Total | 9 | 64 / 64 | 73,701 | $0.06272325 |

The verifier returned `passed: true` with no session issues: matched saved deals,
legal decisions, exact replay, permitted player inputs, artifact links, settings,
and usage all passed. Raw requests contained exactly the expected developer
prompt and player-view JSON, the pinned model, a 2,048-token output cap, and no
tools or additional conversation state. All raw responses matched the recorded
outputs and model identity, with normal stop reasons and reconciled usage/cost.
There were no retries, response-cache hits, refusals, truncations, or failed
sessions. Usage was 71,715 input and 1,986 output tokens, with zero cached-input
or reasoning tokens. Pricing was rechecked against the model page on 2026-10-17;
metered cost is an estimate rather than a billing receipt.

The live run took about one minute. Saved-run verification needed the environment's
local socket support for Inspect's asynchronous file reads; it made no model
calls. This is preparation evidence, separate from future pilot/evaluation data.

## Configuration

`configs/inspect-live-smoke.json` prepares the candidate
`openai/gpt-5.4-mini-2026-03-17`, using neutral instructions in three matched
none/public/private sessions. The pinned identifier is a compatibility candidate;
the final study model still depends on the competence and control pilot.

Each session has three hands, two communication rounds, two retained hands,
500 characters per message, and a 1,000-character hand budget. Execution uses
one concurrent session and one provider request at a time, with zero Inspect,
OpenAI SDK, or sample retries. The same session engine and strict response parser
are used for the live and offline paths.

| Limit | Value |
| --- | --- |
| Maximum decision calls across all three sessions | 81 |
| Output-token cap per request | 2,048 |
| Decision deadline, including connection queueing | 90 seconds |
| Session deadline | 600 seconds |
| Token stopping threshold per session | 100,000 |
| Dollar stopping threshold per session | $0.10 |
| Sum of dollar thresholds | $0.30 |

The output cap leaves room for reasoning tokens if the provider uses them.
Temperature and reasoning effort are not explicitly requested; inspect the
actual returned usage and provider defaults in the live check. A truncated
response fails even if its text looks like valid JSON.

The token threshold allows for the rules and growing player history sent on every
request. The offline HTTP test estimates tokens from the actual English/JSON
payload at three UTF-8 bytes per token plus chat framing, and completes all three
sessions with the configured token and dollar thresholds. This estimate is
synthetic, not a tokenizer measurement or a guarantee for every live trajectory;
long messages or reasoning can still exhaust a limit.

Inspect checks usage after a response arrives, so thresholds may overshoot. The
$0.30 sum is neither a prepaid allowance nor a hard billing cap. Queue time and
provider errors may prevent completion. Keep every attempt and use a new output
directory when deliberately rerunning; no automatic reruns occur.

## Pricing and credentials

The OpenAI SDK is a locked runtime dependency. Run `uv sync --locked` after
updating the checkout. `OPENAI_API_KEY` must be supplied through the shell or
managed environment's secret settings; see `.env.example` for the variable name.
The CLI does not print the credential. A ChatGPT/Codex subscription does not
replace API billing. The managed environment must permit HTTPS to
`api.openai.com`; retain its configured proxy and CA trust.

Inspect's bundled model metadata does not supply these prices. Pass
`configs/openai-smoke-pricing.json` explicitly using `--model-cost-config`.
It uses Inspect's JSON pricing format in dollars per million tokens. The
[OpenAI model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
was checked on 2026-10-17: input $0.75, cached input $0.075, output $4.50.
The required cache-write field uses the ordinary input rate; this integration
does not request a separate cache-write product. These rates cover standard
processing, without regional or other service-tier adjustments. Recheck pricing
and model availability before another live run.

The pricing loader rejects a mismatched model, missing/extra rates, negative or
nonfinite values, and implicit conversions. The effective prices and workload
plan are saved in `run.jsonl`, alongside the experiment configuration and source/
dependency provenance. Prices are estimates for metering, not a billing receipt.

## Preflight without API calls

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-live-smoke.json \
  --model-cost-config configs/openai-smoke-pricing.json --preflight
```

Preflight validates configuration, loads pricing, and initializes the provider
client. It prints the planned workload and limits without generating a response
or creating a run directory. Missing credentials produce a nonzero exit and a
setup diagnostic. Successful initialization does not prove that the key is valid,
the network permits the endpoint, or the account can access the model.

The offline equivalent needs no key:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-offline.json --offline --preflight
```

## Live execution

With provider access ready, explicitly run the smoke test in a fresh directory:

```sh
uv run --locked python scripts/run_experiment.py configs/inspect-live-smoke.json \
  --model-cost-config configs/openai-smoke-pricing.json \
  --output runs/preparation/live-smoke-001
```

For Python callers, use `configure_model_cost(model_id, path)` from
`poker_collusion.pricing` before `run_experiment(config, output_dir)`.
The default runner and CLI construct the provider through `configured_model` so
OpenAI SDK retries are disabled independently of Inspect's retry setting.
Injected test models must honor the same transport contract.

## Verify and review saved evidence

```sh
uv run --locked python scripts/verify_run.py runs/preparation/live-smoke-001
```

This command makes no model calls. It checks the complete run manifest, planned
sample coverage, matched deals and settings, Inspect/session/request links, and
both journals. It replays every game trajectory and checks that raw successful
text parses to the decision recorded by the session engine. It also compares
actual Inspect inputs with the permitted prompts, verifies generation settings
and cache/retry records, checks raw payload availability, and reconciles usage.
Returned model identifiers must match the configured snapshot, allowing omission
of the provider prefix; an alias mismatch needs explicit review.

The JSON report includes each session's status, completed hands, call and payload
counts, returned model identifiers, token totals, summed call durations, metered
cost, and issues. Non-complete sessions or insufficient evidence produce a
nonzero exit. Corrupt or missing files also fail. Neither a successful Inspect
evaluation status nor a mock report by itself establishes live compatibility.
Artifacts remain verifiable after copying the entire run directory: references
are resolved within that directory rather than using their original absolute paths.

Token accounting follows Inspect's convention: `input_tokens` excludes cache
reads and writes, which have separate report fields. Those three input counts
plus `output_tokens` must equal `total_tokens`. `reasoning_tokens` is a subset
of output, not an additional charge in the token total. Negative or contradictory
counts fail verification, as do disagreements between per-call usage and any
model's session-level counts.

Review the raw OpenAI requests and responses in `model.jsonl` or Inspect's viewer
before accepting the live check. The current SDK translates the system role to
`developer` and the output cap to `max_completion_tokens` for this model; offline
HTTP tests check that conversion, exact user-view JSON, no tools, and single-call
failure behavior. The verifier checks provider-independent Inspect inputs; it
does not claim to validate every provider's raw wire format or server behavior.

The live review must confirm successful legal decisions in all channels, the
snapshot identifier, complete usage and raw payloads, expected parameter mapping,
and no additional conversation state or unintended inputs. Preserve failures and
diagnostics if any check fails. Successful compatibility is the prerequisite for
the separate competence/coordination-control pilot, not its result.
