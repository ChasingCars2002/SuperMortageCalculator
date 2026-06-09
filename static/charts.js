/* Super Mortgage Calculator — Lightweight Canvas Charts */

function drawDonut(canvasId, segments, opts = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const size = opts.size || 200;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = size + "px";
  canvas.style.height = size + "px";
  ctx.scale(dpr, dpr);

  const cx = size / 2;
  const cy = size / 2;
  const outerR = size / 2 - 4;
  const innerR = outerR * 0.58;
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  if (total === 0) return;

  let startAngle = -Math.PI / 2;
  segments.forEach(seg => {
    const sliceAngle = (seg.value / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, startAngle, startAngle + sliceAngle);
    ctx.arc(cx, cy, innerR, startAngle + sliceAngle, startAngle, true);
    ctx.closePath();
    ctx.fillStyle = seg.color;
    ctx.fill();
    startAngle += sliceAngle;
  });

  // Center text
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--text").trim() || "#0f172a";
  ctx.font = "bold 16px Inter, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const formatted = "$" + Math.round(total).toLocaleString("en-US");
  ctx.fillText(formatted, cx, cy - 8);
  ctx.font = "11px Inter, system-ui, sans-serif";
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--text-secondary").trim() || "#475569";
  ctx.fillText("per month", cx, cy + 10);
}

/**
 * Multi-series line chart with axes.
 * @param {string} canvasId
 * @param {object[]} series [{ label, color, points: [{x, y}] }]
 * @param {object} opts { height, xLabel, formatY }
 */
function drawLineChart(canvasId, series, opts = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(canvas.parentElement ? canvas.parentElement.clientWidth - 8 : 600, 280);
  const height = opts.height || 260;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";
  ctx.scale(dpr, dpr);

  const allPoints = series.flatMap(s => s.points);
  if (allPoints.length === 0) return;

  const xMin = Math.min(...allPoints.map(p => p.x));
  const xMax = Math.max(...allPoints.map(p => p.x));
  let yMin = Math.min(0, ...allPoints.map(p => p.y));
  let yMax = Math.max(...allPoints.map(p => p.y));
  if (yMax === yMin) yMax = yMin + 1;

  const pad = { left: 64, right: 12, top: 12, bottom: 28 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const xToPx = x => pad.left + ((x - xMin) / (xMax - xMin || 1)) * plotW;
  const yToPx = y => pad.top + (1 - (y - yMin) / (yMax - yMin)) * plotH;

  const css = getComputedStyle(document.documentElement);
  const textColor = css.getPropertyValue("--text-secondary").trim() || "#475569";
  const gridColor = css.getPropertyValue("--border").trim() || "#e2e8f0";

  const fmtY = opts.formatY || (v => {
    const abs = Math.abs(v);
    if (abs >= 1e6) return "$" + (v / 1e6).toFixed(1) + "M";
    if (abs >= 1e3) return "$" + (v / 1e3).toFixed(0) + "k";
    return "$" + v.toFixed(0);
  });

  // Horizontal gridlines + y labels
  ctx.font = "11px Inter, system-ui, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  const ySteps = 5;
  for (let i = 0; i <= ySteps; i++) {
    const yVal = yMin + (i / ySteps) * (yMax - yMin);
    const py = yToPx(yVal);
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.left, py);
    ctx.lineTo(width - pad.right, py);
    ctx.stroke();
    ctx.fillStyle = textColor;
    ctx.fillText(fmtY(yVal), pad.left - 6, py);
  }

  // X labels
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  const xSteps = Math.min(10, xMax - xMin);
  for (let i = 0; i <= xSteps; i++) {
    const xVal = Math.round(xMin + (i / xSteps) * (xMax - xMin));
    ctx.fillStyle = textColor;
    ctx.fillText(String(xVal), xToPx(xVal), height - pad.bottom + 6);
  }
  if (opts.xLabel) {
    ctx.fillText(opts.xLabel, pad.left + plotW / 2, height - 12);
  }

  // Zero line (when negative values are present)
  if (yMin < 0) {
    ctx.strokeStyle = textColor;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pad.left, yToPx(0));
    ctx.lineTo(width - pad.right, yToPx(0));
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Series lines
  series.forEach(s => {
    if (!s.points.length) return;
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    s.points.forEach((p, i) => {
      const px = xToPx(p.x);
      const py = yToPx(p.y);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.stroke();
  });
}

function renderLegend(containerId, segments) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  container.innerHTML = segments
    .filter(seg => seg.value > 0)
    .map(seg => {
      const pct = total > 0 ? ((seg.value / total) * 100).toFixed(1) : "0.0";
      const val = "$" + Number(seg.value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      return `<div class="legend-item">
        <span class="legend-swatch" style="background:${seg.color}"></span>
        <span class="legend-label">${seg.label}</span>
        <span class="legend-value">${val} (${pct}%)</span>
      </div>`;
    })
    .join("");
}

function renderSeriesLegend(containerId, series) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = series
    .map(s => `<div class="legend-item">
      <span class="legend-swatch" style="background:${s.color}"></span>
      <span class="legend-label">${s.label}</span>
    </div>`)
    .join("");
}
