function chart(estimate) {
  const figure = $("comparison-chart");
  if (estimate.difference === null) {
    figure.append(element("p", "No eligible matched blocks. The primary difference and interval are unavailable.", "notice")); return;
  }
  const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 640 140"); svg.setAttribute("role", "img");
  const title = document.createElementNS(ns, "title");
  title.textContent = `Private minus public: ${difference(estimate.difference, "enacted")}. ${confidence} interval: ${interval(estimate, "enacted")}.`;
  svg.append(title);
  const x = value => 55 + (value + 1) * 265;
  function draw(tag, attributes, text) {
    const node = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
    if (text !== undefined) node.textContent = text; svg.append(node);
  }
  draw("line", {x1: 55, y1: 80, x2: 585, y2: 80, class: "axis"});
  draw("line", {x1: x(0), y1: 12, x2: x(0), y2: 85, class: "zero"});
  for (const tick of [-1, -.5, 0, .5, 1]) {
    draw("line", {x1: x(tick), y1: 80, x2: x(tick), y2: 86, class: "axis"});
    draw("text", {x: x(tick), y: 105, "text-anchor": "middle"}, `${tick > 0 ? "+" : ""}${tick * 100}`);
  }
  if (estimate.interval !== null) {
    draw("line", {x1: x(estimate.interval.lower), y1: 45, x2: x(estimate.interval.upper), y2: 45, class: "interval"});
    for (const end of [estimate.interval.lower, estimate.interval.upper]) draw("line", {x1: x(end), y1: 37, x2: x(end), y2: 53, class: "interval"});
  }
  draw("circle", {cx: x(estimate.difference), cy: 45, r: 6, class: "estimate-dot"});
  draw("text", {x: 320, y: 132, "text-anchor": "middle"}, "Private − public · percentage points");
  figure.append(svg, element("figcaption", estimate.interval === null ? "Point estimate only; fewer than two eligible blocks." : `Point: saved estimate. Line: saved ${confidence} paired block bootstrap interval.`));
}

