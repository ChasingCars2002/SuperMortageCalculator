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
