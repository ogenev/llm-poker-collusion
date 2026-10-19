# Matched-session comparison v0.1

This offline layer reads saved Inspect experiments and explicitly selected
annotation files, calls the [single-session analyser](analysis-protocol.md),
and compares conditions within matched blocks. Inspect supplies the execution
records and model audit; it does not assign coalition labels or run a new model
for comparison. Human judgments come from the annotation workflow.

The default policy below is preparation infrastructure. The pilot, human rubric
calibration, evaluation sample size, stopping rule, and final analysis policy
still need to be fixed before the sprint evaluation. An output marked
`evaluation` does not certify that those decisions were made.

## Try the complete offline workflow

From the repository root, with the locked environment installed:

```sh
uv run --locked python scripts/generate_comparison_example.py \
  runs/preparation/comparison-example-001
uv run --locked python scripts/compare_sessions.py \
  runs/preparation/comparison-example-001/comparison.json \
  --output runs/preparation/comparison-example-001/report.json
```

The generator uses the existing Inspect mock and creates three matched blocks,
each with no/public/private communication and three hands. All initial seat
rotations appear. Players pass communication and check/call; complete scripted
negative reviews are supplied for this known fixture. Usage is synthetic.
The generator writes only into a new directory. It is a workflow demonstration,
not a human review, a model competence check, or research evidence.

The comparison command makes no model calls. It writes a new private JSON file
(mode `0600`) and refuses to overwrite an existing report. Exit code 0 means a
report was produced, even if no blocks qualify. Invalid inputs or an existing
output return exit code 2. Inspect uses local event-loop sockets and writable
XDG cache/data directories; comparison needs no provider credentials.

## Select real runs and reviews

Create a JSON manifest. Every path is relative to that manifest's directory
(absolute paths also work). For example:

```json
{
  "kind": "session_comparison",
  "version": 1,
  "dataset_role": "preparation",
  "reviewer_kind": "human",
  "bootstrap": {"replicates": 2000, "seed": 1729, "confidence": 0.95},
  "runs": [
    {
      "directory": "run-001",
      "reviews": [
        {
          "sample_id": "block-0-private",
          "annotation": "reviews/private-0.json",
          "previous": null
        },
        {
          "sample_id": "block-0-public",
          "annotation": "reviews/public-0-revised.json",
          "previous": "reviews/public-0-original.json"
        }
      ]
    }
  ]
}
```

`sample_id` is the existing Inspect sample ID. Its block/channel must agree with
the recorded metadata and journals. It is not a way to relabel a session.
Select at most one annotation per sample. For a revision, supply its exact
immediate predecessor. Selection is explicit; the tool does not choose the
latest file, average reviewers, or adjudicate disagreements.

All fields shown are required, and unknown fields and duplicate JSON keys are
errors. `reviews` can be empty. Omitting a review keeps that session unreviewed;
it does not remove the session from the dataset. A selected annotation file that
is absent is recorded as missing. A missing revision predecessor is an error.
An available review is validated against its journal using the existing rules;
if the session cannot be located, that review remains unvalidated and unused.

Use a separate manifest for each of `preparation`, `pilot`, and `evaluation`.
Pilot/evaluation label estimates require human reviews. Preparation can select
either human or scripted reviews. Other reviewer kinds remain visible but are
excluded from label estimates. Model judging is not supported by this policy.
Mock gameplay is permitted only in preparation. A dataset role is an explicit
declaration: software cannot determine when a real model run was intended as
pilot versus evaluation data. Keep those run directories separate yourself.

## Matching, completeness, and integrity

Each selected run must have a committed `run.jsonl` header. Its saved experiment
configuration enumerates **all planned samples**, including ones without
reviews or artifacts. Include every run from the planned dataset. The tool
cannot discover a run omitted from the manifest, and a completely absent run
header is an error rather than permission to guess its planned workload.

Available Inspect samples must have unique expected IDs, epoch 1, and matching
run/block/channel identities. Their saved schedules must match the configured
seed, hand count, and initial seat rotation, and every condition within a block
must have the same saved deals and rotations. Saved deals are authoritative;
the comparison never regenerates them using today's random generator.

Game journals are checked against the Inspect sample and replayed by the
single-session analyser. Complete model journals and Inspect events are checked
using the existing saved-sample verifier: linked decisions, prompts, settings,
raw outputs, and usage must agree. A failed verification check is not a missing
review. Broken hashes, wrong annotations, inconsistent identities/deals,
duplicate samples, and corrupted records stop the comparison.

