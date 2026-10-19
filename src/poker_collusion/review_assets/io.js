async function digest(bytes) {
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}
function revisionInfo() {
  $("reviewer-id").disabled = !!previous;
  $("download-previous").hidden = !previous;
  $("revision-info").textContent = previous
    ? `Next export revises ${previous.review.annotation_id}. Keep its file (${previous.name}) for --previous validation. Reviewer identity is preserved.`
    : "New independent human review. No judgments are prefilled.";
}
function downloadBytes(bytes, name) {
  const url = URL.createObjectURL(new Blob([bytes], {type: "application/json"}));
  const anchor = el("a"); anchor.href = url; anchor.download = name;
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
function lock(value) {
  busy = value;
  // Prevent edits while hashing/importing so an asynchronous operation cannot
  // discard an intervening edit or record the wrong predecessor.
  document.querySelectorAll("button, input, select, textarea").forEach(node => { node.disabled = value; });
  if (!value) $("reviewer-id").disabled = !!previous;
}
async function importReview(file) {
  if (!file || busy) return;
  lock(true);
  try {
    const bytes = await file.arrayBuffer();
    const review = validateReview(strictJSON(new TextDecoder("utf-8", {fatal: true}).decode(bytes)));
    requireThat(review.reviewer.kind === "human",
      "This form resumes human reviews only. Scripted/model labels are not imported into human work. Start a blank independent review.");
    const sha256 = await digest(bytes);
    if (dirty && !confirm("Importing replaces unsaved form changes. Continue?")) return;
    pairs = clone(review.pair_reviews);
    for (const pair of pairs) for (const episode of pair.episodes) for (const stage of STAGES) episode[stage] ??= blankJudgment();
    previous = {review, sha256, name: file.name, bytes}; target = null; dirty = false;
    $("reviewer-id").value = review.reviewer.id;
    renderPairs(); revisionInfo();
    notice("Imported human review. Its next export will be a new revision. Validate earlier revision links separately with Python.");
  } catch (error) { notice(`Import failed: ${error.message}`, true); }
  finally { lock(false); $("import-review").value = ""; }
}
async function exportReview(status) {
  if (busy) return;
  lock(true);
  try {
    const review = serialize(status);
    const bytes = new TextEncoder().encode(JSON.stringify(review, null, 2) + "\n");
    const sha256 = await digest(bytes);
    const name = `review-${review.annotation_id}.${status}.json`;
    downloadBytes(bytes, name);
    previous = {review, sha256, name, bytes}; dirty = false; revisionInfo();
    notice(`Download requested: ${name}. Confirm it saved and keep it: the next export revises this file. Use “Download predecessor again” to retry a canceled download. Python validation still required.`);
  } catch (error) { notice(`Cannot export: ${error.message}. Drafts may leave a judgment entirely blank, but partially filled judgments need a verdict, explanation, and alternatives.`, true); }
  finally { lock(false); }
}
$("import-review").addEventListener("change", event => importReview(event.target.files[0]));
$("export-draft").addEventListener("click", () => exportReview("draft"));
$("export-complete").addEventListener("click", () => exportReview("complete"));
$("download-previous").addEventListener("click", () => {
  if (previous && !busy) downloadBytes(previous.bytes, previous.name);
});
$("reviewer-id").addEventListener("input", changed);
$("new-review").addEventListener("click", () => {
  if ((dirty || previous) && !confirm("Start a blank independent review? Download any changes you want to keep first.")) return;
  pairs = blankPairs(); previous = null; target = null; dirty = false;
  $("reviewer-id").value = ""; renderPairs(); revisionInfo();
  notice("New independent human review. All pairs are unreviewed.");
});
window.addEventListener("beforeunload", event => {
  if (dirty || busy) { event.preventDefault(); event.returnValue = ""; }
});
$("rubric-version").textContent = DATA.rubric.version;
$("source-summary").textContent = `Source: ${DATA.source.session_id} · ${DATA.source.status} · events 0–${LAST}`;
$("source-details").textContent = `SHA-256: ${DATA.source.sha256}\nSource status: ${DATA.source.status}\nUncommitted trailing bytes: ${DATA.trailing_bytes}\nThis page embeds the full audit journal. Source status and review completion are separate.`;
$("event-count").textContent = `${DATA.events.length} saved events`;
renderTranscript(); renderPairs();
if (!crypto.randomUUID || !crypto.subtle) {
  notice("This browser does not support local-file Web Crypto. Open the page in a current Chromium or Firefox browser.", true);
  lock(true);
}
