# Human usability check

Do this **after** the [technical walkthrough](workflow-walkthrough.md). Use its
`POKER_CHECK_DIR` directory, generated forms, and reports. The goal is to find
confusing wording, lost work, difficult evidence selection, and misleading
report presentation before the pilot. You are testing the tools with authored
preparation examples, not establishing reviewer agreement or model behavior.

This is a manual task for a person. Automated browser tests do not complete it.
Read the full [provisional rubric](collusion-rubric.md) first. Assign your own
judgments; do not import or relabel the supplied scripted annotations as human.
The example names and prior walkthrough reveal their intended themes, so this
is not a blinded assessment of labeling accuracy.

## 1. Start a short observation log

In `$POKER_CHECK_DIR/check-results.md`, record your reviewer ID, date, code
commit, OS/browser, and whether you needed help. Use a row for each task:

| Task / artifact | Pass, fail, or not run | Time / help needed | Confusion or error | Suggested change |
| --- | --- | --- | --- | --- |
| Read recorded player view | | | | |
| Cite supporting and contradicting evidence | | | | |
| Save draft, reopen, export revision | | | | |
| Validate and analyse saved review | | | | |
| Select matched human reviews and render report | | | | |
| Explain report denominators and exclusions | | | | |

Use **blocker** for lost work, inability to finish, or misleading results;
**friction** for a task that works but is hard to understand. Capture the exact
button/field, example name, and event number when something is confusing.

## 2. Practice reading the transcript and making judgments

Open these files under `forms/rubric/`, in this order:

| Form | What to try |
| --- | --- |
| `01-ordinary-play.html` | Explain why similar actions alone do or do not justify a candidate arrangement. |
| `04-information-exchange.html` | Follow an offer, the recipient's access to it, and later messages/actions. |
| `03-unexecuted-agreement.html` | Judge proposal, acceptance, and enactment separately. |
| `06-ambiguous-play.html` | Record uncertainty where the evidence leaves an unresolved question. |
| `02-rejected-proposal.html` | Optional extra: use contradicting evidence for a claimed agreement. |
| `05-preferential-betting.html` | Optional extra: connect a betting action to a proposed arrangement. |

For each of the first four:

1. Enter your reviewer ID. Confirm all three pairs initially say **Unreviewed**.
2. Read the whole transcript. Expand a **recorded view** and explain what that
   player knew at that decision. Distinguish the player's information from audit
   cards, other players' views, pending messages, and later deliveries.
3. Review A–B, A–C, and B–C. Choose **Reviewed — no candidate** or
   **Reviewed — candidate episodes**, and explain why. Complete pair coverage
   must run from event `0` through the last saved event; the form initially fills
   that interval when a pair becomes reviewed. Check it against the source.
4. For a candidate, describe the arrangement and set its inclusive episode
   interval. For each stage, choose a verdict, explain it, and consider plausible
   independent play, error, or coincidence. Observed needs supporting evidence.
5. Click **Choose evidence** for the relevant stage. Pick **Supporting** or
   **Contradicting**, then **Cite event** or **Cite message** in the transcript.
   Follow the resulting reference back, remove one, and add it again. Check the
   sender, recipient, event number, and message index. Keep citations inside the
   episode interval. Add contradicting evidence only when it is relevant.
6. On the ambiguous case, check whether you can record the unresolved issue
   clearly. A complete review may contain **Uncertain**; completion does not
   require forcing a yes/no answer.

Before looking at the supplied `.annotation.json` files, write down what was
hard to decide or express. You may then compare your reasoning with the authored
examples. A disagreement is a calibration question, not automatically a software
bug or a reason to change your answer.

## 3. Test save, resume, and revision on the ambiguous case

Use `forms/rubric/06-ambiguous-play.html` for this lifecycle check. If you have
already exported from this form, preserve those files and use **New blank review**
to begin a separate check; an imported/exported review already has a predecessor.

1. Start an independent review with your ID. Fill one pair's coverage and some
   judgments, leaving other pairs unreviewed. For a partially filled judgment,
   either complete its verdict/explanation/alternatives or leave it entirely
   empty. An observed judgment still needs evidence in a draft.
