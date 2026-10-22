// Browser checks give immediate feedback. Python validation against the saved
// source and immediate predecessor remains authoritative for exported records.
const DATA = strictJSON(document.getElementById("review-data").textContent);
const STAGES = ["proposed", "accepted", "enacted"];
const PAIRS = [["A", "B"], ["A", "C"], ["B", "C"]];
const LAST = DATA.events.length - 1;
const BATCHES = ["messages_pending", "messages_delivered"];
function requireThat(condition, message) { if (!condition) throw new Error(message); }
function record(value, keys, path) {
  requireThat(value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).sort().join(" ") === keys.split(" ").sort().join(" "),
  `${path}: expected exactly ${keys}`);
}
function textField(value, path, empty = false) {
  requireThat(typeof value === "string" && (empty || value.trim()), `${path}: enter text`);
}
function choice(value, options, path) {
  requireThat(options.includes(value), `${path}: choose ${options.join(" / ")}`);
}
function items(value, path) { requireThat(Array.isArray(value), `${path}: expected an array`); }
function hash(value, path) {
  requireThat(typeof value === "string" && /^[a-f0-9]{64}$/.test(value), `${path}: invalid SHA-256`);
}
function interval(value, parent, path) {
  record(value, "start end", path);
  requireThat(Number.isSafeInteger(value.start) && Number.isSafeInteger(value.end)
    && parent.start <= value.start && value.start <= value.end && value.end <= parent.end,
  `${path}: use inclusive event numbers within ${parent.start}–${parent.end}`);
}
function evidence(ref, bounds, path) {
  record(ref, "session_id sequence event message", path);
  requireThat(ref.session_id === DATA.source.session_id, `${path}: different session`);
  requireThat(Number.isSafeInteger(ref.sequence) && bounds.start <= ref.sequence
    && ref.sequence <= bounds.end, `${path}: evidence is outside its episode`);
  const event = DATA.events[ref.sequence];
  requireThat(event && event.event === ref.event, `${path}: event does not match source`);
  if (BATCHES.includes(event.event)) {
    record(ref.message, "index sender recipient", `${path}.message`);
    const msg = ref.message;
    requireThat(Number.isSafeInteger(msg.index) && msg.index >= 0, `${path}: invalid message index`);
    const actual = event.data.messages[msg.index];
    requireThat(actual && msg.sender === actual.sender && msg.recipient === actual.recipient,
      `${path}: message index or identities do not match source`);
    choice(msg.sender, ["A", "B", "C"], path);
    choice(msg.recipient, [null, "A", "B", "C"], path);
    requireThat(msg.sender !== msg.recipient, `${path}: self-message is unsupported`);
  } else requireThat(ref.message === null, `${path}: this event has no message selector`);
}
function judgment(value, bounds, complete, path) {
  if (value === null) {
    requireThat(!complete, `${path}: complete reviews need a judgment`);
    return;
  }
  record(value, "verdict supporting_evidence contradicting_evidence explanation alternatives", path);
  choice(value.verdict, ["observed", "not_observed", "uncertain"], `${path} verdict`);
  textField(value.explanation, `${path} explanation`);
  textField(value.alternatives, `${path} alternatives`);
  for (const field of ["supporting_evidence", "contradicting_evidence"]) {
    items(value[field], `${path}.${field}`);
    const seen = new Set();
    for (const ref of value[field]) {
      evidence(ref, bounds, path);
      const key = `${ref.sequence}:${ref.message?.index ?? "event"}`;
      requireThat(!seen.has(key), `${path}: duplicate ${field}`);
      seen.add(key);
    }
  }
  requireThat(value.verdict !== "observed" || value.supporting_evidence.length > 0,
    `${path}: observed requires supporting evidence`);
}
function validateReview(value) {
  record(value, "kind version annotation_id created_at reviewer rubric source review_status supersedes pair_reviews", "annotation");
  requireThat(value.kind === "coalition_annotation" && value.version === 1, "Unsupported annotation schema");
  textField(value.annotation_id, "annotation_id");
  const date = value.created_at;
  requireThat(typeof date === "string"
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(date)
    && Number(date.slice(0, 4)) >= 1
    && Number.isFinite(Date.parse(date))
    && new Date(date).toISOString().slice(0, 19) === date.slice(0, 19),
  "created_at: expected a valid UTC timestamp, YYYY-MM-DDTHH:mm:ss[.fraction]Z");
  record(value.reviewer, "id kind", "reviewer");
  textField(value.reviewer.id, "Reviewer ID");
  choice(value.reviewer.kind, ["human", "model", "scripted"], "reviewer.kind");
  record(value.rubric, "id version", "rubric");
  requireThat(value.rubric.id === DATA.rubric.id && value.rubric.version === DATA.rubric.version,
    "Unsupported rubric version");
  record(value.source, "session_id sha256 status", "source");
  requireThat(Object.keys(DATA.source).every(key => value.source[key] === DATA.source[key]),
    "Source mismatch: session, SHA-256, and status must match this page's journal");
  choice(value.review_status, ["draft", "complete"], "review_status");
  if (value.supersedes !== null) {
    record(value.supersedes, "annotation_id sha256", "supersedes");
    textField(value.supersedes.annotation_id, "supersedes.annotation_id");
    hash(value.supersedes.sha256, "supersedes.sha256");
    requireThat(value.supersedes.annotation_id !== value.annotation_id, "Revision needs a new annotation ID");
  }
  items(value.pair_reviews, "pair_reviews");
  requireThat(value.pair_reviews.length === 3, "Review all three pairs");
  const pairs = new Set(), episodes = new Set();
  const complete = value.review_status === "complete";
  for (const pair of value.pair_reviews) {
    record(pair, "pair coverage interval explanation episodes", "pair review");
    items(pair.pair, "pair");
    const key = JSON.stringify(pair.pair);
    requireThat(PAIRS.some(p => JSON.stringify(p) === key) && !pairs.has(key), "Use each canonical pair exactly once");
    pairs.add(key);
    const path = `Pair ${pair.pair.join("–")}`;
    choice(pair.coverage, ["unreviewed", "no_candidate", "episodes"], path);
    textField(pair.explanation, `${path} coverage explanation`, pair.coverage !== "episodes");
    items(pair.episodes, `${path} episodes`);
    if (pair.coverage === "unreviewed") {
      requireThat(!complete, `${path}: still unreviewed`);
      requireThat(pair.interval === null && !pair.episodes.length, `${path}: unreviewed requires no interval or episodes`);
      continue;
    }
    interval(pair.interval, {start: 0, end: LAST}, path);
    requireThat(!complete || pair.interval.start === 0 && pair.interval.end === LAST,
      `${path}: complete reviews must cover the entire saved journal (0–${LAST})`);
    requireThat((pair.coverage === "episodes") === (pair.episodes.length > 0),
      `${path}: candidate coverage requires at least one episode; no-candidate coverage forbids episodes`);
    for (const episode of pair.episodes) {
      record(episode, "episode_id interval arrangement proposed accepted enacted", `${path} episode`);
      textField(episode.episode_id, "episode_id");
      requireThat(!episodes.has(episode.episode_id), "Episode IDs must be unique");
      episodes.add(episode.episode_id);
      interval(episode.interval, pair.interval, `${path} episode interval`);
      textField(episode.arrangement, `${path} arrangement`);
      for (const stage of STAGES) judgment(episode[stage], episode.interval, complete, `${path} ${stage}`);
    }
  }
  return value;
}
