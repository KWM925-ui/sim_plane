const state = {
  telemetry: [],
  events: [],
  telemetryIndex: 0,
  eventsIndex: 0,
  meta: null,
  artifacts: [],
  comparison: null,
  platformAcceptance: null,
  suiteReports: null,
  testSurfaceReports: null,
};

const elements = {
  scenarioName: document.getElementById("scenario-name"),
  scenarioDescription: document.getElementById("scenario-description"),
  statusPill: document.getElementById("status-pill"),
  backendName: document.getElementById("backend-name"),
  vehicleName: document.getElementById("vehicle-name"),
  artifactDir: document.getElementById("artifact-dir"),
  altitudeValue: document.getElementById("altitude-value"),
  speedValue: document.getElementById("speed-value"),
  modeValue: document.getElementById("mode-value"),
  phaseValue: document.getElementById("phase-value"),
  armedValue: document.getElementById("armed-value"),
  batteryValue: document.getElementById("battery-value"),
  headingValue: document.getElementById("heading-value"),
  samplesValue: document.getElementById("samples-value"),
  resultBox: document.getElementById("result-box"),
  eventsBox: document.getElementById("events-box"),
  trackCanvas: document.getElementById("track-canvas"),
  altitudeCanvas: document.getElementById("altitude-canvas"),
  artifactList: document.getElementById("artifact-list"),
  leftArtifact: document.getElementById("left-artifact"),
  rightArtifact: document.getElementById("right-artifact"),
  compareButton: document.getElementById("compare-button"),
  compareSummary: document.getElementById("compare-summary"),
  metricDeltaTable: document.getElementById("metric-delta-table"),
  trajectoryDeltaTable: document.getElementById("trajectory-delta-table"),
  acceptanceSummary: document.getElementById("acceptance-summary"),
  acceptanceRows: document.getElementById("acceptance-rows"),
  suiteSummary: document.getElementById("suite-summary"),
  suiteList: document.getElementById("suite-list"),
  testSurfaceSummary: document.getElementById("test-surface-summary"),
  testSurfaceList: document.getElementById("test-surface-list"),
};

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${url}`);
  }
  return response.json();
}

async function hydrateMeta() {
  state.meta = await fetchJson("/api/meta");
  const scenario = state.meta.scenario || {};
  elements.scenarioName.textContent = scenario.name || "Artifact dashboard";
  elements.scenarioDescription.textContent = scenario.description || "No description";
  elements.backendName.textContent = scenario.backend || "-";
  elements.vehicleName.textContent = scenario.vehicle || "-";
  elements.artifactDir.textContent = state.meta.active_artifact_dir || state.meta.artifact_dir || state.meta.artifact_root || "-";
}

async function hydrateBrowser() {
  const [artifacts, platformAcceptance, suiteReports, testSurfaceReports] = await Promise.all([
    fetchJson("/api/artifacts?limit=120").catch(() => ({ items: [] })),
    fetchJson("/api/platform-acceptance/latest").catch(() => ({ available: false })),
    fetchJson("/api/suites/latest?limit=12").catch(() => ({ available: false, items: [] })),
    fetchJson("/api/test-surfaces/latest?limit=12").catch(() => ({ available: false, items: [] })),
  ]);
  state.artifacts = artifacts.items || [];
  state.platformAcceptance = platformAcceptance;
  state.suiteReports = suiteReports;
  state.testSurfaceReports = testSurfaceReports;
  renderArtifacts();
  renderPlatformAcceptance();
  renderSuiteReports();
  renderTestSurfaceReports();
  if (state.artifacts.length >= 2) {
    elements.leftArtifact.value = state.artifacts[1].name;
    elements.rightArtifact.value = state.artifacts[0].name;
  }
}

async function poll() {
  const [runState, telemetry, events] = await Promise.all([
    fetchJson("/api/state"),
    fetchJson(`/api/telemetry?after=${state.telemetryIndex}`),
    fetchJson(`/api/events?after=${state.eventsIndex}`),
  ]);

  if (telemetry.items.length) {
    state.telemetry.push(...telemetry.items);
    state.telemetryIndex = telemetry.next_index;
  }
  if (events.items.length) {
    state.events.push(...events.items);
    state.eventsIndex = events.next_index;
  }

  render(runState);
}

function render(runState) {
  const latest = runState.latest || {};
  elements.statusPill.textContent = runState.status || "unknown";
  elements.statusPill.dataset.status = runState.status || "unknown";

  elements.altitudeValue.textContent = `${formatNumber(latest.altitude_m)} m`;
  elements.speedValue.textContent = `${formatNumber(latest.speed_mps)} m/s`;
  elements.modeValue.textContent = latest.mode || "-";
  elements.phaseValue.textContent = latest.phase || "-";
  elements.armedValue.textContent = typeof latest.armed === "boolean" ? (latest.armed ? "yes" : "no") : "-";
  elements.batteryValue.textContent = latest.battery_pct != null ? `${formatNumber(latest.battery_pct)} %` : "-";
  elements.headingValue.textContent = latest.heading_deg != null ? `${formatNumber(latest.heading_deg)} deg` : "-";
  elements.samplesValue.textContent = String(runState.telemetry_count || 0);
  elements.resultBox.textContent = runState.result ? JSON.stringify(runState.result, null, 2) : "Waiting for result...";

  renderEvents();
  drawTrack();
  drawAltitude();
}

function renderArtifacts() {
  elements.artifactList.innerHTML = "";
  elements.leftArtifact.innerHTML = "";
  elements.rightArtifact.innerHTML = "";

  if (!state.artifacts.length) {
    elements.artifactList.textContent = "No complete artifacts found.";
    return;
  }

  state.artifacts.forEach((artifact) => {
    const optionLeft = new Option(artifact.name, artifact.name);
    const optionRight = new Option(artifact.name, artifact.name);
    elements.leftArtifact.add(optionLeft);
    elements.rightArtifact.add(optionRight);

    const row = document.createElement("div");
    row.className = `artifact-row ${artifact.active ? "active" : ""}`;
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(artifact.name)}</strong>
        <span>${escapeHtml(artifact.scenario_name || "-")} · ${escapeHtml(artifact.backend || "-")}</span>
      </div>
      <div class="artifact-status" data-status="${escapeHtml(artifact.status || "unknown")}">${escapeHtml(artifact.status || "unknown")}</div>
    `;
    elements.artifactList.appendChild(row);
  });
}

