const $ = id => document.getElementById(id);
const clone = value => JSON.parse(JSON.stringify(value));
const uid = () => crypto.randomUUID();
const whole = () => ({start: 0, end: LAST});
const blankJudgment = () => ({verdict: "", supporting_evidence: [], contradicting_evidence: [], explanation: "", alternatives: ""});
const blankPairs = () => PAIRS.map(pair => ({pair: [...pair], coverage: "unreviewed", interval: null, explanation: "", episodes: []}));
const blankEpisode = bounds => ({episode_id: uid(), interval: {...bounds}, arrangement: "", ...Object.fromEntries(STAGES.map(stage => [stage, blankJudgment()]))});
let pairs = blankPairs();
let previous = null;
let target = null;
let dirty = false;
let busy = false;
function notice(message, error = false) {
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
}
function changed() { dirty = true; }
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, action) {
  const node = el("button", text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function labeled(text, control) {
  const label = el("label", text);
  label.append(control);
  return label;
}
function select(options, value, action) {
  const node = el("select");
  for (const [key, label] of options) {
    const option = el("option", label); option.value = key; node.append(option);
  }
  node.value = value;
  node.addEventListener("change", () => { action(node.value); changed(); });
  return node;
}
function textarea(object, key) {
  const node = el("textarea"); node.value = object[key]; node.dataset.field = key;
  node.addEventListener("input", () => { object[key] = node.value; changed(); });
  return node;
}
function rawDetails(label, data, audit = false) {
  const node = el("details", undefined, audit ? "audit" : "");
  node.append(el("summary", label), el("pre", JSON.stringify(data, null, 2)));
  return node;
}
function reference(event, index = null) {
  const message = index === null ? null : event.data.messages[index];
  return {session_id: DATA.source.session_id, sequence: event.sequence, event: event.event,
    message: message === null ? null : {index, sender: message.sender, recipient: message.recipient}};
}
function refLabel(ref) {
  return `#${ref.sequence} ${ref.event}` + (ref.message === null ? "" : ` [${ref.message.index}] ${ref.message.sender} → ${ref.message.recipient ?? "all"}`);
}
function refreshTarget() {
  document.querySelectorAll(".judgment").forEach(node => {
    node.classList.toggle("active", !!target && node.dataset.episode === target.episode.episode_id && node.dataset.stage === target.stage);
  });
  $("citation-target").textContent = target
    ? `${target.pair.pair.join("–")} · episode ${target.pair.episodes.indexOf(target.episode) + 1} · ${target.stage}`
    : "Select a judgment's “Choose evidence” button, then cite events here.";
}
function cite(ref) {
  if (!target) { notice("Choose a judgment in the review panel before citing evidence.", true); return; }
  try { evidence(ref, target.episode.interval, "Selected evidence"); }
  catch (error) { notice(error.message, true); return; }
  const field = $("evidence-kind").value;
  const refs = target.episode[target.stage][field];
  if (refs.some(item => item.sequence === ref.sequence && item.message?.index === ref.message?.index)) {
    notice("This reference is already in the selected evidence list."); return;
  }
  refs.push(ref); changed(); renderEvidence(target.episode, target.stage);
  notice(`Added ${field === "supporting_evidence" ? "supporting" : "contradicting"} evidence: ${refLabel(ref)}`);
}
function serialize(status) {
  const result = clone(pairs);
  for (const pair of result) for (const episode of pair.episodes) for (const stage of STAGES) {
    const judgment = episode[stage];
    // Only a completely empty judgment becomes null. Never drop unfinished notes
    // or evidence: validation instead explains which fields still need filling.
    if (!judgment.verdict && !judgment.explanation && !judgment.alternatives
      && !judgment.supporting_evidence.length && !judgment.contradicting_evidence.length) episode[stage] = null;
  }
  const now = new Date().toISOString();
  return validateReview({kind: "coalition_annotation", version: 1, annotation_id: uid(),
    created_at: previous && Date.parse(previous.review.created_at) >= Date.parse(now) ? previous.review.created_at : now,
    reviewer: previous ? clone(previous.review.reviewer) : {id: $("reviewer-id").value, kind: "human"},
    rubric: clone(DATA.rubric), source: clone(DATA.source), review_status: status,
    supersedes: previous ? {annotation_id: previous.review.annotation_id, sha256: previous.sha256} : null,
    pair_reviews: result});
}
