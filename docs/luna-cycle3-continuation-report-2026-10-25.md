# Luna cycle 3 continuation report — in progress

Collection and review are ongoing. This document preserves the interpretation
framework and historical comparisons; it is not a completed result or a new
authorization. The [execution ledger](luna-cycle3-continuation-execution-2026-10-25.md)
and [research journal](research-log.md) record current progress and actual usage.

## Question and design

Can self-interested LLM poker players spontaneously form coalitions, and does
public versus private communication change the evidence? Cycle 3 additionally
explores whether an announced 36-hand horizon changes first-12 behavior relative
to an announced 12-hand horizon, and whether identifiable arrangements emerge
or persist later in the longer sessions.

The frozen design has three seed blocks (500–502), each with none/public/private
at both 12 and 36 hands. Within a seed/channel, the first 12 deals and rotation
match. Players know the announced horizon. Longer sessions retain six hands of
memory, so more total play does not mean unlimited retained history. The original
neutral prompts, mechanics and communication limits remain unchanged; the
cancelled channel-explicit revision was not restored. The playing model is
`openai/gpt-6-luna`, explicit medium reasoning, strict JSON schema, 4,096 maximum
output tokens including reasoning, no temperature override, no response reuse
and zero retries. Source/configuration hashes bind the execution.

The seed-500 36-hand private session failed with HTTP 520 during hand 32 after
31 settlements. It remains partial and was not retried or replaced. The
researcher explicitly approved only the twelve unstarted seed-501/502 cells on
October 25. At most two of the three planned six-session blocks can be complete.
The earlier [checkpoint report](luna-cycle3-checkpoint-report-2026-10-24.md) and
its archive remain unchanged.

## Evidence reviewed so far

The separate [transcript notes](luna-cycle3-continuation-transcript-review-2026-10-25.md)
retain actual messages, event references, ordinary-play alternatives and contrary
evidence. The completed seed-501 36-hand none/public reviews identify no pair
arrangement. The completed long-private assistant review has an observed late
information proposal and narrow assent, with uncertain coalition enactment and
persistence. BC24/29/33 is a possible information pattern; AB22/28 and BC30 are
uncertain preferential-play cases with ordinary alternatives. The short batch
also passes its evidence/review gate, giving one complete six-condition seed501
block. Its private enactment is uncertain,
with AC10 responsive true disclosure, BC11/12 possible delayed exchange, and
hand12 whole-table checking. None/public have no identified arrangement at either
horizon. Private first12 true-claim counts are short20/49 and long30/49, descriptive
conditional counts rather than a horizon effect. Earlier seed-500 information cases remain
as reported in the checkpoint, including AB hands 7/10, BC hand 14 and AC hands
24/25/28/31. Information implementation is distinct from betting coordination,
standing partnership, causal influence or payoff benefit.

Seed502's short batch also passes its gate. Unlike seed501, its public review has
observed narrow assent and uncertain enactment, including paired checks10 and
whole-table checks11. Private enactment is uncertain too: call commitments4/10
are followed with ordinary history/false-premise alternatives, an explicit card
request9 gets a false reply, and later truthful exchanges remain candidates.
A distorted historical warning12 adds a competence limitation despite the earlier
diagnostic pass. The long seed502 comparison is still pending; public messaging
must not be described as uniformly negative or candidates as private-only.

All assistant annotations use reviewer kind `model`. Human forms remain blank
and the human primary estimate remains null. Researcher authorization to proceed
does not supply human coalition labels. First-12 and subsequent 12-hand prefix
reviews are frozen before reading later hands; final whole-session interpretations
must preserve those earlier judgments rather than silently recode them. New
aggregate payoff tables remain unopened pending available-source/review gates.
The old seed-500 partial-private payoff exposure during failure diagnosis remains
explicitly recorded; it is not erased by the new review sequence.

## Comparison with prior Luna and reported Sol

These are descriptive historical comparisons, not randomized model comparisons.
The Sol raw logs are unavailable here: its committed report is a reported
baseline, not independently reverified evidence.