function overview() {
  $("dataset-role").textContent = `${label(report.dataset_role)} · ${label(report.gameplay_kind)}`;
  $("dataset-note").textContent = report.dataset_role === "preparation"
    ? "Preparation dataset. These results support workflow checks; they are not sprint evaluation findings."
    : report.dataset_role === "pilot"
    ? "Pilot dataset. Use these results to assess the protocol and measurement process before evaluation."
    : "Evaluation dataset, as declared in the manifest. Confirm the study plan was frozen before interpreting the results.";
  if (report.gameplay_kind === "scripted_mock") $("dataset-note").append(document.createTextNode(" Gameplay and usage are scripted mock fixtures."));
  const reviewed = report.sessions.filter(s => s.analysis?.review !== null && s.analysis?.review !== undefined).length;
  card($("overview-cards"), "Planned blocks", number(report.planned_blocks), "Unit for paired comparisons");
  card($("overview-cards"), "Planned sessions", number(report.planned_sessions), "Includes unavailable attempts");
  card($("overview-cards"), "Audited complete", number(Object.values(report.conditions).reduce((n, c) => n + c.audited_complete_sessions, 0)), "Eligible for payoff comparisons");
  card($("overview-cards"), "Selected reviews", number(reviewed), `Of ${report.planned_sessions} planned sessions; includes drafts`);
  const settings = report.experiment_settings, model = settings.model.settings;
  facts($("settings"), [["Model", model.model], ["Instructions", label(report.instruction)], ["Hands per session", settings.session.hands], ["Reviewer kind", label(report.reviewer_kind)], ["Policy", "v0.1 · provisional preparation default"]]);
  $("settings-detail").textContent = JSON.stringify({experiment: settings, analysis: report.policy}, null, 2);
  const primary = report.contrasts[0].estimates.enacted;
  card($("primary-cards"), "Private rate", percent(primary.left_mean), "Same paired denominator as public");
  card($("primary-cards"), "Public rate", percent(primary.right_mean), "Same paired denominator as private");
  card($("primary-cards"), "Difference", difference(primary.difference, "enacted"), `${confidence} interval: ${interval(primary, "enacted")}`);
  card($("primary-cards"), "Eligible blocks", `${primary.eligible_blocks} / ${primary.planned_blocks}`, `${primary.excluded_blocks} excluded`);
  chart(primary); list($("primary-warnings"), primary.warnings);
  estimateDetails($("primary-members"), primary);
  for (const channel of ["private", "public", "none"]) {
    const condition = report.conditions[channel], panel = $("condition-coverage");
    panel.append(element("h3", `${names[channel]} · ${condition.planned_sessions} planned`));
    panel.append(element("p", `Statuses: ${Object.entries(condition.statuses).map(([s, n]) => `${label(s)} ${n}`).join(" · ") || "Condition not planned"}. Audited complete: ${condition.audited_complete_sessions}.`, "hint"));
    table(panel, `${names[channel]}: raw review counts and eligible rates`, ["Stage", "Observed", "Not observed", "Uncertain", "Unknown", "Eligible / planned", "Excluded", "Resolved rate"], stages.map(stage => {
      const s = condition.stages[stage], v = s.reported_verdicts;
      return [label(stage), v.observed, v.not_observed, v.uncertain, v.unknown, `${s.eligible_sessions} / ${condition.planned_sessions}`, s.excluded_sessions, percent(s.resolved_rate)];
    }));
  }
  for (const contrast of report.contrasts) {
    const panel = details($("secondary-results"), `${names[contrast.left]} − ${names[contrast.right]}`);
    const metrics = Object.keys(contrast.estimates).sort((a, b) => [...stages, "payoff_A", "payoff_B", "payoff_C", "payoff_AB", "payoff_AC", "payoff_BC"].indexOf(a) - [...stages, "payoff_A", "payoff_B", "payoff_C", "payoff_AB", "payoff_AC", "payoff_BC"].indexOf(b));
    table(panel, `Saved differences and ${confidence} intervals`, ["Outcome", "Left mean", "Right mean", "Difference", `${confidence} interval`, "Eligible / planned", "Excluded"], metrics.map(metric => {
      const e = contrast.estimates[metric], stage = stages.includes(metric);
      return [stage ? label(metric) : `Payoff ${metric.slice(7)}`, stage ? percent(e.left_mean) : number(e.left_mean), stage ? percent(e.right_mean) : number(e.right_mean), difference(e.difference, metric), interval(e, metric), `${e.eligible_blocks} / ${e.planned_blocks}`, e.excluded_blocks];
    }));
    for (const metric of metrics) {
      const e = contrast.estimates[metric], detail = details(panel, `${label(metric)}: blocks, exclusions, and caveats`);
      list(detail, e.warnings); estimateDetails(detail, e);
    }
  }
  facts($("report-origin"), [["Comparison JSON SHA-256", payload.report_sha256], ["Analysis ruleset", `${report.provenance.ruleset} ${report.provenance.ruleset_version}`], ["Analysis code SHA-256", report.provenance.implementation_sha256], ["Runtime", `Python ${report.provenance.python_version} · OpenSpiel ${report.provenance.open_spiel_version}`]]);
  list($("report-notes"), report.notes);
  $("run-details").textContent = JSON.stringify(report.runs, null, 2);
  table($("input-hashes"), "Saved comparison input references (not reread by this viewer)", ["Path", "SHA-256"], report.inputs.map(input => [input.path, input.sha256 ?? "Missing input"]));
  const unlinked = report.runs.reduce((n, run) => n + run.unlinked_session_directories.length, 0);
  if (unlinked) $("dataset-note").append(document.createTextNode(` ${unlinked} unlinked session directories require review; see provenance.`));
}
