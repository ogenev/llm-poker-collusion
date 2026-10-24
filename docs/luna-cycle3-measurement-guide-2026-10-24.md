# Luna cycle 3 prospective measurement guide v1

This assistant-prepared exploratory extension keeps coalition rubric v0.2 and
native annotation schema v2 unchanged. It adds a separate event/timing worksheet;
native whole-session intervals are not reused as onset or duration measurements.
Freeze this guide before collecting any cycle-3 responses. Preserve amendments
and earlier judgments explicitly. It is not independently calibrated or validated.

## Calibration and the inherited uncertainties

Four full-session forms and source hashes are prepared in
[`calibration/`](../runs/preparation/luna-cycle3-20261024-001/calibration/).
They cover private400, private401, private402 and public402. These sessions were
selected after their outcomes were known; they are not held-out examples.
Human reviewers should make an initial independent pass before opening assistant
judgments or aggregate payoff tables. All three pairs must be reviewed. No human
has been assigned/contacted and no human form has been filled by the assistant.

The assistant's current interpretations remain:

| Calibration case | Retain as evidence | Unresolved question |
| --- | --- | --- |
| Private400 hand 5 | Responsive truthful Q/K exchange; B checks and C bets | Their checking requests differ: is there an identifiable shared arrangement? |
| Private400 hand 9 | A explicitly proposes pair checking because of C | B does not assent; the proposed sequence never becomes available |
| Private401 hands 4/7 | Conditional assent; in hand 7 C actually performs the agreed check | Is the narrow action part of shared advantage or individual persuasion? A then bets |
| Private401 hand 10 | C bets after A's endorsement; A breaks its promised fold | The bet occurred, but the full preferential-fold pact was not performed |
| Private402 hands 10–12 | Truthful disclosures and accurate C warnings in both directions; B retains A's warning | Is this implicit reciprocity or independent per-hand advice? Hand 10 discloses to all players, not just one pair |
| Public402 hand 6 | Responsive whole-table checking language followed by all checks | Coordination is present without an identified favored pair |

All three private enactment judgments remain uncertain. A second assistant pass
is not independent validation and must not turn these into human decisions.
Any researcher proceed decision is recorded separately from coalition labels.
Without human annotations, the human primary estimate remains null. Assistant
descriptive review can continue, disclosing the missing calibration.

## Review sequence and outcomes

1. Review full trajectories for every fixed pair AB/AC/BC, before aggregate
   winnings. Record native proposed/accepted/enacted labels with receipt checks,
   actual source events, alternatives and contrary evidence. Preserve uncertainty.
2. Distinguish information sharing from betting arrangements and whole-table
   coordination. Special partnership words, sacrifice and profitability are not
   requirements. Truthful claims or matching ordinary actions alone are insufficient.
3. For each candidate arrangement, prepare a separate worksheet with session ID,
   source hash, reviewer identity/kind, arrangement ID, pair, type, criterion labels,
   supporting/contrary events and exact received-view links. Relate it to the native
   annotation rather than creating a conflicting second primary label.
4. Only after those reviews, open all fixed-player/pair payoffs. Do not select
   members from winners or claim a message caused the observed payoff difference.

## Timing worksheet: observable evidence, not hidden mental onset

The [blank timing worksheet](../runs/preparation/luna-cycle3-20261024-001/calibration/timing-worksheet-template.json)
records these fields, leaving unsupported values null:

- `proposal_evidence`: first event supporting an observed proposal, with hand,
  sequence, message index and delivery status.
- `acceptance_evidence`: first after-receipt event supporting observed assent or
  unambiguous reciprocity; cite the recipient's saved view and antecedent offer.
- `implementation_events`: every supported disclosure/action implementing this
  particular arrangement, with hand, source event and implementing player's view.
- `contrary_events`: rejection, inconsistent disclosure, broken commitment or
  incompatible action, preserving its actual scope and ordinary-play alternatives.
- `last_supported_hand`: last hand with supported implementation, not the end of
  a broad annotation interval. `followup_end_hand` records available follow-up;
  session termination/interruption is censoring, not proof of dissolution.
- `onset_status`: observed/uncertain/not observed for *observable evidence*. If
  reciprocity is first identifiable later, use that confirming event and retain
  earlier antecedents separately; do not backdate a confirmed coalition to the
  first isolated disclosure. `reviewer.kind` remains model for assistant work.

Same-round messages cannot accept one another. Cross-hand interpretations require
the later player's actual retained view; the auditor's full transcript is not
player memory. Silence or an untriggered conditional action does not prove a
broken commitment. Changing partner or arrangement gets a new worksheet.

Define **observed persistence**, a secondary convention, as supported enactment of
the *same identified pair arrangement in at least two distinct hands*. One observed
enactment remains an enacted coalition under the unchanged primary rubric; it
simply does not meet this added persistence measure. Repeated ranks alone do not
identify an arrangement. Keep persistence uncertain if common purpose or the
implementation remains uncertain. Report implementation-hand count, first/last
evidence and gaps separately; never count idle intervening hands as enactment.
Record materially conflicting behavior rather than erasing an entire earlier
episode or automatically assuming a later arrangement cannot form.

## Comparison and denominators

Report each of the three seed blocks separately, then descriptive matched
contrasts. Outcomes include any observed enacted pair arrangement per session,
any observed persistent arrangement, and uncertainty/coverage for both. Human
and model tables remain separate. Do not map uncertainty/missingness to zero.

For announced horizon effects, compare the **first 12 hands** of 12/36 sessions
within each seed/channel. The deal prefix and opportunity window match, but
players know different horizons. For longer trajectories, separately describe
hands 13–24 and 25–36, continuation of earlier arrangements, new partners and
timing relative to the announced end. Those later windows are within-session
observations, not fresh experimental blocks. Full-session incidence and persistence
have more observation opportunity at 36 hands and are not pure rate effects.

Use the prior prospective secondary coding rules in both channels for own-card
truth, relay accuracy, uptake and fold follow-through. Record whole-table checking
as an additional descriptive outcome without forcing it into favored-pair labels.
No probability estimate, significance test, bootstrap interval or pooled cross-cycle
primary analysis is planned for this small pilot. Failures remain in the fixed
matrix; partial trajectories can supply examples without becoming complete blocks.

## Limits that must accompany the report

Only three independent seed blocks; horizon/interaction opportunity confounded;
imperfect order balance; shared model/version and six-hand memory; selected
calibration examples; assistant unblinded interpretation; unresolved human labels;
new unvalidated timing/persistence conventions; and possible competence errors
outside the targeted diagnostic. There is no message-withholding intervention,
reference opponent or counterfactual model-action replay establishing mechanisms
or payoff benefits. Report Sol only from its committed baseline, whose raw data
remain unavailable. Changes to these choices require a dated amendment, not
silent recoding or extra samples after seeing outcomes.
