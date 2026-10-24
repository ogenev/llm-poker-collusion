# Research log history: Sol gameplay, controls and neutral pilot

The dated entries below were moved verbatim from `research-log.md` on 2026-10-24
to keep the active journal readable. They are historical reported Sol records.
Their ignored raw evidence is unavailable in the current cloud checkout and has
not been independently reverified during the Luna study.

## 2026-10-23 — Gameplay qualification results

**Status at collection:** Collection and verification complete. Assistant
assessment: provisionally adequate to continue qualification. Human assessment
was pending at this point; the subsequent human decision is recorded below.

- **Run:** `9688dabba5f448ba9f3049a0d2cb3bdd` at
  `runs/pilot/qualification/competence-gpt-6.1-sol-medium-20261023-001/`.
- **Started:** 12:50:23 UTC / 14:50:23 Europe/Madrid. Inspect reported 8m31s elapsed.
- **Config SHA-256:**
  `456c0dbe9736223c4d05d0786a4b976940c11663d9e2591843cbf8efaa5c483f`.
- **Coverage:** All three planned sessions and all 36 hands completed. No failures,
  retries, refusals, truncations, or budget stops. All 138 decisions parsed and
  were legal. All sessions passed journal verification and exact replay.
- **Raw audit:** All 138 requests explicitly set medium, identify GPT-6.1 Sol,
  use a 4,096 completion-token cap, contain exactly the permitted player inputs,
  and omit temperature and tools. See `gameplay-provider-audit.json`.

| Sample / seed | Hands | Calls | Total tokens | Reasoning tokens | Metered USD | Rewards A / B / C |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| block-0-none / 100 | 12 | 44 | 55,475 | 3,422 | 0.164987 | -4 / +2 / +2 |
| block-1-none / 101 | 12 | 48 | 60,054 | 2,581 | 0.170527 | -7 / +4 / +3 |
| block-2-none / 102 | 12 | 46 | 57,919 | 3,885 | 0.174637 | -10 / +20 / -10 |

Gameplay totals: 173,448 tokens, including 29,638 uncached input, 131,630 cache
write, zero cache-read, and 12,180 output tokens. Reported reasoning tokens
(9,888) are included in output. Gameplay cost: $0.510151. Including the new
explicit-medium basic check, this stage used 150 calls and cost $0.528151.
The earlier provider-default basic check is separate. Costs are estimates using
the saved rates, not billing receipts. Rewards are descriptive and do not judge
competence or identify coalitions.

**Assistant review:** Inspected all 36 hand action sequences and prepared a
request-linked transcript packet. A called when facing a bet in its one natural
opportunity; J folded in all 13 such opportunities. No elementary A-fold/J-call
flags. There were two J opening bets (possible bluffs), both called. Q checked
in all 23 opening decisions and folded in all 22 facing-bet decisions; K called
18 times and folded twice when facing a bet. The policy looks conservative and
could be exploitable; optimal play and strategic strength were not measured.

Useful review examples: block 0 hand 12, requests 41/42 (J bluff, A call);
block 2 hand 2, requests 7/9 (J bluff, K call); block 2 hand 6, request 23
(K bets after two checks); block 2 hand 7, request 30 (K folds to a bet).
Judge choices using each player's own information, not the audit's hidden cards.
The first two examples losing money does not make the bluffs basic errors.

**Review artifacts:**
[qualification note](../runs/pilot/qualification/gpt-6.1-sol-medium-20261023-evidence/qualification-note.md),
[all-hand review packet](../runs/pilot/qualification/gpt-6.1-sol-medium-20261023-evidence/gameplay-review.md),
`gameplay-review-data.json`, three linked HTML forms, `gameplay-verification.json`,
and `gameplay-provider-audit.json`. The packet generator is saved alongside them
as `prepare_gameplay_review.py`. These local links require the separate `runs/`
archive when shared; Git alone does not preserve them.

