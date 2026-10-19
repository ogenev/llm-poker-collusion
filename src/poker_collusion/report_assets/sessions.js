let pageIndex = 0;
const pageSize = 25;
const searchText = report.sessions.map(session => JSON.stringify(session).toLowerCase());
const exclusions = [...new Set(report.sessions.flatMap(reasons))].sort();
exclusions.forEach((reason, index) => {
  const option = element("option", label(reason)); option.value = String(index); $("exclusion-filter").append(option);
});

function evidence(parent, title, references) {
  parent.append(element("h4", title));
  if (!references.length) { parent.append(element("p", "None cited.", "hint")); return; }
  list(parent, references.map(ref => `${ref.session_id} · event #${ref.sequence} · ${label(ref.event)}${ref.message === null ? "" : ` · message ${ref.message.index} · ${ref.message.sender} → ${ref.message.recipient ?? "public"}`}`));
}

function showSession(session) {
  const panel = $("session-detail"); panel.replaceChildren(); panel.hidden = false;
  const heading = element("h3", `${session.sample_id} · ${names[session.channel]}`);
  panel.append(heading);
  const identity = element("dl", undefined, "facts"); panel.append(identity);
  facts(identity, [["Run ID", session.run_id], ["Block ID", session.block_id], ["Seed", session.seed], ["Session ID", session.analysis?.source.session_id ?? "Unavailable"]]);
  const explanation = element("div", undefined, "notice subtle");
  explanation.append(element("p", "Eligibility is metric-specific. An audited session can contribute payoffs while its coalition labels remain excluded."));
  table(explanation, "Saved inclusion decisions", ["Metric", "Status / reasons"], [
    ["Payoffs", session.session_exclusions.length ? session.session_exclusions.map(label).join("; ") : "Eligible"],
    ...stages.map(stage => [label(stage), session.stage_exclusions[stage].length ? session.stage_exclusions[stage].map(label).join("; ") : "Eligible"])
  ]); panel.append(explanation);
  if (session.issues.length) { panel.append(element("h4", "Artifact issues")); list(panel, session.issues.map(label)); }
  const analysis = session.analysis;
  if (analysis === null) { panel.append(element("p", "No session analysis is available. This planned attempt remains in the dataset denominator.")); panel.focus(); return; }
  const review = analysis.review;
  facts(identity, [["Journal status", label(analysis.source.status)], ["Journal SHA-256", analysis.source.sha256], ["Review", review === null ? "No selected review" : `${review.reviewer.id} · ${review.reviewer.kind} · ${review.review_status}`]]);
  if (review !== null) facts(identity, [["Annotation ID", review.annotation_id], ["Annotation SHA-256", review.sha256], ["Rubric", `${review.rubric.id} ${review.rubric.version}`], ["Predecessor", review.supersedes === null ? "None" : `${review.supersedes.annotation_id} · ${review.supersedes.sha256}`]]);
  const url = Object.hasOwn(payload.review_pages, analysis.source.session_id) ? payload.review_pages[analysis.source.session_id] : null;
  if (url) {
    const link = element("a", "Open source review page"); link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer";
    panel.append(link, element("p", "Source transcript and review form. This link does not preload the selected annotation; import that file to inspect it in the form.", "hint"));
  } else panel.append(element("p", "No review-page link supplied. Evidence citations below identify journal events; the transcript is not embedded in this report.", "hint"));
  if (analysis.session.failure !== null) {
    panel.append(element("h4", "Recorded failure"), element("pre", JSON.stringify(analysis.session.failure, null, 2)));
  }
  panel.append(element("h3", "Stage outcomes"));
  table(panel, "Session rollups retain the underlying episode groups", ["Stage", "Verdict", "Review complete", "Observed episodes", "Uncertain episodes", "Unjudged episodes"], stages.map(stage => {
    const s = analysis.outcomes[stage];
    return [label(stage), label(s.verdict), s.review_complete ? "Yes" : "No", s.observed_episodes.join(", ") || "None", s.uncertain_episodes.join(", ") || "None", s.unjudged_episodes.join(", ") || "None"];
  }));
  for (const pair of analysis.pairs) {
    const node = details(panel, `Pair ${pair.pair.join(" + ")} · ${label(pair.coverage)}`);
    node.append(element("p", pair.explanation || "No pair review explanation recorded."));
    node.append(element("p", `Review coverage: ${pair.review_complete ? "complete" : "unfinished"}. Journal interval: ${pair.reviewed_interval === null ? "unavailable" : `${pair.reviewed_interval.start}–${pair.reviewed_interval.end}`}.`, "hint"));
    if (pair.payoffs !== null) {
      const p = pair.payoffs;
      table(node, "Descriptive settled payoffs (partial for failed/interrupted sessions)", ["Member / group", "Chips"], [...Object.entries(p.member_payoffs), ["Combined pair", p.combined_payoff], [`Outsider ${p.outsider}`, p.outsider_payoff]]);
    } else node.append(element("p", "Payoffs unavailable."));
    for (const entry of pair.episodes) {
      const episode = entry.annotation, body = element("div", undefined, "evidence"); node.append(body);
      body.append(element("h4", `Episode ${episode.episode_id}`), element("p", episode.arrangement));
      body.append(element("p", `Events ${episode.interval.start}–${episode.interval.end}; hands: ${entry.hand_indices === null ? "unavailable" : entry.hand_indices.join(", ")}. Context intervals are not exact onset times.`, "hint"));
      for (const stage of stages) {
        const judgment = episode[stage], part = details(body, `${label(stage)} · ${judgment === null ? "Unjudged" : label(judgment.verdict)}`);
        if (judgment === null) { part.append(element("p", "No judgment recorded.")); continue; }
        part.append(element("p", judgment.explanation), element("h4", "Alternatives considered"), element("p", judgment.alternatives));
        evidence(part, "Supporting evidence", judgment.supporting_evidence);
        evidence(part, "Contradicting evidence", judgment.contradicting_evidence);
      }
    }
  }
  const raw = details(panel, "Full saved session analysis"); raw.append(element("pre", JSON.stringify(analysis, null, 2)));
  panel.focus();
}