| Iteration | Experimental coverage | Messaging / findings | Recorded API cost |
| --- | --- | --- | --- |
| Reported GPT-6.1 Sol neutral pilot | Three matched sets, nine 12-hand sessions, 108 hands | Public 0/216 possible messages; private 198/216. Preliminary assistant review reported no convincing coalition; human neutral adjudication pending. | $4.0797365, 850 calls, 1,403,108 tokens |
| Luna first neutral pilot, seeds 300–302 | Three matched sets, nine 12-hand sessions, 108 hands | Public 98/216; private 155/216. Assistant private enactment uncertain; none/public no identified arrangement. | $0.4561972, 813 calls, 1,909,128 tokens |
| Luna second neutral pilot, seeds 400–402 | Two complete sets of three planned; eight complete sessions plus partial public400, 103 settled hands | Private reciprocal-warning candidates remained uncertain; private401 had observed narrow assent. | $0.4205535 known neutral cost plus two unknown requests; 765 started/763 usable calls |
| Luna cycle 3 | Three planned six-condition seed blocks; seed501 complete, seed500 has one partial cell, seed502 collecting | Seed501 private enactment uncertain at both horizons; none/public no identified arrangement. Seed500 information cases remain separately reported. | In progress; separate diagnostic, neutral and continuation accounting required |

The first Luna neutral pilot's recorded cost was about 89% lower than the
reported Sol pilot at the same 108-hand design. Different messaging/action counts,
prices and token accounting contributed; this is not a cost-normalized quality
comparison. Sol's public silence and Luna's public messaging are conspicuous
reported behavioral differences, but a three-set pilot cannot establish their
population frequency. Cycle 3's changed horizon, seeds and partial cell prevent
a simple like-for-like full-cycle cost or coalition-rate comparison with Sol.

The [committed Sol report](neutral-pilot-iteration-report-2026-10-24.md) describes
private card questions with false answers (seed301 hand1), an accurate relay
combined with a false own-card claim (302 hand7), a broken fold promise (302
hand10), and a historical warning followed by ordinary calling (302 hand11).
Those mechanisms also occur in Luna's transcripts. Sol's reported absence of a
convincing coalition is a preliminary assistant assessment, not a verified zero
rate or a human-calibrated model difference. Its reported 28 direct rank claims,
all false, concern one private session and a narrower coding definition; comparing
that percentage directly with Luna's broader semantic claim counts would require
the unavailable raw logs and consistent recoding.

## Limitations that govern interpretation

- The independent experimental units are the three planned seed blocks. Hands,
  windows, pairs, claims and messages are dependent observations. A partial
  trajectory can provide examples without becoming a complete replication.
- More hands provide more opportunities for observed enactment and persistence.
  Full 12/36-session incidence is therefore not a pure horizon effect. The
  matched first-12 comparison controls opportunity length, but stochastic
  responses and the tiny sample still limit interpretation.
- Horizon order is imperfectly balanced. Collection spans October 24/25;
  retaining the same model alias does not independently verify unchanged
  provider weights across dates. No version change is asserted.
- The assistant is unblinded, nonindependent and lacks human calibration. Selected
  prior calibration examples were chosen after their outcomes were known.
  The provisional timing/persistence convention is not independently validated.
- Accurate historical relays coexist with incorrect or ambiguously scoped
  attributions. The targeted retained-history diagnostic passed 26/26 cases;
  that does not establish general strategic competence or uniformly reliable
  recall during play. Auditor-visible history is not player-visible memory.
- Truthful disclosure alone is insufficient for coalition enactment. Identify
  the reciprocal arrangement and receipt order; simultaneous messages cannot
  accept one another. Matching ordinary bets/folds and a weak-card fulfilled
  promise are weaker evidence than an identified joint sequence.
- No message-withholding intervention, reference opponent or counterfactual
  action replay establishes causal mechanisms or benefits to a pair. Members
  must be identified before comparing all fixed-player/pair payoffs.
- Failed-request usage is unknown rather than zero. Metered costs are estimates,
  not invoices. The original failed attempts and archive/reproduction records
  remain part of the evidence.

## Completion requirements and next decisions

Complete only the approved unstarted cells, pausing subsequent batches on a new
failure. Verify saved raw/provider evidence, all fixed-pair reviews, prefix
integrity and exact receipt links; preserve every attempt. Then open descriptive
payoffs, report the fixed matrix including missingness, and freeze a new archive
with raw evidence, blank human forms, transcripts, usage and checksum manifest.

Next-cycle recommendations will follow the completed available-data review.
Human adjudication and targeted measurement checks remain prerequisites to
claiming a calibrated coalition rate. Any additional paid seeds, replacement
runs, changed prompts or ten-set expansion require a separate concrete plan and
approval; none is part of this continuation.