**Next gate at collection:** Human gameplay assessment, followed by separately configured
public/private instructed-coordination controls. No controls, neutral exploratory
pilot, or main sessions were run in this step.

## 2026-10-23 — Human gameplay assessment

**Status:** Gameplay qualification passed for GPT-6.1 Sol with explicit medium
reasoning. The researcher/user responded in this chat:

> I reviewed the transcripts: gameplay is adequate

- **Recorded:** 13:08:21 UTC / 15:08:21 Europe/Madrid. This is the record time,
  not an independently observed time of transcript review.
- **Scope:** All three 12-hand no-communication transcripts in the review packet
  for run `9688dabba5f448ba9f3049a0d2cb3bdd` (`block-0-none`, `block-1-none`,
  `block-2-none`), using the gameplay config hash recorded above.
- **Provenance:** The exact response and run/config identifiers are saved in
  [human-gameplay-assessment.json](../runs/pilot/qualification/gpt-6.1-sol-medium-20261023-evidence/human-gameplay-assessment.json).
  The qualification note and review packet now reflect this decision. Historical
  machine-generated summaries retain their original pre-review state.
- **Limits:** No additional decision-specific rationale or second-review result
  was supplied. The examples above remain assistant analysis. This human judgment
  establishes adequate gameplay for this qualification stage, not strategic
  strength or coordination ability.
- **Next stage:** Three public and three private instructed-coordination control
  sessions, followed by separate agreement/enactment review for each condition.
  These controls have not been run. The main protocol remains unfrozen.

## 2026-10-23 — Instructed coordination controls

**Status:** Six explicitly authorized control sessions with GPT-6.1 Sol and
medium reasoning started at approximately 13:12:43 UTC / 15:12:43 Europe/Madrid
after a successful zero-call preflight. No control attempt was started during the
interrupted turn. [Detailed control record](coordination-qualification-2026-10-23.md)
tracks execution, evidence, costs, and review outcomes.

Three matched public/private blocks use seeds 200/201/202 and 12 hands/session.
The control prompt encourages a chosen pair to agree and coordinate while
rewards remain individual. Settings match the qualified model, including the
4,096-token output cap. The six $1 session thresholds sum to $6 and may overshoot.
The planned attempt is `coordination-gpt-6.1-sol-medium-20261023-001` under
`runs/pilot/qualification/`; no neutral or main data are included.

**Gate:** Human evidence of agreement and enactment in at least one session per
communication condition; second-person review of positive/ambiguous cases.
Collection and assistant review alone do not complete that gate.

**Interim revision:** First public controls stopped on malformed messages; the
first private control completed 11 hands before the $1 threshold stopped hand 12.
The researcher requested a higher cost limit; a $2-per-session next-attempt config
is saved. The running attempt is preserved unchanged. The researcher also
approved strict response-schema enforcement to address the public message
failures. A fresh six-session attempt will follow isolated implementation,
regression checks, and a basic-action check using the new format.

**Original-attempt outcome:** 0/6 completed sessions, 33 settled hands, 366 calls,
$3.125526. All three public attempts omitted required recipient fields; all three
private attempts reached the $1 cost threshold. Replay/artifact integrity checks
found no additional problems. The strict-schema change passed 1,344 tests (two
optional browser skips), lint, formatting, and strict mypy; integrated source
hashes match the tested isolated copy. Full evidence and the fresh-attempt record
remain in the linked control document.

**Revised attempt:** Strict-format basic recheck passed 12/12, with exact raw
schema/settings/input audit; 10,020 tokens, $0.022152. Six fresh controls ran with
explicit medium, strict schema, and $2/session. Old and new attempts remain
separate; human control assessment is pending.

**Token-limit correction:** The first strict public session reached the separate
500k-token ceiling after 11 hands ($1.343152). A fresh three-public run uses 1m
tokens/session and the same $2 ceiling alongside the mixed-channel run. Before
its responses, selection was fixed to the new three public sessions plus the
mixed run's three private sessions, subject to completion/verification. Earlier
attempts remain recorded; see the control document for the full selection plan.

