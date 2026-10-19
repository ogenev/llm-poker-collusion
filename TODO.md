# Poker Collusion Implementation Checklist

Implement the study described in [the project overview](llm-poker-collusion-research-project.md) in two phases, using the same simplified architecture: one Python package, an Inspect integration, a session engine, and offline analysis. Use OpenSpiel for the poker rules and Colosseum as a methodological reference.

This checklist tracks implementation and experiment tasks. Complete each phase's milestones in order unless their dependencies permit independent work. Mark a task complete only when its implementation and relevant verification are finished. Phase 1 is a complete sprint deliverable; Phase 2 extends the same code into the full research project.

Preparation increment completed on 2026-10-12: [game protocol](docs/game-protocol.md), locked Python environment, typed game records, OpenSpiel wrapper, and saved matched schedules. The offline suite passes 548 tests, including all 24 deals × 13 terminal paths, privacy, and game replay. Lint, formatting, and strict type checks pass. Inspect and OpenSpiel load together; session execution and model integration remain pending. Full session schemas and the remaining protocol choices below are required before implementing the session layer. No model calls or research runs have been made.

Session increment completed on 2026-10-15: [session protocol](docs/session-protocol.md), validated runtime configuration, immutable player views and decisions, explicit in-memory session state, and scripted sessions in all three channels. The suite now passes 618 tests, including delivery barriers, private-message metadata, folded-card memory, budgets, history retention, reset, failures, and cancellation. The demo completes 30 hands in each condition. Durable audit records, replay, provider configuration, model prompts, and Inspect execution remain pending; no model calls have been made.

Recording increment completed on 2026-10-15: optional append-only JSONL journals, versioned configuration and terminal state records, exact scripted callback observations/responses, durable decisions before effects, and verified full-session replay through the ordinary runner. Failed and cleanly interrupted attempts replay with their original status; abrupt exits retain inspectable incomplete prefixes. See the [recording protocol](docs/recording-protocol.md). This is still pre-sprint preparation; Inspect execution, provider prompts/settings, and research runs remain pending. Mid-session recovery and intervention execution remain Phase 2.

Recording verification: 749 offline tests pass, including 131 recording/replay
checks; Ruff lint/format and strict mypy pass. The CLI records and verifies
30-hand scripted sessions in all three Phase 1 channels. Failure replay and
incomplete-prefix inspection/exclusion also pass.

Audit encoding occurs only at the writer/replay boundary; unlogged sessions skip
it. Replay shares one active-request tracker with live execution. Malformed
response coverage includes deep/cyclic values and oversized integers, retaining
explicit failures without changing the version 1 journal format.

Offline model increment completed on 2026-10-15: packaged neutral and separate
coordination-control prompts, deterministic rendering from permitted player views,
versioned model configuration and prompt/configuration hashes, strict response
parsing, and an injected async text-generator adapter. Fake-model tests cover
rendered-input privacy, bounded memory/reset, all three channels, failure handling,
cancellation, and replay. Malformed text is retained as an invalid candidate in
the existing journal format. See the [model protocol](docs/model-protocol.md).
Inspect transport/task execution and durable provider request/response auditing
remain pending; no provider calls or research runs have been made.

Offline model verification: 875 tests pass, including 126 new model-boundary
checks. Ruff lint/format and strict mypy pass. The package wheel includes the
prompt resources, and the documented fake-model example completes using that wheel.

Inspect increment 2 completed on 2026-10-15: one sample per session, matched
channel blocks, explicit player-specific model inputs, bounded concurrency and
per-session limits, separate competence/control templates, and durable model-call
evidence linked to game requests and Inspect model events. The unchanged game
journal remains authoritative and replay uses no models. The
[Inspect protocol](docs/inspect-protocol.md) documents commands, artifacts, and
failure handling. Verification uses the actual Inspect runtime with a scripted
mock; usage is synthetic. Live provider compatibility remains increment 3, and
no provider calls or research runs have been made.

