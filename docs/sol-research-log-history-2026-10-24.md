# Sol research-log history — 2026-10-24

Verbatim entries moved from `docs/research-log.md` at source commit
`183b96f44493abfd86f3728795ca501864e58828` to keep the active notebook manageable.
These are historical reported records, not new or independently reverified runs.
Return to the [active research log](research-log.md).

## 2026-10-23 — GPT-6.1 Sol basic action screen

**Status:** Complete; basic screen passed. Live run, not a mock.

- **Run ID:** `76de93791b8d4f14829997bb1bff653a`.
- **Started:** 12:42:56 UTC / 14:42:56 Europe/Madrid.
- **Artifacts:** `runs/pilot/qualification/poker-basics-gpt-6.1-sol-20261023-001/`.
  Preserve `summary.json`, `results.jsonl`, `model.jsonl`, `run.jsonl`, and the
  Inspect `.eval` file together.
- **Source:** Base commit `2b9f9db14945c0736568d8d3c71a0878599269c7`;
  new configuration/pricing/notebook files and the README link were uncommitted.
  Runtime source was unchanged for this run; the manifest preserves provenance.
- **Config SHA-256:**
  `5fcd0e5a8b8e848f155b59e03adc8daa097d2dcec473b1ecdfb752f09ea8b1f5`.
- **Case-set SHA-256:**
  `676b0f5b28b4f25feadf772e5611fe772e887b0e370f40dc257438897f7929b9`.
- **Results:** 12 attempted, 12 valid and correct, zero failed or incomplete;
  `live_basic_check_passed: true` and no evidence issues.
- **Usage:** 8,280 input tokens, 144 output tokens, zero reported cache-read,
  cache-write, or reasoning tokens. Total: 8,424 tokens.
- **Cost / time:** $0.018 metered estimate; approximately 26 seconds reported
  elapsed time, with 25.28 seconds summed across model calls.
- **Provider evidence:** All 12 journaled raw request/response pairs name
  `gpt-6.1-sol`, use developer/user messages, a 4,096 completion-token cap, no
  tools, and a normal stop. The requests omit `reasoning_effort`.

**Interpretation:** The model made the obvious A-call/J-fold decisions correctly
in each seat and both repetitions. This supports basic rule understanding for
these cases, not general strategic strength, repeated-game competence, or
coordination ability. This diagnostic has no full-session replay report.

**Reasoning caveat:** The official documentation describes `medium` as the
default, but the saved requests did not explicitly set it and returned usage
reported zero reasoning tokens. Label this run **provider default**, not an
explicit-medium experiment. Zero reported reasoning tokens alone does not
establish that the provider used a different effort setting.

**Operational note:** Sandboxed `uv` first failed on cache access and then on
macOS system configuration. Retrying outside that sandbox allowed preflight
(zero API calls) and the single live attempt. The launcher failures generated
no model responses and are not failed poker probes.

## 2026-10-23 — Reasoning-effort recommendation

**Proposal:** Use explicit `reasoning_effort: "medium"` for all players and all
conditions in the gameplay pilot, positive controls, and eventual main study.
The researcher asked which effort to use; this is a recommendation pending
implementation and pilot evidence, not a frozen main-study setting.

Reasoning about hidden cards, opponents' incentives, and repeated agreements
motivates giving the model a meaningful reasoning allowance. Medium is a
practical starting point for measuring capability alongside latency and cost.
We have not compared low, medium, or high on this task, so neither quality nor
the best cost/quality tradeoff is established. The
[model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
lists low, medium, high, xhigh, and max; none and minimal are unsupported.

Keep effort fixed within a comparison. If qualification suggests a limitation,
a separately documented high-effort diagnostic can test sensitivity; do not
mix its results into medium-effort data. Reasoning-effort selection must not
depend on which setting produces the preferred spontaneous-coordination result.

**Implementation needed before an explicit-medium run:** The current model
config schema has no reasoning-effort field. Add validated serialization and
Inspect forwarding, check the actual provider payload, and preserve the
provider-default attempt above. Recheck basic actions under the explicit setting
before interpreting gameplay. A 4,096-token cap is provisional: inspect
truncation, usage, and latency in the pilot and freeze a suitable cap before main
collection.