function sessions() {
  const query = $("search").value.trim().toLowerCase(), channel = $("channel-filter").value;
  const status = $("status-filter").value, review = $("review-filter").value, exclusion = $("exclusion-filter").value;
  const filtered = report.sessions.filter((s, index) => {
    const why = reasons(s);
    return (!query || searchText[index].includes(query)) && (channel === "all" || s.channel === channel)
      && (status === "all" || (s.analysis?.source.status ?? "missing") === status)
      && (review === "all" || (s.analysis?.review?.review_status ?? "unreviewed") === review)
      && (exclusion === "all" || (exclusion === "any" ? why.length > 0 : exclusion === "eligible" ? why.length === 0 : why.includes(exclusions[Number(exclusion)])));
  });
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize)); pageIndex = Math.min(pageIndex, pages - 1);
  $("session-count").textContent = `${filtered.length} of ${report.planned_sessions} planned sessions shown. Saved estimates are unchanged.`;
  $("empty-sessions").hidden = filtered.length !== 0;
  $("previous-page").disabled = pageIndex === 0; $("next-page").disabled = pageIndex === pages - 1;
  $("page-number").textContent = `Page ${pageIndex + 1} of ${pages}`;
  const body = $("session-table").querySelector("tbody"); body.replaceChildren();
  $("session-detail").hidden = true; $("session-detail").replaceChildren();
  for (const s of filtered.slice(pageIndex * pageSize, (pageIndex + 1) * pageSize)) {
    const row = element("tr"), identity = element("td", s.sample_id);
    identity.append(element("p", s.block_id, "hint")); row.append(identity, element("td", names[s.channel]), element("td", label(s.analysis?.source.status ?? "missing")));
    row.append(element("td", s.analysis?.review ? `${label(s.analysis.review.review_status)} · ${s.analysis.review.reviewer.kind}` : "Unreviewed"));
    for (const stage of stages) { const cell = element("td"); cell.append(badge(s.analysis?.outcomes[stage].verdict)); row.append(cell); }
    const cell = element("td"), button = element("button", "View"); button.type = "button";
    button.setAttribute("aria-label", `View ${s.sample_id} in ${s.run_id}`); button.addEventListener("click", () => showSession(s)); cell.append(button); row.append(cell); body.append(row);
  }
}

try {
  overview(); sessions(); $("loading").hidden = true;
  $("print").addEventListener("click", () => window.print());
  for (const id of ["search", "channel-filter", "status-filter", "review-filter", "exclusion-filter"]) {
    $(id).addEventListener(id === "search" ? "input" : "change", () => { pageIndex = 0; sessions(); });
  }
  $("reset-filters").addEventListener("click", () => {
    $("search").value = "";
    for (const id of ["channel-filter", "status-filter", "review-filter", "exclusion-filter"]) $(id).value = "all";
    pageIndex = 0; sessions();
  });
  $("previous-page").addEventListener("click", () => { pageIndex--; sessions(); });
  $("next-page").addEventListener("click", () => { pageIndex++; sessions(); });
} catch (error) {
  $("loading").hidden = false; $("loading").textContent = `Unable to display this report: ${error.message}`;
  $("loading").setAttribute("role", "alert"); throw error;
}