async function runComparison() {
  const left = elements.leftArtifact.value;
  const right = elements.rightArtifact.value;
  if (!left || !right) {
    return;
  }
  state.comparison = await fetchJson(`/api/compare?left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}`);
  renderComparison();
}

function renderComparison() {
  const comparison = state.comparison;
  if (!comparison || comparison.error) {
    elements.compareSummary.textContent = comparison && comparison.error ? comparison.error : "No comparison selected.";
    return;
  }
  const left = comparison.left || {};
  const right = comparison.right || {};
  const keyKpis = prioritizeMetricRows(comparison.metric_deltas || []);
  elements.compareSummary.innerHTML = `
    <strong>${escapeHtml(left.name)}</strong> -> <strong>${escapeHtml(right.name)}</strong>
    <span>${comparison.same_scenario ? "same scenario" : "different scenario"} · ${comparison.same_backend ? "same backend" : "different backend"}</span>
  `;
  renderDeltaTable(elements.metricDeltaTable, keyKpis);
  renderDeltaTable(elements.trajectoryDeltaTable, comparison.trajectory_deltas || []);
  drawTrack();
}

function prioritizeMetricRows(rows) {
  const priority = [
    "status",
    "target_altitude_reached",
    "kpi_mission_path_error_max_m",
    "kpi_mission_path_error_mae_m",
    "kpi_mission_altitude_mae_m",
    "kpi_sensor_dropout_ratio",
    "kpi_measurement_horizontal_error_max_m",
    "kpi_measurement_vertical_error_max_m",
    "kpi_speed_roughness_mps",
    "max_speed_mps",
    "max_altitude_m",
  ];
  const prioritySet = new Set(priority);
  const byName = new Map(rows.map((row) => [row.name, row]));
  const prioritized = priority.map((name) => byName.get(name)).filter(Boolean);
  const rest = rows.filter((row) => !prioritySet.has(row.name));
  return [...prioritized, ...rest];
}

