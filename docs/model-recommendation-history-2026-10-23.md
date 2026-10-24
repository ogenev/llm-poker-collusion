# Initial model recommendation history

Original research-log entry, preserved verbatim below. Moved on 2026-10-24
to keep the active [research log](research-log.md) bounded.

## 2026-10-23 — Initial model recommendation (superseded)

**Status: superseded by the researcher's GPT-6.1 Sol choice below.** The initial
recommendation is retained to preserve the decision history.

Start qualification and the first exploratory iteration with
`openai/gpt-5.4-mini-2026-03-17`, the same snapshot for all three players and all
conditions. Retain it for the sprint's main study only if qualification and
practical throughput are adequate.

### Rationale

1. **Existing integration evidence.** The recorded smoke run checked legal
   responses, private player inputs, exact replay, raw provider payloads, model
   identity, and usage. Starting here reduces integration uncertainty during the
   sprint. These checks do not establish poker strength.
2. **A dated snapshot.** The configured identifier matches the snapshot listed
   in the [official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
   Pinning it makes the study target explicit; it does not make sampling
   deterministic or guarantee indefinite availability.
3. **Feasible initial cost.** Its standard token rates remain consistent with our
   pricing file. The prior smoke run was inexpensive, although longer histories
   and different behavior prevent simply extrapolating its cost to the study.
4. **An empirical selection gate.** Adequacy for this small game must be tested
   through gameplay and instructed controls. General coding or reasoning claims
   do not demonstrate poker competence or a tendency to coordinate.

### Current alternatives considered

Official documentation and prices checked on 2026-10-23. Rates below are USD per
million tokens at Standard processing rates and short context; cache writes,
regional premiums, different tiers, and token consumption can change total cost.

| Candidate | Input | Cached input | Output | Role considered |
| --- | ---: | ---: | ---: | --- |
| GPT-5.4 mini | $0.75 | $0.075 | $4.50 | Initial candidate with a dated snapshot and local compatibility evidence. |
| GPT-6 Luna | $0.10 | $0.01 | $0.50 | Lower token-price alternative if experiment volume becomes the constraint; requires compatibility and qualification checks here. |
| GPT-6.1 Sol | $2.00 | $0.10 | $10.00 | Candidate to investigate if the current model shows substantive competence limitations; poker superiority is untested. |

Sources: [official API pricing](https://developers.openai.com/api/docs/pricing),
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), and
[GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol).
The GPT-6 pages currently list identifiers without dated suffixes. Account
access, behavior, latency, and usage for these alternatives were not tested.
This is a focused comparison within our existing provider integration, not a
benchmark of all available models or providers.

The recommendation therefore rests on existing integration evidence and the
qualification plan. GPT-5.4 mini is not the lowest-price model in this comparison.
GPT-6.1 Sol's documented positioning for more demanding work makes it a candidate
for a capability check, not evidence that it will coordinate more successfully.

### Settings and reconsideration rule

The prepared configurations use a 2,048-token output cap, omit temperature and
reasoning effort, disable sampled-response reuse, and allow no retries. The
current GPT-5.4 mini documentation lists default reasoning effort as `none`;
the preparation smoke run recorded zero reasoning tokens. The resulting study
would characterize this configuration, not all reasoning settings of the model.

If qualification fails, first distinguish API/parser/budget problems from
substantive gameplay or coordination failures. Document any prompt, reasoning,
output-budget, or model change and requalify the revised configuration in a new
attempt. Do not switch models merely because a neutral pilot lacks spontaneous
coordination. Choose and freeze the main configuration before main responses.

**Action in this entry:** Created the notebook, checked current documentation,
and recorded the recommendation. No live model calls or experiment-configuration
changes were made for this entry.