Missing samples/journals, sessions that never started, and incomplete journals
remain in the output with exclusion reasons. With an unfinished run manifest
or missing Inspect index, all its planned samples remain unavailable. Orphaned
session directories are listed explicitly, but their identity is not guessed
and they are not counted as extra sessions. Resolve unlinked attempts before
interpreting a study report. Failed and interrupted journals retain the
single-session analyser's descriptive facts; partial totals do not qualify as
complete-session payoffs.

Across runs, the tool requires identical model settings, instructions, session
settings, limits, channel sets, and saved execution provenance. Seeds must be
unique across runs, and copied run IDs cannot inflate N. Controls need a
separate manifest because their instructions differ. Public and private must
both be planned; no communication is an optional baseline (absent baseline
comparisons are explicitly unavailable). Source/provenance differences require
separate reports, even when you think two versions are equivalent.

## Estimates and denominators

The primary estimate is **private minus public in the probability that a
session contains observed enacted coordination**. Each session contributes
one binary outcome per stage, using the existing stage rollup. Proposed and
accepted outcomes are separate, descriptive estimates. No logical staircase
is imposed on their labels, and no-communication sessions are never assigned
negative labels automatically.

A session qualifies for label estimates only when it has complete, verified
game and model evidence, all planned hands, the selected reviewer kind, complete
full-journal review coverage, and a resolved stage verdict. `observed` maps to
1 and `not_observed` to 0. `uncertain`, missing judgments/reviews, and draft or
partial coverage remain visible and are excluded from resolved estimates.
An observed episode can establish a positive session rollup alongside an
uncertain episode; both episode lists remain in the embedded analysis.

For a stage's paired estimate, **both members of a block must qualify**. The
report includes each included block's two values and difference, every excluded
block with reasons by condition, and planned/eligible/excluded denominators.
Condition summaries also retain raw verdict counts and statuses, including
nonqualifying reviews. Their resolved rates may have different denominators;
the paired estimate uses the shared eligible blocks. Excluding failures and
uncertain labels can bias results; this output does not solve missingness.

Payoff estimates use audited complete sessions independently of annotation
completion. They compare whole-session chip totals for A, B, C and each fixed
pair AB, AC, BC. All identities are retained; the tool never selects a pair
because it won or was labeled a coalition. The outsider is the remaining
player and its total equals minus the pair total. Per-hand values and pair
membership are available in each embedded session analysis. These are
descriptive condition differences, not post-agreement effects or causal
evidence that coordination helped.

## Uncertainty

For each metric and contrast, compute one left-minus-right difference per
eligible block. The estimate is their arithmetic mean. Resample those whole
blocks with replacement, preserving both sessions, and compute the mean for
each bootstrap replicate. Report the two percentile quantiles with linear
interpolation. The manifest records the random seed, confidence level, and
replicate count (100–10,000); the example uses 2,000 replicates and 95%.

No interval is reported with fewer than two eligible blocks. With identical
observed differences, bootstrap intervals have zero width; the report warns
that this does not establish certainty. Small or sparse samples can have poor
coverage. Block independence is an assumption that study design must justify;
unique seeds alone do not establish it. Hands, episodes, and overlapping pairs
are never extra independent observations. Baseline contrasts and payoff/stage
comparisons are descriptive, with no significance tests or multiplicity claim.

## Reproducible output and remaining work

The report is `session_comparison_analysis` version 1, policy version 0.1. It
embeds the explicit selection, experiment settings and their hash, run IDs and
execution provenance, all single-session analyses, exclusions, condition
summaries, and contrasts. The primary result is
`contrasts[0].estimates.enacted`; difference units are probability points
(multiply by 100 for percentage points). Payoff units are chips per session.

The `inputs` list hashes the exact bytes of the manifest, run manifests,
Inspect logs, linked journals, selected reviews, and predecessors read by the
comparison. Absent referenced files have null hashes. Inputs and inventories
are rechecked after analysis; use stable saved artifacts. Analysis source code
and runtime versions are also recorded. Given the same selection, bytes, code,
and runtime, output is deterministic. Moving the complete tree does not break
relative references or require the absolute paths recorded during execution.

Standalone HTML reporting, human usability testing, adjudication, precise
reviewer-selected onset markers, subsequent-hand payoff windows, and the live
pilot/evaluation remain separate work. This command does not modify annotation
files, submit Inspect scores, run a model judge, or create new model responses.
