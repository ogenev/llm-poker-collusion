function intervalControls(bounds) {
  const node = el("div", undefined, "interval");
  for (const field of ["start", "end"]) {
    const input = el("input"); input.type = "number"; input.min = "0"; input.max = String(LAST);
    input.step = "1"; input.value = String(bounds[field]); input.dataset.bound = field;
    input.addEventListener("input", () => { bounds[field] = input.value === "" ? null : Number(input.value); changed(); });
    node.append(labeled(`Event ${field} (inclusive)`, input));
  }
  return node;
}
function renderEvidence(episode, stage) {
  const container = [...document.querySelectorAll("[data-evidence]")]
    .find(node => node.dataset.evidence === `${episode.episode_id}:${stage}`);
  if (!container) return;
  container.replaceChildren();
  for (const field of ["supporting_evidence", "contradicting_evidence"]) {
    container.append(el("strong", field === "supporting_evidence" ? "Supporting evidence" : "Contradicting evidence"));
    const refs = episode[stage][field];
    if (!refs.length) container.append(el("span", "None selected", "hint"));
    refs.forEach((ref, index) => {
      const row = el("div", undefined, "evidence-row");
      row.append(button(refLabel(ref), () => jumpTo(ref)), button("Remove", () => {
        refs.splice(index, 1); changed(); renderEvidence(episode, stage);
      }));
      container.append(row);
    });
  }
}
function judgmentForm(pair, episode, stage) {
  const judgment = episode[stage];
  const node = el("fieldset", undefined, "judgment");
  node.dataset.episode = episode.episode_id; node.dataset.stage = stage;
  node.append(el("legend", stage[0].toUpperCase() + stage.slice(1)));
  const verdict = select([["", "Not yet judged"], ["observed", "Observed"], ["not_observed", "Not observed"], ["uncertain", "Uncertain"]],
    judgment.verdict, value => { judgment.verdict = value; });
  verdict.dataset.field = "verdict";
  node.append(labeled("Judgment", verdict), button("Choose evidence", () => {
    target = {pair, episode, stage}; refreshTarget(); notice("Select supporting or contradicting evidence, then cite a transcript event or message.");
  }));
  const refs = el("div", undefined, "evidence-list"); refs.dataset.evidence = `${episode.episode_id}:${stage}`;
  node.append(refs, labeled("Explanation — why this judgment?", textarea(judgment, "explanation")),
    labeled("Plausible alternatives or why none fits", textarea(judgment, "alternatives")));
  return node;
}
function episodeForm(pair, episode, index) {
  const node = el("section", undefined, "episode"); node.dataset.episode = episode.episode_id;
  const heading = el("div", undefined, "episode-heading");
  heading.append(el("h3", `Episode ${index + 1}`), button("Remove episode", () => {
    if (!confirm("Remove this episode and all of its judgments and evidence?")) return;
    pair.episodes.splice(pair.episodes.indexOf(episode), 1);
    if (target?.episode === episode) target = null;
    changed(); renderPairs();
  }));
  node.append(heading, intervalControls(episode.interval), labeled("Arrangement being assessed", textarea(episode, "arrangement")));
  for (const stage of STAGES) node.append(judgmentForm(pair, episode, stage));
  return node;
}
function hasEpisodeWork(pair) {
  return pair.episodes.some(episode => episode.arrangement
    || episode.interval.start !== pair.interval.start || episode.interval.end !== pair.interval.end
    || STAGES.some(stage => {
      const judgment = episode[stage];
      return judgment && (judgment.verdict || judgment.explanation || judgment.alternatives
        || judgment.supporting_evidence.length || judgment.contradicting_evidence.length);
    }));
}
function changeCoverage(pair, value) {
  pair.coverage = value;
  if (value === "unreviewed") pair.interval = null;
  else if (value === "no_candidate") pair.interval = whole();
  else pair.interval ??= whole();
  if (value === "episodes" && !pair.episodes.length) pair.episodes.push(blankEpisode(pair.interval));
  if (value !== "episodes") {
    pair.episodes = [];
    if (target?.pair === pair) target = null;
  }
  changed(); renderPairs();
}
function renderPairs() {
  const container = $("pairs");
  const opened = new Set([...container.querySelectorAll(".pair[open]")].map(node => node.dataset.pair));
  const first = !container.children.length;
  container.replaceChildren();
  pairs.forEach((pair, index) => {
    const node = el("details", undefined, "pair"); const key = pair.pair.join("–");
    node.dataset.pair = pair.pair.join(""); node.open = opened.has(node.dataset.pair) || first && index === 0;
    node.append(el("summary", `${key} · ${pair.coverage.replaceAll("_", " ")}`));
    const body = el("div", undefined, "pair-body");
    const coverage = select([["unreviewed", "Unreviewed"], ["no_candidate", "Reviewed — no candidate"], ["episodes", "Reviewed — candidate episodes"]], pair.coverage, value => {
      body.querySelector(".coverage-confirmation")?.remove();
      if (value !== "episodes" && hasEpisodeWork(pair)) {
        coverage.value = pair.coverage;
        const prompt = el("div", undefined, "coverage-confirmation"); prompt.setAttribute("role", "alert");
        prompt.append(el("p", `Switching to ${value === "no_candidate" ? "no candidate" : "unreviewed"} removes this pair's candidate episodes, judgments, and evidence.`));
        const actions = el("div", undefined, "toolbar");
        actions.append(button("Discard episodes and switch", () => changeCoverage(pair, value)),
          button("Keep candidate episodes", () => { prompt.remove(); coverage.focus(); }));
        prompt.append(actions); coverage.parentElement.after(prompt);
        return;
      }
      changeCoverage(pair, value);
    });
    coverage.dataset.field = "coverage";
    body.append(labeled("Pair coverage", coverage));
    if (pair.coverage === "no_candidate") {
      const full = pair.interval.start === 0 && pair.interval.end === LAST;
      body.append(el("p", full
        ? "Whole session reviewed — no candidate arrangement found. No explanation is required."
        : `This imported review covers only events ${pair.interval.start}–${pair.interval.end}. Review the rest before marking the whole session reviewed.`, "hint"));
      if (!full) body.append(button("Mark whole session reviewed", () => {
        pair.interval = whole(); changed(); renderPairs();
      }));
      const notes = el("details", undefined, "coverage-notes"); notes.open = !!pair.explanation;
      notes.append(el("summary", "Notes (optional)"), labeled("Optional notes", textarea(pair, "explanation")));
      body.append(notes);
    } else {
      if (pair.interval) body.append(intervalControls(pair.interval));
      body.append(labeled("Coverage explanation", textarea(pair, "explanation")));
    }
    if (pair.coverage === "episodes") {
      pair.episodes.forEach((episode, i) => body.append(episodeForm(pair, episode, i)));
      body.append(button("Add episode", () => { pair.episodes.push(blankEpisode(pair.interval)); changed(); renderPairs(); }));
    }
    node.append(body); container.append(node);
  });
  for (const pair of pairs) for (const episode of pair.episodes) for (const stage of STAGES) renderEvidence(episode, stage);
  $("progress").textContent = `${pairs.filter(pair => pair.coverage !== "unreviewed").length} / 3 pairs marked reviewed`;
  refreshTarget();
}