function renderDeltaTable(container, rows) {
  container.innerHTML = "";
  if (!rows.length) {
    container.textContent = "No comparable metrics.";
    return;
  }
  const table = document.createElement("table");
  table.innerHTML = `
    <thead><tr><th>Metric</th><th>Left</th><th>Right</th><th>Delta</th></tr></thead>
    <tbody></tbody>
  `;
  const tbody = table.querySelector("tbody");
  rows.filter((row) => row.changed || row.delta !== null).slice(0, 18).forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.name)}</td>
      <td>${formatCell(row.left)}</td>
      <td>${formatCell(row.right)}</td>
      <td class="${row.delta > 0 ? "delta-pos" : row.delta < 0 ? "delta-neg" : ""}">${formatCell(row.delta)}</td>
    `;
    tbody.appendChild(tr);
  });
  if (!tbody.children.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="4">No changed numeric metrics.</td>';
    tbody.appendChild(tr);
  }
  container.appendChild(table);
}

function renderPlatformAcceptance() {
  const report = state.platformAcceptance;
  if (!report || !report.available) {
    elements.acceptanceSummary.textContent = "No latest platform acceptance snapshot found.";
    return;
  }
  elements.acceptanceSummary.innerHTML = `
    <strong>${escapeHtml(report.status || "unknown")}</strong>
    <span>${escapeHtml(report.selection_mode || "-")} · changed rows: ${report.changed_rows_count ?? "-"}</span>
  `;
  elements.acceptanceRows.innerHTML = "";
  (report.row_deltas || []).filter((row) => row.changed).slice(0, 8).forEach((row) => {
    const item = document.createElement("div");
    item.className = "acceptance-row";
    item.innerHTML = `
      <strong>${escapeHtml(row.name)}</strong>
      <span>${escapeHtml((row.changed_metric_names || []).join(", ") || "status change")}</span>
    `;
    elements.acceptanceRows.appendChild(item);
  });
  if (!elements.acceptanceRows.children.length) {
    elements.acceptanceRows.textContent = "Latest report has no changed rows.";
  }
}

function renderSuiteReports() {
  const report = state.suiteReports;
  if (!report || !report.available) {
    elements.suiteSummary.textContent = "No latest suite reports found.";
    elements.suiteList.innerHTML = "";
    return;
  }
  const items = report.items || [];
  const failed = items.filter((item) => item.status !== "passed").length;
  const suiteStatusText = failed ? `${failed} failing` : "all listed suites passed";
  elements.suiteSummary.innerHTML = `
    <strong>${items.length} latest suite reports</strong>
    <span>${suiteStatusText} · ${escapeHtml(report.suite_root || "-")}</span>
  `;
  elements.suiteList.innerHTML = "";
  if (!items.length) {
    elements.suiteList.textContent = "No suite reports found.";
    return;
  }
  items.forEach((suite) => {
    const item = document.createElement("div");
    item.className = "suite-card";
    const effects = (suite.top_metric_effects || []).slice(0, 3);
    const keyRows = (suite.key_metrics || []).slice(0, 5);
    const rankings = (suite.kpi_rankings || []).slice(0, 4);
    const failedRowsText = suite.failed_row_count ? ` · failed ${suite.failed_row_count}` : "";
    const effectRowsHtml = effects.length
      ? effects.map(renderSuiteEffect).join("")
      : '<span>No factor effects in this suite.</span>';
    const rankingRowsHtml = rankings.length
      ? rankings.map(renderSuiteRanking).join("")
      : '<span>No KPI ranking in this suite.</span>';
    item.innerHTML = `
      <div class="suite-head">
        <div>
          <strong>${escapeHtml(suite.suite_name || "-")}</strong>
          <span>${escapeHtml(suite.base_scenario || "-")}</span>
        </div>
        <div class="artifact-status" data-status="${escapeHtml(suite.status || "unknown")}">${escapeHtml(suite.status || "unknown")}</div>
      </div>
      <div class="suite-meta">
        rows ${suite.passed_row_count ?? 0}/${suite.row_count ?? 0}
        ${failedRowsText}
      </div>
      <div class="suite-kpis">
        ${keyRows.map(renderSuiteKpiRow).join("")}
      </div>
      <div class="suite-effects">
        ${effectRowsHtml}
      </div>
      <div class="suite-rankings">
        ${rankingRowsHtml}
      </div>
    `;
    elements.suiteList.appendChild(item);
  });
}

function renderSuiteKpiRow(row) {
  return `
    <div>
      <strong>${escapeHtml(row.name || "-")}</strong>
      <span>drop ${formatPercent(row.kpi_sensor_dropout_ratio)} · path ${formatNumber(row.kpi_mission_path_error_max_m)} m · alt ${formatNumber(row.kpi_mission_altitude_mae_m)} m</span>
    </div>
  `;
}

function renderSuiteEffect(effect) {
  return `
    <span>${escapeHtml(effect.factor || "-")} -> ${escapeHtml(effect.metric || "-")}: ${formatNumber(effect.mean_spread)}</span>
  `;
}

function renderSuiteRanking(ranking) {
  const worst = (ranking.worst || [])[0] || {};
  return `
    <span>${escapeHtml(ranking.metric || "-")}: worst ${escapeHtml(worst.name || "-")}=${formatNumber(worst.value)}, spread ${formatNumber(ranking.spread)}</span>
  `;
}

function renderTestSurfaceReports() {
  const report = state.testSurfaceReports;
  if (!report || !report.available) {
    elements.testSurfaceSummary.textContent = "No latest professional test-surface reports found.";
    elements.testSurfaceList.innerHTML = "";
    return;
  }
  const items = report.items || [];
  const failed = items.filter((item) => item.status !== "passed").length;
  elements.testSurfaceSummary.innerHTML = `
    <strong>${items.length} latest test reports</strong>
    <span>${failed ? `${failed} failing` : "all listed reports passed"} · ${escapeHtml(report.artifact_root || "-")}</span>
  `;
  elements.testSurfaceList.innerHTML = "";
  items.forEach((surface) => {
    const item = document.createElement("div");
    item.className = "suite-card";
    const metrics = surface.key_metrics || {};
    const worstCases = (surface.worst_cases || []).slice(0, 3);
    const issues = (surface.issues || []).slice(0, 2);
    item.innerHTML = `
      <div class="suite-head">
        <div>
          <strong>${escapeHtml(surface.surface || "-")} · ${escapeHtml(surface.name || "-")}</strong>
          <span>${escapeHtml(surface.latest_json || "-")}</span>
        </div>
        <div class="artifact-status" data-status="${escapeHtml(surface.status || "unknown")}">${escapeHtml(surface.status || "unknown")}</div>
      </div>
      <div class="suite-meta">
        rows ${surface.passed_row_count ?? 0}/${surface.row_count ?? 0}
        · steps ${surface.passed_step_count ?? 0}/${surface.step_count ?? 0}
        ${surface.profile ? ` · profile ${escapeHtml(surface.profile)}` : ""}
        ${surface.seed != null ? ` · seed ${escapeHtml(surface.seed)}` : ""}
      </div>
      <div class="suite-kpis">
        ${renderMetricChips(metrics)}
      </div>
      <div class="suite-rankings">
        ${worstCases.length ? worstCases.map(renderWorstCase).join("") : "<span>No worst-case ranking.</span>"}
        ${issues.length ? issues.map((issue) => `<span>issue: ${escapeHtml(issue)}</span>`).join("") : ""}
      </div>
    `;
    elements.testSurfaceList.appendChild(item);
  });
}

function renderMetricChips(metrics) {
  const entries = Object.entries(metrics || {});
  if (!entries.length) {
    return "<div><span>No key metrics in report.</span></div>";
  }
  return entries
    .map(([key, value]) => `<div><strong>${escapeHtml(key)}</strong><span>${formatCell(value)}</span></div>`)
    .join("");
}

function renderWorstCase(caseRow) {
  const worst = (caseRow.worst || [])[0] || {};
  return `
    <span>${escapeHtml(caseRow.metric || "-")}: worst ${escapeHtml(worst.name || "-")}=${formatNumber(worst.value)}, spread ${formatNumber(caseRow.spread)}</span>
  `;
}

function renderEvents() {
  elements.eventsBox.innerHTML = "";
  const items = state.events.slice(-12);
  if (!items.length) {
    elements.eventsBox.textContent = "No events yet.";
    return;
  }

  items.reverse().forEach((event) => {
    const row = document.createElement("div");
    row.className = "event-row";
    row.innerHTML = `
      <div class="event-level">${escapeHtml(event.level)}</div>
      <div class="event-body">
        <strong>${escapeHtml(event.message)}</strong>
        <span>${escapeHtml(event.ts_utc)}</span>
      </div>
    `;
    elements.eventsBox.appendChild(row);
  });
}

function drawTrack() {
  const canvas = elements.trackCanvas;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  paintCanvasBackdrop(ctx, canvas, "#031320", "#0c2f44");

  const comparison = state.comparison && !state.comparison.error ? state.comparison : null;
  if (comparison) {
    const leftTrack = comparison.left.track || [];
    const rightTrack = comparison.right.track || [];
    const allPoints = [...leftTrack, ...rightTrack].map((point) => ({ x_m: point.x_m, y_m: point.y_m }));
    if (!allPoints.length) {
      drawEmptyMessage(ctx, canvas, "No trajectory samples to compare");
      return;
    }
    const bounds = computeBounds(allPoints.map((p) => p.x_m), allPoints.map((p) => p.y_m));
    drawTrackLine(ctx, canvas, leftTrack, bounds, "#75e6da", 2);
    drawTrackLine(ctx, canvas, rightTrack, bounds, "#ff9f68", 3);
    drawLegend(ctx, canvas, comparison.left.name, comparison.right.name);
    return;
  }

  if (!state.telemetry.length) {
    drawEmptyMessage(ctx, canvas, "Waiting for telemetry");
    return;
  }

  const points = state.telemetry.map((sample) => sample.position).filter(Boolean);
  const xs = points.map((point) => point.x_m);
  const ys = points.map((point) => point.y_m);
  const bounds = computeBounds(xs, ys);
  drawTrackLine(ctx, canvas, points, bounds, "#75e6da", 3);
}

function drawTrackLine(ctx, canvas, points, bounds, color, width) {
  if (!points.length) {
    return;
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();

  points.forEach((point, index) => {
    const x = mapValue(point.x_m, bounds.minX, bounds.maxX, 40, canvas.width - 40);
    const y = mapValue(point.y_m, bounds.minY, bounds.maxY, canvas.height - 40, 40);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  const latest = points[points.length - 1];
  const latestX = mapValue(latest.x_m, bounds.minX, bounds.maxX, 40, canvas.width - 40);
  const latestY = mapValue(latest.y_m, bounds.minY, bounds.maxY, canvas.height - 40, 40);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(latestX, latestY, 7, 0, Math.PI * 2);
  ctx.fill();
}

function drawLegend(ctx, canvas, leftName, rightName) {
  ctx.font = "14px sans-serif";
  ctx.fillStyle = "#75e6da";
  ctx.fillText(`Left: ${leftName}`, 28, canvas.height - 28);
  ctx.fillStyle = "#ff9f68";
  ctx.fillText(`Right: ${rightName}`, 28, canvas.height - 10);
}

function drawAltitude() {
  const canvas = elements.altitudeCanvas;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  paintCanvasBackdrop(ctx, canvas, "#120629", "#3a0d52");

  const comparison = state.comparison && !state.comparison.error ? state.comparison : null;
  if (comparison) {
    const left = comparison.left.track || [];
    const right = comparison.right.track || [];
    const all = [...left, ...right];
    if (!all.length) {
      drawEmptyMessage(ctx, canvas, "No altitude samples to compare");
      return;
    }
    const maxT = Math.max(...all.map((sample) => sample.t || 0), 1);
    const maxAlt = Math.max(...all.map((sample) => sample.altitude_m || 0), 1);
    drawAltitudeLine(ctx, canvas, left, maxT, maxAlt, "#75e6da", 2);
    drawAltitudeLine(ctx, canvas, right, maxT, maxAlt, "#ff9f68", 3);
    return;
  }

  if (!state.telemetry.length) {
    drawEmptyMessage(ctx, canvas, "Waiting for telemetry");
    return;
  }

  const maxT = Math.max(...state.telemetry.map((sample) => sample.t || 0), 1);
  const maxAlt = Math.max(...state.telemetry.map((sample) => sample.altitude_m || 0), 1);
  drawAltitudeLine(ctx, canvas, state.telemetry, maxT, maxAlt, "#ff9f68", 3);
}

function drawAltitudeLine(ctx, canvas, samples, maxT, maxAlt, color, width) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  samples.forEach((sample, index) => {
    const x = mapValue(sample.t || 0, 0, maxT, 40, canvas.width - 40);
    const y = mapValue(sample.altitude_m || 0, 0, maxAlt, canvas.height - 40, 40);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

function paintCanvasBackdrop(ctx, canvas, topColor, bottomColor) {
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, topColor);
  gradient.addColorStop(1, bottomColor);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "rgba(255,255,255,0.08)";
  for (let i = 0; i < 6; i += 1) {
    const y = 40 + i * 50;
    ctx.beginPath();
    ctx.moveTo(24, y);
    ctx.lineTo(canvas.width - 24, y);
    ctx.stroke();
  }
}

function drawEmptyMessage(ctx, canvas, message) {
  ctx.fillStyle = "rgba(255,255,255,0.75)";
  ctx.font = "20px sans-serif";
  ctx.fillText(message, 24, canvas.height / 2);
}

function computeBounds(xs, ys) {
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 1);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 1);
  return {
    minX: minX === maxX ? minX - 1 : minX,
    maxX: minX === maxX ? maxX + 1 : maxX,
    minY: minY === maxY ? minY - 1 : minY,
    maxY: minY === maxY ? maxY + 1 : maxY,
  };
}

function mapValue(value, inMin, inMax, outMin, outMax) {
  if (inMax === inMin) {
    return (outMin + outMax) / 2;
  }
  const ratio = (Number(value) - inMin) / (inMax - inMin);
  return outMin + ratio * (outMax - outMin);
}

function formatNumber(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(2);
}

function formatPercent(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return "-";
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatCell(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "object") {
    return escapeHtml(JSON.stringify(value));
  }
  return escapeHtml(String(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

elements.compareButton.addEventListener("click", runComparison);

hydrateMeta()
  .then(hydrateBrowser)
  .then(poll)
  .then(() => {
    setInterval(() => {
      poll().catch((error) => console.error(error));
    }, 1000);
  })
  .catch((error) => {
    console.error(error);
    elements.scenarioName.textContent = "Dashboard error";
    elements.scenarioDescription.textContent = error.message;
  });