Inspect verification: 930 offline tests pass, with Ruff lint/format and strict
mypy passing. A concurrent 30-hand run in each of the three channels completes;
all 630 model calls retain raw mock payloads, both journals link successfully,
and all three game trajectories replay exactly. The suite covers out-of-order
responses, global connection limits, fresh attempts, private-input isolation,
malformed/refused/truncated responses, retry suppression, time/token/dollar limits,
disk failures, incomplete prefixes, and corrupted audit links.

Increment 3 offline preparation completed on 2026-10-15: a pinned OpenAI smoke
candidate, explicit pricing and workload limits, client preflight without API
calls, and a command that verifies complete saved runs across Inspect and both
journals. Tests exercise the real OpenAI SDK using simulated HTTP, including
request translation, raw evidence, failures, and zero SDK retries. See the
[live smoke instructions](docs/live-smoke.md). Review fixes size the smoke token
threshold for repeated prompts and check token accounting, including cached input,
reasoning, and per-model session totals. All 986 offline tests pass, with Ruff
lint/format and strict mypy passing. The live run is deliberately deferred
until API credentials and provider access are ready. No provider calls or research
runs have been made; compatibility, competence, and coordination remain unproven.

Phase 1 steps 1–6 review completed on 2026-10-15: whole-run verification now uses
the authoritative saved schedules, checks Inspect metadata against the game
journals, and rejects unmatched deals across conditions without depending on the
current deal generator. Oversized decision timeouts now produce the same
validation error as other invalid values. Eight regression cases bring the suite
to 994 passing offline tests; Ruff lint/format and strict mypy pass. The follow-up
review found no further actionable issues. Live qualification remains deferred,
and milestone 7 remains research sprint work.

