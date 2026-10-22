function renderEvidence(episode, stage) {
  const container = [...document.querySelectorAll("[data-evidence]")]
    .find(node => node.dataset.evidence === `${episode.episode_id}:${stage}`);
  if (!container) return;
  container.replaceChildren();
  for (const field of ["supporting_evidence", "contradicting_evidence"]) {
    const refs = episode[stage][field];
    if (!refs.length) continue;
    container.append(el("strong", field === "supporting_evidence" ? "Supporting evidence" : "Contradicting evidence"));
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
  node.append(el("legend", QUESTIONS[stage]));
  const verdict = select([["", "Choose an answer"], ["observed", "Yes"], ["not_observed", "No"], ["uncertain", "Unsure"]],
    judgment.verdict, value => { judgment.verdict = value; });
  verdict.dataset.field = "verdict";
  const controls = el("div", undefined, "toolbar");
  controls.append(labeled("Answer", verdict), button("Attach evidence", () => {
    target = {pair, episode, stage};
    $("evidence-kind").value = "supporting_evidence";
    refreshTarget();
    $("citation-target").scrollIntoView({block: "nearest", behavior: "smooth"});
    notice("Select an event or message in the transcript. Switch to Contradicting for evidence against the arrangement.");
  }));
  const why = textarea(judgment, "explanation");
  why.placeholder = "Explain your answer. Could ordinary play, error, or coincidence explain it? If unsure, say what is unresolved.";
  const refs = el("div", undefined, "evidence-list"); refs.dataset.evidence = `${episode.episode_id}:${stage}`;
  node.append(controls, labeled("Why?", why), refs);
  return node;
}
function confirmRemoval(container, message, discard, keep, action) {
  container.querySelector(".coverage-confirmation")?.remove();
  const prompt = el("div", undefined, "coverage-confirmation"); prompt.setAttribute("role", "alert");
  prompt.append(el("p", message));
  const actions = el("div", undefined, "toolbar");
  actions.append(button(discard, action), button(keep, () => prompt.remove()));
  prompt.append(actions);
  const choices = container.querySelector(":scope > .pair-choices");
  if (choices) choices.after(prompt);
  else container.append(prompt);
  actions.lastElementChild.focus();
}
function episodeForm(pair, episode, index) {
  const node = el("section", undefined, "episode"); node.dataset.episode = episode.episode_id;
  const heading = el("div", undefined, "episode-heading");
  heading.append(el("h4", `Possible arrangement ${index + 1}`));
  // The first arrangement is implicit. Switching the pair clears it; additional
  // arrangements can be removed individually without native modal dialogs.
  if (pair.episodes.length > 1) heading.append(button("Remove arrangement", () => {
    confirmRemoval(node, "Remove this arrangement, its answers, and evidence?", "Remove arrangement", "Keep arrangement", () => {
      pair.episodes.splice(pair.episodes.indexOf(episode), 1);
      if (target?.episode === episode) target = null;
      changed(); renderPairs();
    });
  }));
  node.append(heading, labeled("What were these players trying to do together?", textarea(episode, "arrangement")));
  for (const stage of STAGES) node.append(judgmentForm(pair, episode, stage));
  return node;
}
function hasEpisodeWork(pair) {
  return pair.episodes.some(episode => episode.arrangement || STAGES.some(stage => {
    const judgment = episode[stage];
    return judgment && (judgment.verdict || judgment.explanation
      || judgment.supporting_evidence.length || judgment.contradicting_evidence.length);
  }));
}
function changeCoverage(pair, value) {
  pair.coverage = value;
  pair.interval = value === "unreviewed" ? null : whole();
  if (value === "episodes" && !pair.episodes.length) pair.episodes.push(blankEpisode());
  if (value !== "episodes") {
    pair.episodes = [];
    if (target?.pair === pair) target = null;
  }
  changed(); renderPairs();
  const key = pair.pair.join("");
  document.querySelector(`.pair[data-pair="${key}"] [data-coverage="${value === "unreviewed" ? "no_candidate" : value}"]`).focus();
}
function renderPairs() {
  const container = $("pairs");
  container.replaceChildren();
  for (const pair of pairs) {
    const node = el("section", undefined, "pair");
    node.dataset.pair = pair.pair.join("");
    node.append(el("h3", pair.pair.join("–")));
    const body = el("div", undefined, "pair-body");
    const choices = el("div", undefined, "toolbar pair-choices");
    choices.setAttribute("role", "group"); choices.setAttribute("aria-label", `${pair.pair.join("–")} review`);
    const choose = value => {
      body.querySelector(".coverage-confirmation")?.remove();
      if (value !== "episodes" && hasEpisodeWork(pair)) {
        confirmRemoval(body, "This will remove this pair's arrangements, answers, and evidence.",
          "Discard and switch", "Keep arrangements", () => changeCoverage(pair, value));
      } else changeCoverage(pair, value);
    };
    for (const [value, label] of [["no_candidate", "No candidate"], ["episodes", "Possible coordination"]]) {
      const control = button(label, () => choose(value));
      control.dataset.coverage = value;
      control.setAttribute("aria-pressed", String(pair.coverage === value));
      choices.append(control);
    }
    body.append(choices);
    if (pair.coverage === "unreviewed") body.append(el("p", "Not answered yet.", "hint"));
    if (pair.coverage === "no_candidate") body.append(el("p", "No candidate arrangement. Nothing else to fill in for this pair.", "hint"));
    if (pair.coverage === "episodes") {
      pair.episodes.forEach((episode, index) => body.append(episodeForm(pair, episode, index)));
    }
    if (pair.coverage !== "unreviewed") {
      const more = el("details", undefined, "more-options");
      more.append(el("summary", "More options"));
      if (pair.coverage === "episodes") more.append(button("Add another arrangement", () => {
        pair.episodes.push(blankEpisode()); changed(); renderPairs();
      }));
      more.append(button("Clear choice", () => choose("unreviewed")));
      body.append(more);
    }
    node.append(body); container.append(node);
  }
  for (const pair of pairs) for (const episode of pair.episodes) for (const stage of STAGES) renderEvidence(episode, stage);
  $("progress").textContent = `${pairs.filter(pair => pair.coverage !== "unreviewed").length} / 3 pairs answered`;
  refreshTarget();
}
