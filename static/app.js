/* Super Mortgage Calculator — Frontend Logic */

const form = document.getElementById("calc-form");
const resultsDiv = document.getElementById("results");
const errorBox = document.getElementById("error-box");

function fmt(n) {
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(n) {
  return Number(n).toFixed(2) + "%";
}

function set(id, value) {
  document.getElementById(id).textContent = value;
}

function colorSign(id, value) {
  const el = document.getElementById(id);
  el.classList.remove("positive", "negative");
  if (value >= 0) el.classList.add("positive");
  else el.classList.add("negative");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.classList.add("hidden");
  resultsDiv.classList.add("hidden");

  const payload = {
    home_price: parseFloat(document.getElementById("home_price").value),
    down_payment_pct: parseFloat(document.getElementById("down_payment_pct").value),
    loan_term_years: parseInt(document.getElementById("loan_term_years").value),
    annual_interest_rate: parseFloat(document.getElementById("annual_interest_rate").value),
    annual_property_tax: parseFloat(document.getElementById("annual_property_tax").value || 0),
    annual_homeowners_insurance: parseFloat(document.getElementById("annual_homeowners_insurance").value || 0),
    monthly_hoa: parseFloat(document.getElementById("monthly_hoa").value || 0),
    pmi_annual_rate: parseFloat(document.getElementById("pmi_annual_rate").value || 0),
    zip_code: document.getElementById("zip_code").value.trim(),
    monthly_rent: parseFloat(document.getElementById("monthly_rent").value || 0),
    spy_return: parseFloat(document.getElementById("spy_return").value || 10),
  };

  let data;
  try {
    const resp = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    data = await resp.json();
    if (!resp.ok) throw new Error(data.error || "Server error");
  } catch (err) {
    errorBox.textContent = "Error: " + err.message;
    errorBox.classList.remove("hidden");
    return;
  }

  const m = data.mortgage;
  const a = data.appreciation;
  const rvb = data.rent_vs_buy;

  // PITI breakdown
  set("r-pi",       fmt(m.monthly_principal_interest));
  set("r-tax",      fmt(m.monthly_property_tax));
  set("r-ins",      fmt(m.monthly_insurance));
  set("r-hoa",      fmt(m.monthly_hoa));
  set("r-pmi",      fmt(m.monthly_pmi));
  set("r-piti",     fmt(m.monthly_piti));

  // Show/hide PMI row
  const pmiRow = document.getElementById("pmi-row");
  pmiRow.style.display = m.pmi_required ? "" : "none";

  // Total cost
  set("r-dp",        fmt(m.down_payment));
  set("r-loan",      fmt(m.loan_amount));
  set("r-principal", fmt(m.total_principal));
  set("r-interest",  fmt(m.total_interest));
  set("r-total",     fmt(m.total_paid));

  // Appreciation
  set("r-zip",     a.zip_code);
  set("r-cagr",    fmtPct(a.cagr_pct));
  set("r-hv-now",  fmt(a.current_value));
  set("r-hv-30",   fmt(a.future_value_30yr));

  const netEl = document.getElementById("r-net");
  netEl.textContent = (a.net_gain_or_loss >= 0 ? "+" : "") + fmt(a.net_gain_or_loss);
  colorSign("r-net", a.net_gain_or_loss);

  const roiEl = document.getElementById("r-roi");
  roiEl.textContent = (a.roi_pct >= 0 ? "+" : "") + fmtPct(a.roi_pct);
  colorSign("r-roi", a.roi_pct);

  // Rent vs Buy table
  const tbody = document.getElementById("r-rvb-body");
  tbody.innerHTML = "";
  rvb.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>Year ${row.year}</td>
      <td>${fmt(row.monthly_rent)}</td>
      <td>${fmt(row.monthly_mortgage)}</td>
      <td>${fmt(row.monthly_investment)}</td>
      <td><strong>${fmt(row.portfolio_value)}</strong></td>
    `;
    tbody.appendChild(tr);
  });

  resultsDiv.classList.remove("hidden");
  resultsDiv.scrollIntoView({ behavior: "smooth", block: "start" });
});