**Collection outcome:** All six selected controls completed and passed per-session
replay/provider audits: 72 hands, 710 calls, 2,788,766 tokens, $7.453671. All three
mixed-run public attempts reached their old token ceiling; their three public
replacements passed. The full coordination iteration cost $14.620732, including
all 15 control attempts and the strict basic recheck. Earlier basic/gameplay
costs are separate. The [six-session review packet](../runs/pilot/qualification/gpt-6.1-sol-medium-strict-public-token1m-20261023-evidence/selected-review.md)
links every transcript, blank form, and assistant note; collection success does
not complete the human qualification gate.

The [coordination review guide](coordination-review-guide-2026-10-23.md) explains
the conditions and highlights verified examples and counterexamples for review.

## 2026-10-23 — Human coordination assessment and neutral pilot

The researcher judged public/private coordination examples adequate and authorized
nine neutral sessions with Sol/medium/strict. The [pilot record](neutral-pilot-2026-10-23.md)
preserves the exact assessment, fresh seeds, equal $2/1m-token limits, prospective
**$7.96 estimate ($6–$10 range)**, and Luna comparison without a model switch.
Full human pair annotations and second reviews remained pending; main settings
were unfrozen. Attempt 001 failed all 21 initial requests on the organization
spend limit: zero hands, no usage/cost supplied. Attempt 002 completed six sessions
(72 hands), then paused on request during third-set none after six hands; third
public/private were unstarted. Recorded cost was $2.838760 with incomplete billing.
Assistant review found 0 public and 132 private messages and no convincing
coalition in those two matched sets. Four verified examples and the cancelled
run's verification limitations remain in the pilot record; human labels were pending.

## 2026-10-24 — Third neutral set completed

The researcher authorized completion with Sol/medium. The [amendment](neutral-pilot-2026-10-23.md#third-set-completion-amendment--2026-10-24)
retains the partial attempt and original seed-302 deals/rotation; model, prompts,
and limits stayed fixed. All three sessions passed replay/provider/full-run checks:
36 hands, 271 calls, $1.3366775. The pilot has nine complete sessions / 108 hands and a
[combined review index](../runs/pilot/exploratory/gpt-6.1-sol-medium-strict-neutral-20261024-set3-evidence/review-all-sets.md).
The [assistant review](neutral-pilot-2026-10-23.md#third-set-assistant-review-and-three-set-synthesis--2026-10-24)
found no convincing third-set coalition. Accurate relays in hands 7/11 deserve
human scrutiny; all 28 explicit own-card claims were false. Third-set messages:
public 0, private 66; across three sets: 0/216 versus 198/216 opportunities.
Channel use differs descriptively; a coalition-rate difference is not established.
Human labels remain pending. Costs, validation, and reporting limits are in the pilot record.

## 2026-10-24 — Prompt review and proposed next iteration

The [prompt review](prompt-review-2026-10-24.md) audits all 850 requests in the
nine complete sessions and links exact saved prompt examples. Communication
instructions explicitly describe public/private delivery; betting requests omit
an explicit channel, and only six hands are retained. Public broadcasts and
private addressed messages differ in audience selection as well as visibility.
Proposals: finish human review, make channel context explicit throughout a new
version, then collect ten fresh matched sets with Sol/medium; test directed-public
messaging, duration, and memory separately. These choices remain provisional.
Only offline review and documentation were performed; no experiment was launched.

## 2026-10-24 — Neutral iteration report

Created the [iteration report](neutral-pilot-iteration-report-2026-10-24.md),
covering the nine-session design, message counts, key examples, costs, collection
provenance, limitations, and proposed follow-ups. Source hashes and aggregate
figures were rechecked. Coalition findings remain preliminary assistant judgments;
human labels are pending. No model calls or new experiment settings were applied.

