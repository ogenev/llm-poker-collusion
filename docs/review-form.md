# Local human-review form

The standalone HTML form implements the [annotation format](annotation-format.md)
and supports the provisional [coalition rubric v0.2](collusion-rubric.md). It runs
without a server, account, model call, or external browser assets. The reviewer
assigns every judgment; the page checks fields and evidence references.

## Generate and open

From the repository root, generate a page for a stable saved journal:

```sh
uv run --locked python scripts/generate_review_page.py \
  runs/preparation/annotation-examples-001/06-ambiguous-play.jsonl \
  --output runs/preparation/ambiguous-review.html
```

If those preparation examples do not exist, first run the example-generation
command in the [annotation workflow](annotation-format.md#generate-and-validate-examples).
Use a new output filename each time; the generator never overwrites an existing
file. It exits 0 with a JSON result on success, or 2 with a JSON error. The HTML
file is created with mode 0600 and contains the source journal, including audit
information. Keep it with the same care as the journal itself.

Open the generated file in a current Chromium or Firefox browser. No Python
process needs to remain running. The page uses Web Crypto for annotation IDs and
revision hashes. Managed browsers may prohibit local-file navigation; the form
reports missing Web Crypto support if the browser does not provide it.

## Review a session

1. Read the full rubric and the transcript. Expand a **recorded view** for the
   information available to that player. Audit cards and other players' views
   are extra information for the reviewer. “Show all journal events” includes
   pending batches and decision lifecycle events.
2. Choose **No candidate** or **Possible coordination** for A–B, A–C, and B–C.
   All three start unanswered. No candidate needs no text or other input.
3. Possible coordination opens one card. Describe what the players were trying
   to do together, then independently answer **Was a shared plan proposed?**,
   **Was it accepted?**, and **Was it carried out?** with **Yes / No / Unsure**.
4. Give one short **Why?** explanation for each answer, including plausible
   alternatives such as ordinary play, error, or coincidence. For Unsure,
   explain the unresolved issue. Yes needs supporting evidence.
5. Click **Attach evidence** beside the relevant answer, then **Cite event** or
   **Cite message** in the transcript. Use the evidence-type selector for
   contradicting evidence. References retain the event, message index, sender,
   and recipient, and can be revisited or removed.
6. Enter your reviewer ID near the save buttons, confirm **I reviewed the whole
   transcript for all three pairs**, and choose **Finish review**.

There are no event-range inputs or coverage explanations. Each arrangement is
assessed over the whole saved session. Citations identify specific evidence;
these reviews do not measure precise onset or duration. For another distinct
arrangement involving the same pair, use **More options → Add another
arrangement**. One arrangement can span several hands and has all three stages.

Switching back to No candidate removes an untouched card immediately. If it
contains work, an inline prompt offers **Discard and switch** or **Keep
arrangements**. **More options → Clear choice** resets a pair to unanswered with
the same protection. Removing an extra arrangement also uses an inline prompt,
so embedded previews do not depend on native confirmation dialogs for these actions.

The form does not infer acceptance from message order, enactment from a matching
action, or coordination from payoffs. These are human interpretations under the
rubric. The browser's recorded-view display does not replay game semantics.

## Save, resume, and revise

**Save draft** downloads a valid unfinished review. A completely empty judgment
becomes `null`. Once an answer contains notes or evidence, fill its verdict and
Why before saving; Yes still needs supporting evidence. An arrangement needs a
description. Invalid partial work stays in the form with an error; it is never
silently dropped. Unanswered pairs and entirely blank judgments are allowed.

**Finish review** additionally requires every pair answered, all three answers
per arrangement, and the whole-transcript confirmation. Completion does not
require certainty or a completed source session. Source status stays attached.

The page does not autosave or write directly to your journal or annotation files.
Download before closing; the browser will normally warn about unsaved edits.
Confirm that the download actually saved. Every export creates a new annotation
ID and filename. After the first export, subsequent exports link to the preceding
download's ID and exact byte hash. **Download predecessor again** retries that
download without changing its bytes or creating another revision. Keep every
file needed for the revision chain.

To resume, open **Saved reviews → Import human review** in the same HTML. The page checks its
schema, rubric version, source session/hash/status, and evidence links before
replacing the current form. It preserves the reviewer identity, episode IDs, and
judgments; the next export links to the imported file's exact bytes. Reviewer
identity is locked for revisions. These are declared identities, not authentication.

Scripted and model reviews are rejected by this human-only form. For an independent
review, use **New blank review** and assign your own judgments. A wrong-source or
malformed import leaves the current review intact. Imported revision chains still
need separate Python validation against their predecessor files.

This form uses annotation schema v2 and rubric v0.2. Old-format reviews are not
supported or migrated. Start new reviews after regenerating the HTML; generate
new scripted annotation examples and comparison reports for preparation checks.
Imports of new reviews must use whole-session pair and arrangement intervals.

Generated HTML files embed the form code and do not update automatically.
Regenerate from a saved source journal into a new HTML filename after updating.

Validate downloads before analysis:

```sh
uv run --locked python scripts/validate_annotation.py REVIEW.json --log SESSION.jsonl

# If the exported review has a non-null supersedes field:
uv run --locked python scripts/validate_annotation.py REVISION.json \
  --log SESSION.jsonl --previous PREVIOUS_REVIEW.json
```

The Python validator remains authoritative for structure, source binding, and
the immediate revision link. Neither it nor the form validates the scientific
correctness of the judgments. Human usability review, calibration, disagreement
handling, and analysis remain separate work.

To combine a selected review with verified game facts, use the
[single-session analyser](analysis-protocol.md). It produces JSON stage summaries
and descriptive payoffs while preserving your judgments, uncertainty, and revision.

## Development checks

Python tests cover source embedding, script escaping, private/exclusive output,
incomplete journals, and CLI failures. Browser tests fill all six authored
scenarios, export drafts and complete reviews, reopen revisions, reject invalid
imports, preserve uncertain labels, and check mobile layout. Python validates
every browser export and its predecessor. All browser reviewer identities are
automated test fixtures, not empirical human reviews.

The browser suite is opt-in and requires Node, the `playwright` package, and
Chromium. These are development dependencies only; generated pages need none of
them. Install Playwright separately, then run:

```sh
npm install --prefix /tmp/poker-review-tools playwright
NODE_PATH=/tmp/poker-review-tools/node_modules \
CHROMIUM_PATH=/usr/bin/chromium POKER_REVIEW_BROWSER=1 \
uv run --locked pytest -q tests/test_review_browser.py
```

Adjust `CHROMIUM_PATH` for the installed browser, or omit it to use a browser
installed by Playwright. In managed test environments that prohibit `file://`,
set `POKER_REVIEW_BROWSER_HTTP=1`: Playwright fulfills the exact generated HTML
at a localhost URL without a running server. That checks the interface and JSON
workflow, but does not establish that the managed browser permits opening local
files. Unexpected page network requests fail the browser test.