Live qualification completed on 2026-10-17: the pinned OpenAI smoke candidate
completed all three matched channels, three hands each. All 64 calls retained
raw payloads; saved-run verification and raw provider review passed with no
issues, retries, or failed sessions. Usage was 73,701 tokens and metered cost
was $0.06272325. Evidence is retained in
`runs/preparation/live-smoke-20261017-001/`; see the
[accepted run](docs/live-smoke.md#accepted-run-2026-10-17). Milestone 6 is complete.
Competence, coordination controls, final study model selection, and evaluation
remain milestone 7; this smoke run is preparation data only.

## Phase scope

| Dimension | Phase 1 Sprint study | Phase 2 Full research project |
| --- | --- | --- |
| Models | One fixed model with three independent player histories | Multiple models and independent replications |
| Conditions | Public-only versus private-only; no-communication baseline | All four communication conditions crossed with neutral and fair-play instructions |
| Controls | Poker competence, a separate instructed-coordination positive control, and annotation checks | Reuse and extend controls across models and conditions |
| Analysis | Human-reviewed agreements and enacted coordination, descriptive payoffs, session-level uncertainty | Validated annotation, persistence, switching, controlled effectiveness, and fair-play violations |
| Counterfactuals | Optional small message-withholding check | Complete snapshots, robust recovery, repeated withholding, and all 24 next-hand deals |
| Output | Reproducible sprint experiment and report | Full experimental study, research report, and release artifacts |

Keep Phase 1 pilot and evaluation data separate, and keep both separate from Phase 2 confirmatory data. The primary Phase 1 comparison is private-only versus public-only under neutral instructions. A null finding is a valid result when its uncertainty and control results are reported. Phase 1 does not support claims about breaking an explicit fair-play rule.

## Architecture and scope

| Module | Responsibility |
| --- | --- |
| `experiment.py` | Inspect task and solver, model decision function, experiment configuration loading |
| `session.py` | Hand phases, turn scheduling, communication, player observations, bounded memory |
| `poker.py` | OpenSpiel wrapper, action translation, explicit dealing, settlement |
| `records.py` | Typed configuration and records, complete session state, event and snapshot persistence |
| `analysis.py` | Behavioral measurements, coalition annotation support, payoff analysis and exports |

Start with ordinary functions and explicit data structures. Keep source files below roughly 500 lines; extract a focused module when complexity warrants it. Tests, configuration files, prompt templates, and documentation live alongside these five initial modules.

The core extension points are a decision callable receiving only a player's permitted view, the poker wrapper, and explicit serializable session state. Phase 1 establishes those boundaries. Phase 2 adds snapshot-based recovery and counterfactual continuations through the same session loop.

Keep the session and game logic independent of Inspect types. Use JSONL for events and versioned JSON for state records and snapshots. Add analysis table exports when measurements need them. Parallelize independent sessions through Inspect before considering distributed workers. Phase 1 requires reliable records and explicit handling of failed sessions; full mid-session recovery is a Phase 2 deliverable.

## Phase 1 Sprint study

### Milestone 1 Specify the sprint protocol

Dependencies: none. Primary outputs: rules, configuration specification, and prompt requirements.

- [x] Align the overview and checklist with the accepted Inspect architecture and two-phase scope.
- [x] Specify the three-player, four-card rules completely: card ranks, one-chip ante, one opening bet, no raises, check/bet/call/fold semantics, response order, terminal states, and net settlement.
- [x] Specify what is revealed at showdown and after folds, including which cards and payoff information each player receives. Resolve this before constructing histories.
- [x] Define persistent player identities separately from acting positions. Specify seat rotation and whether matched deals are assigned by identity or position so comparisons remain consistent.
- [x] Define the fixed communication phase after dealing and before betting. Start the pilot with two configurable rounds and simultaneous delivery at each round's end; settle the choice before main runs.
- [x] Define optional messages, permitted recipients, message-length units, and per-player budgets. Match sending opportunities across public-only and private-only conditions.
- [x] Specify bounded memory, session length, new-session resets, and how prior hands are retained or removed. Use an explicit retention rule for the baseline.
- [x] Specify neutral individual-objective prompts and a separate instructed-coordination positive control. Keep partner assignment and pooled rewards out of the main conditions. Packaged templates and the [model protocol](docs/model-protocol.md) define the offline baseline; control performance and prompt suitability still require the live pilot.
- [x] Define malformed-output, refusal, timeout, retry, and incomplete-session handling before collecting results. Separate transport retries from additional model decisions. The runtime uses zero retries and explicit failed/interrupted states; any future provider retry policy must be specified and recorded before live evaluation.

Done when every observation, legal decision, phase transition, and failure outcome has a written rule. Unresolved pilot parameters must be explicit configuration fields.

### Milestone 2 Create the package and typed records

Dependencies: milestone 1. Primary outputs: package skeleton, locked environment, and state schemas.

Runtime session records, Phase 1 configuration, and audit persistence are implemented. The compound tasks below remain open where they also require analysis or complete recovery state. The current in-memory state is not a session checkpoint.

Milestone 5 now supplies durable events, versioned configuration/terminal records,
configuration and schedule hashes, and session/event/request identifiers with
optional run/matched-block identifiers. Milestone 6 adds model/experiment configuration,
prompt hashes, provenance, and Inspect references. Compound recovery tasks remain
open for Phase 2 snapshot/branch state.

- [x] Create `pyproject.toml`, a compatible Python environment managed with uv, and a lockfile. Verify the selected Inspect and OpenSpiel versions work together on the target machine. Python 3.13.7, Inspect 0.3.278, and OpenSpiel 1.6.15 install and import together on macOS arm64; end-to-end Inspect execution remains milestone 6.
- [ ] Add the five initial modules, test directories, configuration and prompt directories, and output-directory conventions.
- [x] Configure pytest, formatting, linting, and type checking with documented local commands. Keep ordinary verification independent of paid model calls.
- [x] Define validated configuration records for rules, communication, instructions, model settings, memory, deal schedules, stopping limits, and failure policy. Phase 1 rules and the zero-retry failure policy are fixed; the pinned OpenAI smoke candidate passed live compatibility on 2026-10-17.
- [ ] Define `PlayerView`, phase-specific decisions, messages, events, results, and serializable state. Reject inconsistent phase/action/channel combinations and unknown configuration values.
- [ ] Define complete session state: game state, phase and cursor, player identities and seats, all histories, rewards, pending messages, budgets, schedule position, and random-generator state.
- [ ] Define audit identifiers for runs, matched blocks, sessions, hands, events, requests, snapshots, and branches. Keep internal identifiers and experimental labels out of player-visible observations.
- [x] Add schema versions and configuration/prompt hashes. Reject incompatible saved records explicitly rather than loading them partially. Future snapshot/branch schemas accompany Phase 2 recovery.
- [x] Add environment-variable configuration for credentials and ignore generated runs, caches, and credential files in version control. `.env.example` documents `OPENAI_API_KEY`; preflight checks client setup without API calls. Secrets belong in the shell or managed environment, not experiment files.

Done when configurations and state records validate, serialize, and round-trip in offline tests, and the package passes the configured checks.

### Milestone 3 Implement and verify the poker wrapper

Dependencies: milestones 1 and 2. Primary module: `poker.py`.

- [x] Load OpenSpiel's parameterized three-player Kuhn game and verify its behavior against the written rules.
- [x] Implement explicit deal application, current-player lookup, legal actions, action application, terminal detection, and net returns.
- [x] Translate OpenSpiel action codes into unambiguous check/bet/call/fold decisions according to the current betting state.
- [x] Generate and persist seeded deal schedules with independent reshuffling between hands. Apply seat mappings consistently across matched conditions.
- [x] Enumerate all 24 ordered deals and every reachable legal betting path. Check termination, winner selection, chip accounting, and zero-sum returns against independently specified expected outcomes.
- [x] Cover late opening bets, previously checking players responding to a bet, all-check showdowns, all opponents folding, and attempts to act after termination.
- [x] Verify serialized game states restore the same legal actions and outcomes and that copied game states can change independently.

Done when the wrapper passes exhaustive offline game checks and the documented rules match its behavior. These 24-deal checks use no LLM calls; exhaustive LLM continuations belong to Phase 2.

### Milestone 4 Implement sessions and private communication

Dependencies: milestones 2 and 3. Primary module: `session.py`.

- [x] Implement the session loop with explicit deal, communication, betting, settlement, memory-update, and session-end phases.
- [x] Define an asynchronous decision callable that receives only a player's view and returns a validated message, pass, or betting decision. Supply scripted and seeded-random implementations for tests.
- [x] Construct player views from explicitly permitted fields. Include the player's own card, allowed public information, own rewards, delivered messages, and bounded history.
- [x] Implement no-communication, public-only, and private-only settings using configuration and small delivery functions.
- [x] Give every player the same private-recipient choices. Enforce optional sending, recipient validity, allowed channels, and message budgets in code.
- [x] Collect each communication round's decisions before delivery. Ensure model response timing cannot change another player's observation within that round.
- [x] Preserve identities through seat rotation, accumulate individual rewards, and apply the specified memory policy consistently. Reset all player histories between independent sessions.
- [x] Test observation privacy, including private-message metadata, folded cards, other players' histories, audit labels, and full game-state strings. Verify that one player's model output is shared only through an explicit message. This increment validates the scripted decision boundary; actual provider prompts are checked during Inspect integration.
- [x] Test the three Phase 1 channel conditions with scripted sessions, budget exhaustion, declined messages, invalid recipients, and malformed actions. Ensure failures follow the configured policy without silent substitutions.

Done when scripted players can complete repeated sessions in every condition and privacy and phase-order tests pass.

### Milestone 5 Implement reliable recording and replay

Dependencies: milestone 4. Primary modules: `records.py` and `session.py`.

- [x] Record append-only events for phase transitions, deals, views, decisions, message sending and delivery, actions, rewards, memory updates, and failures. Intervention records accompany intervention execution in Phase 2; no interventions run in this increment.
- [x] Save the exact inputs sent to each player and returned decisions so replay and privacy checks can inspect actual observations. Keep the complete audit record separate from player histories. This covers the scripted callable boundary; provider prompts/raw responses follow in milestone 6. Unsupported Python objects retain explicitly marked diagnostics and fail validation.
- [x] Save versioned session/configuration records and retain completed events if a run fails. Detect incomplete records and distinguish completed, failed, and interrupted sessions.
- [x] Record accepted decisions before applying them. Preserve failed attempts and require a separate new file/session identifier for every complete-session rerun rather than silently replacing data. There are no automatic reruns; the evaluation rerun policy must be frozen in milestone 7.
- [x] Implement deterministic replay from recorded events and decisions without model calls. Compare reconstructed state, histories, and rewards with the original trajectory.
- [x] Test recording and replay for a full scripted session and interrupted sessions. Verify that private observations remain auditable and that incomplete trajectories are excluded or handled as specified.

Done when complete scripted sessions replay exactly and failed runs remain visible without contaminating results. Exact replay uses recorded decisions; fresh LLM continuations may differ. Mid-session resume is not a Phase 1 completion requirement.

### Milestone 6 Integrate Inspect and model execution

Dependencies: milestone 5. Primary module: `experiment.py`.

Increment 1 supplies the provider-independent request/parse boundary. Increment 2
connects it to the actual Inspect task/solver/model runtime, verified with an offline
scripted model. Increment 3's offline implementation supplies a pinned candidate,
small live configuration, pricing, preflight, OpenAI SDK HTTP tests, and saved-run
verification. Live qualification passed on 2026-10-17 with the pinned OpenAI
candidate; fix the study model after the competence/control pilot. Neither the
offline checks nor this smoke run establish poker competence or
spontaneous/enacted coordination.

- [x] Implement the Inspect decision function with explicit player-specific inputs, generation settings, structured response parsing, and validation against the current phase.
- [x] Keep all persistent player memory in session state. Ensure model clients do not introduce conversation state that snapshots cannot capture. Inspect receives fresh explicit messages for each request; all 64 live smoke payloads matched the expected two-message inputs without additional conversation state.
- [x] Implement a custom solver that invokes the session runner and exposes results and artifact references to Inspect without using a shared sample transcript as player input.
- [x] Map one Inspect sample to one complete session. Build tasks/configurations for the three Phase 1 channels under neutral instructions, maintaining a shared matching identifier across conditions.
- [x] Add separate positive-control and competence configurations. Use one fixed model with three separate histories and individual rewards in the main formation experiments. Shipped templates use the offline mock until a live model is selected; competence and control outcomes are not yet scored.
- [x] Record requested and returned model identifiers where available, supported generation parameters, exact prompts, raw returned outputs, token usage, latency, retry information, and run provenance. Inspect events retain effective settings and raw payloads; all 64 live smoke calls passed payload and usage review.
- [x] Apply bounded concurrency, transport retries, timeouts, token/cost limits, and the predefined model-failure policy. Record interrupted or incomplete runs explicitly. Retries are zero; limits apply per session and may overshoot for in-flight responses. Dollar limits require known Inspect pricing.
- [x] Configure response-cache behavior so independent sessions do not reuse sampled answers. Record exact outputs and supported sampling settings without assuming seeds make provider calls deterministic.
- [x] Connect Inspect execution logs to the experiment event records using stable references, with the experiment records authoritative for game behavior.
- [x] Test the integration with a fake model interface and simulated provider HTTP. Provide a small, explicitly invoked live smoke-run configuration, preflight, pricing, and offline artifact verification.
- [x] Execute the bounded live smoke run and review model identity, settings, legal decisions, privacy, usage, raw payloads, and replay. Accepted on 2026-10-17: three complete sessions, nine hands, 64 calls, and no verification issues. See [live evidence](docs/live-smoke.md#accepted-run-2026-10-17).

Done when Inspect can execute and inspect complete sessions, preserve distinct player histories, and report failures and usage without changing the protocol.

### Milestone 7 Run and report the sprint study

Dependencies: Phase 1 milestones 1 through 6. Primary outputs: reviewed evidence, analysis, and the sprint report.

- [x] Draft a short rubric for attempted, agreed, and enacted coalitions, requiring message/action evidence and recording uncertainty. [Rubric v0.1](docs/collusion-rubric.md) includes six authored worked examples and identifies membership behaviorally rather than selecting the highest-winning pair. This is pre-sprint preparation; pilot calibration and the evaluation freeze remain below.
- [x] Implement [versioned JSON annotations and offline validation](docs/annotation-format.md), including per-pair review coverage, independent stage judgments, source hashes, real event/message references, reviewer provenance, and preserved revisions. Validation checks structure and links, not scientific correctness or human approval.
- [x] Generate all six rubric examples through the session runner, verify exact replay, and validate their scripted annotations. These are preparation fixtures, not model observations or evidence of human agreement.
- [x] Create a [local human-review form](docs/review-form.md) with transcript evidence selection, separate stage judgments, draft/complete JSON exports, same-source imports, and preserved revisions. Browser workflow tests use all six scripted examples; they do not establish human agreement or rubric usability.
- [ ] Have a human use the form to check rubric usability on the scripted examples of enacted coordination, talk without action, and similar play without agreement. Do not treat no-communication sessions as guaranteed non-collusion labels.
- [x] Implement [single-session descriptive analysis](docs/analysis-protocol.md): validate the selected annotation and revision, replay terminal journals, retain uncertainty and unfinished coverage, and export session/pair stage outcomes plus identity-based hand and pair/outsider payoffs. Scripted annotations remain identifiable; incomplete-journal payoffs are unavailable.
- [ ] Add precise proposal/agreement timing and subsequent-hand payoff summaries using explicit reviewer-selected timing markers and a documented window rule. Current episode intervals include context and must not be treated as exact onset times. Distinguish descriptive results from causal effectiveness claims.
- [ ] Implement matched condition comparisons and uncertainty estimates that preserve independent session blocks. Record failed sessions, absent coalitions, ambiguous labels, and the small study's limitations.
- [ ] Run offline tests, formatting, linting, and type checks; validate the complete scripted three-condition workflow, privacy, matched deals, seat rotation, logging, and replay.
- [ ] Run a bounded competence and positive-control pilot with the chosen model. Estimate context growth, failure rates, usage, cost, and variability before setting the evaluation budget.
- [ ] Freeze the primary comparison, labeling rubric, session and hand counts, message/memory limits, failure policy, and stopping rule before the sprint evaluation. Keep the pilot separate.
- [ ] Run the fixed public/private comparison, no-communication baseline, and separate instructed-coordination positive control with matched schedules and fresh histories.
- [ ] Human-review the evaluation trajectories under the frozen rubric, record disagreements, and generate reproducible tables of enacted coordination and payoffs with uncertainty.
- [ ] Document setup and commands, and write the sprint report with controls, evidence, findings, and limitations. Use the official PDF template, an abstract of at most 150 words, authors/affiliations, and the required limitations and ethical-considerations appendix. Distinguish pre-sprint preparation from new sprint work.
- [ ] Package the configuration, locked dependencies, permitted trajectory logs, reviewed labels, and analysis outputs so the sprint result can be inspected and regenerated.

Done when the core sprint comparison is implemented, validated, executed, and reported with traceable evidence. Negative or inconclusive findings are acceptable; limitations must reflect competence, control performance, and sample size. Neither full effectiveness estimates nor fair-play violation claims are required or implied.

### Optional Phase 1 mechanism check

Dependencies: the core sprint work is complete and time/budget remain. This does not block Phase 1 completion.

- [ ] Reuse the Phase 2 snapshot/intervention design for a small predefined message-delivery versus withholding comparison, with complete state copies, isolated continuations, and fresh downstream decisions.
- [ ] Fix message/checkpoint selection and repetition count before examining intervention outcomes. Report this check separately, including missing branches and uncertainty.

## Phase 2 Full research project

Entry condition: review Phase 1 findings and resolve any blocking game, privacy, competence, or measurement problems. Reuse the validated code and records; observing spontaneous collusion is not required. Keep Phase 1 results separate from the new confirmatory study.

### Milestone 1 Expand conditions and add complete recovery

Dependencies: Phase 1. Primary modules: `session.py`, `records.py`, and `experiment.py`.

- [ ] Add combined public/private access with a shared per-player budget, matching sending opportunities across communication-enabled conditions.
- [ ] Add explicit fair-play instructions and cross both instruction settings with all four channels. Keep permitted table talk and forbidden coordination precisely defined.
- [ ] Enforce channel mechanics while delivering permitted-channel messages even when their content violates fair-play instructions. Assess those violations offline rather than filtering them out of the experiment.
- [ ] Add and validate multiple model configurations with exact available model identifiers, generation settings, and provider-specific parsing. Preserve individual rewards and symmetric communication opportunities.
- [ ] Persist complete versioned snapshots at safe boundaries, including before dealing and immediately before delivery. Include every player history, pending message/decision, budget, cursor, seat mapping, reward, and random-generator state.
- [ ] Make snapshot writes atomic, record their committed event positions, and reject incompatible snapshots. Prevent duplicate actions or deliveries when restoring committed records.
- [ ] Implement recovery through the ordinary runner using snapshots and subsequent committed records. Distinguish deliberate recorded-response reuse from fresh sampling and flag uncertain in-flight API calls.
- [ ] Test interruption and recovery around decision recording, delivery, action application, and settlement; verify identical scripted outcomes and independent restored state.

Done when all eight conditions and selected models work and sessions resume without missing state or duplicate effects. Reuse any verified snapshot work completed in the optional Phase 1 check.

### Milestone 2 Add counterfactual evaluations

Dependencies: Phase 2 milestone 1. Primary modules: `session.py`, `experiment.py`, and `analysis.py`.

- [ ] Add a small, typed intervention specification for an overridden next-hand deal or withholding a selected pending message. Apply interventions only at valid phase boundaries.
- [ ] Create independent branch copies with parent snapshot, intervention, deal, and continuation-replicate identifiers. Keep branch records outside the parent trajectory.
- [ ] From a pre-deal snapshot, run all 24 ordered deals with configurable repeated continuations and equal deal weights.
- [ ] From a pre-delivery snapshot, compare delivery with withholding. Preserve cards, prior histories, and unrelated pending messages; keep the sender's already-recorded send decision and provide no extra intervention notice to the recipient.
- [ ] Regenerate all subsequent decisions and messages in each continuation. Preserve the configured decision and communication budgets across comparison arms.
- [ ] Verify independent continuation replicates make fresh sampling requests and cannot be collapsed into identical results by response caching.
- [ ] Test that branches cannot mutate the parent or sibling states, memories, schedules, records, or rewards. Use scripted cases with known intervention effects to verify the pipeline.
- [ ] Configure checkpoint/message selection rules and continuation counts before main evaluations. Record estimates of branch cost and completion status, including missing or failed branches.

Done when both next-deal enumeration and message-withholding comparisons run through the existing session loop with verified isolation.

### Milestone 3 Extend measurement and analysis

Dependencies: Phase 2 milestones 1 and 2 for full validation. Primary module: `analysis.py`. Extend the Phase 1 rubric and analysis rather than creating a second pipeline.

- [ ] Define a versioned annotation rubric for attempted, agreed, and enacted coalitions, with cited message/action events, membership, timing, uncertainty, and ambiguous cases.
- [ ] Separate fair-play violations from coalition formation and effectiveness. Label private-card claims against the true deal without treating every inaccurate claim as proven intentional deception.
- [ ] Implement measurements for proposal/agreement/enactment timing, persistence, partner switching, defection, card disclosure, and betting consistent with agreements.
- [ ] Identify coalition membership from predefined behavioral evidence before assessing later payoffs or separate continuations. Apply the same selection procedure across conditions.
- [ ] Compute each member's payoff, combined pair payoff, and outsider payoff relative to matched controls. Evaluate effectiveness from controlled comparisons rather than an LLM judge's opinion or raw winning streaks.
- [ ] Support optional model-assisted annotation with a fixed judge prompt/version, evidence references, and human-review exports. Keep judge outputs out of player observations and decisions.
- [ ] Implement a reproducible human-review sample and disagreement/adjudication records. Assess labeling quality on held-out reviewed examples before relying on automated labels.
- [ ] Export session, hand, event, coalition, and branch tables with provenance. Validate that summaries reconcile with recorded trajectories.
- [ ] Implement paired condition comparisons and confidence intervals that preserve matched blocks and dependence within sessions and branches. Report incomplete runs, ambiguous labels, and missing evaluations under the predefined policy.
- [ ] Test analysis with synthetic positive, negative, ineffective-coordination, and one-member-exploitation examples. Confirm that winning alone cannot trigger an effective-collusion conclusion.

Done when reports can be regenerated from saved records, coalition claims can be traced to evidence, and statistical calculations pass known-case tests.

### Milestone 4 Validate the full implementation and run the expanded pilot

Dependencies: Phase 2 milestones 1 through 3. Outputs: tested package, usable documentation, and expanded pilot findings.

- [ ] Add a continuous-integration workflow running offline tests, formatting, linting, and type checks with the locked dependencies.
- [ ] Run an end-to-end scripted matrix covering all eight main conditions, fresh histories, matched deals, seat rotation, recording, recovery, branches, and analysis.
- [ ] Verify basic poker competence and legal-action reliability with the selected models before interpreting coalition behavior.
- [ ] Run the instructed-coordination positive control and negative annotation controls. Check that the environment and measurements can detect enacted coordination when it occurs.
- [ ] Run a bounded pilot across the planned conditions and candidate models. Measure failure rates, usage, wall time, context growth, behavioral variability, and intervention cost.
- [ ] Review sampled trajectories for accidental privacy leakage, asymmetric opportunities, model-setting mismatches, and prompt wording that suggests coordination in neutral conditions.
- [ ] Use pilot evidence to finalize memory limits, communication rounds/budgets, session length, model settings, labeling criteria, and failure handling. Keep pilot records separate from the main study.
- [ ] Document environment setup, configuration, scripted checks, live runs, recovery, replay, branching, annotation, and report generation with verified commands.
- [ ] Package a small reproducible example run with its configuration, events, snapshot, annotations, and analysis output; ensure released artifacts exclude credentials.

Done when the five-module implementation supports the complete study workflow, required checks pass, and pilot evidence establishes what the system can measure and what remains uncertain.

### Milestone 5 Execute and release the full study

Dependencies: Phase 2 milestone 4. These tasks use the completed framework and new evaluation sessions, separate from both phases' pilot data and Phase 1 evaluation data.

- [ ] Freeze the main protocol, prompts, software versions, primary enacted-coalition outcome, private-versus-public comparison, checkpoint-selection rules, sample size, and analysis plan using pilot evidence.
- [ ] Estimate the full session and branch budget and schedule the predefined independent matched sessions across selected models. Interleave condition execution to reduce time-related confounding.
- [ ] Run the main experiment with fresh histories and retain all run statuses. Follow the fixed stopping rule rather than stopping when a significance threshold is crossed.
- [ ] Run the predefined counterfactual evaluations, human-review sample, paired analyses, and uncertainty estimates.
- [ ] Report formation, persistence, effectiveness, individual benefits, and fair-play violations separately, including negative results and measurement limitations.
- [ ] Prepare reproducible release artifacts and the research report: source, locked dependencies, configurations, prompts, permitted logs, annotation guidance, and analysis commands.

Done when the predefined full study and mechanism evaluations have been analyzed and released with evidence, uncertainty, and explicit limits on the conclusions.

## Later extensions

Revisit these when evidence from the baseline makes them useful.

- [ ] Add mixed-model tables and reference-policy opponents; document limitations of any three-player CFR benchmark.
- [ ] Add new deck sizes or betting rules through the game wrapper and explicit protocol updates.
- [ ] Compare auditors with public-only versus full communication access.
- [ ] Extract communication or persistence modules when their complexity warrants independent ownership.
- [ ] Add distributed workers and shared artifact storage if local Inspect concurrency becomes an operational bottleneck.