2. Click **Download draft JSON** once. Check the download exists. Copy its exact
   bytes to `human/ambiguous-draft.json` under the check directory. Keep the
   original download too; do not open and re-save JSON in an editor.
3. Close and reopen the HTML. It should be blank: **there is no autosave**. Click
   **Import human review** and select the draft. Verify all notes, intervals,
   evidence, and your reviewer ID are restored. The revision identity is locked.
4. Finish reviewing all three pairs and all candidate stages, keeping uncertainty
   wherever justified. Click **Download complete JSON** once. Preserve it as
   `human/ambiguous-complete.json`. It should reference your draft as predecessor.
5. Use **Download predecessor again** if you need another copy of that exact
   predecessor. Every regular export creates a new revision, so if you exported
   more than twice, use the actual immediate predecessor in the commands below.
6. Import the complete review to inspect it without exporting again. Attempt to
   import the supplied scripted annotation, or a review of another source.
   Expect an error and the current review to remain intact.

The file aliases above are for the commands; copying/renaming preserves identity
because hashes bind the file bytes. Avoid creating several different files with
the same alias. Keep earlier revisions.

Validate and analyse your downloads from the repository terminal:

```sh
uv run --locked python scripts/validate_annotation.py \
  "$POKER_CHECK_DIR/human/ambiguous-draft.json" \
  --log "$POKER_CHECK_DIR/rubric/06-ambiguous-play.jsonl"
uv run --locked python scripts/validate_annotation.py \
  "$POKER_CHECK_DIR/human/ambiguous-complete.json" \
  --log "$POKER_CHECK_DIR/rubric/06-ambiguous-play.jsonl" \
  --previous "$POKER_CHECK_DIR/human/ambiguous-draft.json"
uv run --locked python scripts/analyze_session.py \
  "$POKER_CHECK_DIR/rubric/06-ambiguous-play.jsonl" \
  --annotation "$POKER_CHECK_DIR/human/ambiguous-complete.json" \
  --previous "$POKER_CHECK_DIR/human/ambiguous-draft.json" \
  --output "$POKER_CHECK_DIR/human/ambiguous.analysis.json"
```

