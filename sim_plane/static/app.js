const state = {
  telemetry: [],
  events: [],
  telemetryIndex: 0,
  eventsIndex: 0,
  meta: null,
};

const elements = {
  scenarioName: document.getElementById("scenario-name"),
  scenarioDescription: document.getElementById("scenario-description"),
  statusPill: document.getElementById("status-pill"),
  backendName: document.getElementById("backend-name"),
  vehicleName: document.getElementById("vehicle-name"),
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
  elements.scenarioName.textContent = scenario.name || "Unnamed scenario";
  elements.scenarioDescription.textContent = scenario.description || "No description";
  elements.backendName.textContent = scenario.backend || "-";
  elements.vehicleName.textContent = scenario.vehicle || "-";
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
      <div class="event-level">${event.level}</div>
      <div class="event-body">
        <strong>${event.message}</strong>
        <span>${event.ts_utc}</span>
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

  if (!state.telemetry.length) {
    drawEmptyMessage(ctx, canvas, "Waiting for telemetry");
    return;
  }

  const points = state.telemetry.map((sample) => sample.position);
  const xs = points.map((point) => point.x_m);
  const ys = points.map((point) => point.y_m);
  const bounds = computeBounds(xs, ys);

  ctx.strokeStyle = "#75e6da";
  ctx.lineWidth = 3;
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
  ctx.fillStyle = "#ffd166";
  ctx.beginPath();
  ctx.arc(latestX, latestY, 8, 0, Math.PI * 2);
  ctx.fill();
}

function drawAltitude() {
  const canvas = elements.altitudeCanvas;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  paintCanvasBackdrop(ctx, canvas, "#120629", "#3a0d52");

  if (!state.telemetry.length) {
    drawEmptyMessage(ctx, canvas, "Waiting for telemetry");
    return;
  }

  const ts = state.telemetry.map((sample) => sample.t);
  const alts = state.telemetry.map((sample) => sample.altitude_m);
  const maxAlt = Math.max(...alts, 1);

  ctx.strokeStyle = "#ff9f68";
  ctx.lineWidth = 3;
  ctx.beginPath();

  state.telemetry.forEach((sample, index) => {
    const x = mapValue(sample.t, ts[0], ts[ts.length - 1] || 1, 40, canvas.width - 40);
    const y = mapValue(sample.altitude_m, 0, maxAlt, canvas.height - 40, 40);
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
  const ratio = (value - inMin) / (inMax - inMin);
  return outMin + ratio * (outMax - outMin);
}

function formatNumber(value) {
  if (value == null || Number.isNaN(value)) {
    return "0.0";
  }
  return Number(value).toFixed(1);
}

async function boot() {
  await hydrateMeta();
  await poll();
  window.setInterval(() => {
    poll().catch((error) => {
      console.error(error);
    });
  }, 500);
}

boot().catch((error) => {
  console.error(error);
  elements.scenarioName.textContent = "Dashboard failed to load";
  elements.scenarioDescription.textContent = error.message;
});