Expected: both validations succeed with `reviewer_kind: human`; analysis reports
`replay_verified: true` and a complete human review. Inspect the JSON's `review`,
`pairs`, and `outcomes`: your explanations, alternatives, citations, uncertainty,
and predecessor are retained. Outcomes follow the documented
[stage aggregation](analysis-protocol.md#stage-aggregation-rules); automation
does not reconsider your judgment. Validation checks structure/links, not truth.

## 4. Follow two actual human reviews into a comparison report

The rubric examples cannot be batched as matched study data. Instead, use these
two matched forms from the walkthrough:

- `forms/matched/block-0-private.html`
- `forms/matched/block-0-public.html`

Review the full three-hand transcript in each. Make independent human judgments
for all three pairs. Do not assume a negative merely from the channel or the
fixture description. Start blank and export **one complete review per form**,
without a preceding draft, for this minimal example. Preserve the downloads as
`human/block-0-private.json` and `human/block-0-public.json`.

If you instead use revisions, retain and validate their predecessors, and supply
the relative predecessor paths in the manifest below instead of `None`.
`session-index.json` maps each sample ID to its exact log and form.

This command validates both reviews, then creates a new explicit selection
manifest alongside the scripted one. It selects only the two files you named;
the other seven planned sessions remain in the report as unreviewed.

```sh
uv run --locked python - <<'PY'
import json
import os
from pathlib import Path
from poker_collusion.annotation_validation import validate_annotation
from poker_collusion.annotations import read_annotation
from poker_collusion.durable_jsonl import DurableJsonl

root = Path(os.environ["POKER_CHECK_DIR"])
base = root / "matched"
index = json.loads((root / "session-index.json").read_text())
manifest = json.loads((base / "comparison.json").read_text())
manifest["reviewer_kind"] = "human"
selected = []
# For revisions, replace None with each immediate predecessor path,
# relative to matched/, e.g. "../human/block-0-private-draft.json".
predecessors = {"block-0-private": None, "block-0-public": None}
for sample, previous in predecessors.items():
    annotation = root / "human" / f"{sample}.json"
    previous_path = None if previous is None else base / previous
    review = read_annotation(annotation)
    assert review.reviewer.kind == "human" and review.review_status == "complete"
    validate_annotation(review, root / index[sample]["log"], previous_path=previous_path)
    selected.append({"sample_id": sample, "annotation": f"../human/{sample}.json",
                     "previous": previous})
manifest["runs"][0]["reviews"] = selected
with DurableJsonl(base / "comparison-human.json") as output:
    output.write(manifest)
print("Validated two complete human reviews and saved comparison-human.json")
PY
uv run --locked python scripts/compare_sessions.py \
  "$POKER_CHECK_DIR/matched/comparison-human.json" \
  --output "$POKER_CHECK_DIR/matched/report-human.json"
uv run --locked python scripts/render_report.py \
  "$POKER_CHECK_DIR/matched/report-human.json" \
  --review-pages "$POKER_CHECK_DIR/matched/review-pages.json" \
  --output "$POKER_CHECK_DIR/matched/report-human.html"
```

Open `matched/report-human.html`. Expected: preparation/mock, nine planned
sessions, two selected human reviews, and seven unreviewed sessions. If both
enacted judgments resolve to observed/not-observed, there is **one eligible
primary block out of three**, with no interval because N is less than two.
If either remains uncertain, that block is excluded too. The point estimate
follows your judgments; do not change labels to achieve an expected number.
Payoff comparisons still use all three audited blocks.

Use **View** on either selected session, then **Open source review page**.
The link opens its transcript with a blank form. Import the selected human JSON
to see your review; the report link does not preload it. Compare the annotation
ID/hash and any evidence references with the report details.

## 5. Check whether the reports are understandable

Use `matched/report.html`, `report-partial.html`, `report-unreviewed.html`, and
your new `report-human.html`. First try these tasks without consulting the
expected-results table in the technical guide; record where you needed help.

- Find the dataset role, gameplay kind, reviewer kind, planned sessions, and
  planned blocks. Explain why these are preparation checks rather than findings.
- Explain the sign of private-minus-public and what `pp` means. Identify the
  shared denominator used by the two primary rates. Explain why nine sessions
  and 27 hands do not give nine or 27 independent matched blocks.
- In the partial report, find the omitted review, its stage exclusions, and why
  its audited payoff can still contribute. Distinguish unknown, uncertain, and
  not observed. The authored ambiguous analysis supplies an uncertain example;
  the passive comparison fixtures do not manufacture uncertain judgments.
- In the unreviewed report, confirm the missing estimate says unavailable and
  has no fake zero point. In the complete scripted report, find the zero-width
  interval warning. Explain why neither display establishes scientific certainty.
- Filter by private channel, search for `block-0`, then search for nonsense.
  Watch only the session list change; primary rates, intervals, and denominators
  must stay fixed. Reset filters and recover all nine rows.
- Open a session's **View** panel. Find its source hash, review identity, stage
  outcomes, exclusions, and fixed-pair payoffs. Follow the source-page link.
  Where your review contains an episode, follow its explanations and citations.
- Resize to a narrow window, use keyboard Tab to reach controls, and use
  **Print report**. Check readable labels, visible focus, and no clipped main
  content. Wide tables may scroll within their panels. Print includes visible
  report sections and expanded details; the interactive session table is omitted.

The nine-session fixture has one page and no failed gameplay. Record pagination
and failed-session manual checks as **not exercised**, not passed. The optional
browser suite tests those cases, larger lists, and synthetic uncertainty.

## 6. Decide what needs fixing before the pilot

The first usability pass is complete when you can:

- Review the four core examples and explain each stage separately.
- Select and revisit evidence, save/resume without lost work, and validate a
  complete human review with its revision predecessor.
- Trace two actual matched human reviews into a report with explicit selection.
- Explain its denominators, exclusions, uncertainty, and fixed filter behavior.
- Record blockers, friction, unresolved rubric questions, and tasks not run.

Fix blockers and repeat the affected tasks; keep earlier artifacts and notes.
Do not mark the project's human-usability TODO complete until a person has done
the tasks and recorded the outcome. A usable form does not establish reliable
labels: pilot calibration, independent reviewer comparison/adjudication policy,
and the frozen evaluation plan remain separate research work.
