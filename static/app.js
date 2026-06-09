/* Super Mortgage Calculator — UI Logic (client-side only, no server needed) */

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
  el.classList.add(value >= 0 ? "positive" : "negative");
}

/* --- Slider sync --- */
const sliderPairs = [
  { input: "home_price", slider: "home_price_slider" },
  { input: "down_payment_pct", slider: "down_payment_pct_slider" },
  { input: "loan_term_years", slider: "loan_term_years_slider" },
  { input: "annual_interest_rate", slider: "annual_interest_rate_slider" },
];

sliderPairs.forEach(({ input, slider }) => {
  const inputEl = document.getElementById(input);
  const sliderEl = document.getElementById(slider);
  if (!inputEl || !sliderEl) return;

  sliderEl.addEventListener("input", () => {
    inputEl.value = sliderEl.value;
    debouncedCalc();
  });

  inputEl.addEventListener("input", () => {
    const v = parseFloat(inputEl.value);
    if (!isNaN(v)) sliderEl.value = v;
  });
});

/* --- Dark mode toggle --- */
const themeToggle = document.getElementById("theme-toggle");

function applyTheme(dark) {
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  localStorage.setItem("theme", dark ? "dark" : "light");
}

// Init theme: respect localStorage, then system preference
(function initTheme() {
  const stored = localStorage.getItem("theme");
  if (stored) {
    applyTheme(stored === "dark");
  } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    applyTheme(true);
  }
})();

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    applyTheme(!isDark);
  });
}

/* --- Debounced real-time calculation --- */
let debounceTimer = null;

function debouncedCalc() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(runCalculation, 300);
}

// Listen for input changes on all form fields. Sliders already trigger
// debouncedCalc via their own sync listeners above, so exclude range inputs
// here to avoid double-binding the same handler.
form.querySelectorAll("input:not([type=range])").forEach(input => {
  input.addEventListener("input", debouncedCalc);
});

/* --- Chart colors --- */
const CHART_COLORS = {
  pi: "#6366f1",
  tax: "#f59e0b",
  ins: "#10b981",
  hoa: "#8b5cf6",
  pmi: "#ef4444",
};

/* --- Main calculation --- */
function runCalculation() {
  errorBox.classList.add("hidden");

  try {
    const mortgageInputs = {
      homePrice: parseFloat(document.getElementById("home_price").value),
      downPaymentPct: parseFloat(document.getElementById("down_payment_pct").value),
      loanTermYears: parseInt(document.getElementById("loan_term_years").value),
      annualInterestRate: parseFloat(document.getElementById("annual_interest_rate").value),
      annualPropertyTax: parseFloat(document.getElementById("annual_property_tax").value || 0),
      annualHomeownersInsurance: parseFloat(document.getElementById("annual_homeowners_insurance").value || 0),
      monthlyHoa: parseFloat(document.getElementById("monthly_hoa").value || 0),
      pmiAnnualRate: parseFloat(document.getElementById("pmi_annual_rate").value || 0),
    };

    const zip = document.getElementById("zip_code").value.trim();
    const monthlyRent = parseFloat(document.getElementById("monthly_rent").value || 0);
    const spyReturn = parseFloat(document.getElementById("spy_return").value || 10);

    // Validate — if any required numeric input is missing or out of range
    // (e.g. a field cleared mid-typing), hide stale results instead of
    // rendering NaN into every cell and the donut chart.
    const invalid =
      isNaN(mortgageInputs.homePrice) || mortgageInputs.homePrice <= 0 ||
      isNaN(mortgageInputs.downPaymentPct) || mortgageInputs.downPaymentPct < 0 || mortgageInputs.downPaymentPct > 100 ||
      isNaN(mortgageInputs.loanTermYears) || mortgageInputs.loanTermYears < 1 ||
      isNaN(mortgageInputs.annualInterestRate) || mortgageInputs.annualInterestRate < 0;
    if (invalid) {
      resultsDiv.classList.add("hidden");
      return;
    }

    // All calculations run client-side via calculator.js
    const m = calculateMortgage(mortgageInputs);
    const a = calculateAppreciation(mortgageInputs.homePrice, zip, m.totalPaid);
    const snapshots = calculateRentVsBuy({
      monthlyRent,
      monthlyMortgagePITI: m.monthlyPITI,
      downPayment: m.downPayment,
      spyAnnualReturn: spyReturn,
      loanTermYears: mortgageInputs.loanTermYears,
    });

    // --- Render PITI ---
    set("r-pi",   fmt(m.monthlyPI));
    set("r-tax",  fmt(m.monthlyTax));
    set("r-ins",  fmt(m.monthlyIns));
    set("r-hoa",  fmt(m.monthlyHoa));
    set("r-pmi",  fmt(m.monthlyPMI));
    set("r-piti", fmt(m.monthlyPITI));
    document.getElementById("pmi-row").style.display = m.pmiRequired ? "" : "none";

    // --- Render donut chart ---
    const segments = [
      { label: "Principal & Interest", value: m.monthlyPI, color: CHART_COLORS.pi },
      { label: "Property Tax", value: m.monthlyTax, color: CHART_COLORS.tax },
      { label: "Insurance", value: m.monthlyIns, color: CHART_COLORS.ins },
      { label: "HOA", value: m.monthlyHoa, color: CHART_COLORS.hoa },
    ];
    if (m.pmiRequired) {
      segments.push({ label: "PMI", value: m.monthlyPMI, color: CHART_COLORS.pmi });
    }
    drawDonut("piti-donut", segments, { size: 180 });
    renderLegend("piti-legend", segments);

    // --- Render totals ---
    set("r-dp",        fmt(m.downPayment));
    set("r-principal", fmt(m.totalPrincipal));
    set("r-interest",  fmt(m.totalInterest));
    set("r-total-tax", fmt(m.totalTax));
    set("r-total-ins", fmt(m.totalInsurance));
    set("r-total-hoa", fmt(m.totalHoa));
    set("r-total-pmi", fmt(m.totalPMI));
    set("r-total",     fmt(m.totalPaid));
    document.getElementById("pmi-total-row").style.display = m.pmiRequired ? "" : "none";

    // --- Render appreciation ---
    set("r-zip",    a.zip);
    set("r-cagr",   fmtPct(a.cagrPct));
    set("r-hv-now", fmt(a.currentValue));
    set("r-hv-30",  fmt(a.futureValue30yr));

    document.getElementById("r-net").textContent =
      (a.netGainOrLoss >= 0 ? "+" : "") + fmt(a.netGainOrLoss);
    colorSign("r-net", a.netGainOrLoss);

    document.getElementById("r-roi").textContent =
      (a.roiPct >= 0 ? "+" : "") + fmtPct(a.roiPct);
    colorSign("r-roi", a.roiPct);

    // --- Render Rent vs Buy table ---
    const tbody = document.getElementById("r-rvb-body");
    tbody.innerHTML = "";
    snapshots.forEach(row => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>Year ${row.year}</td>
        <td>${fmt(row.monthlyRent)}</td>
        <td>${fmt(row.monthlyMortgage)}</td>
        <td>${fmt(row.monthlyInvestment)}</td>
        <td><strong>${fmt(row.portfolioValue)}</strong></td>
      `;
      tbody.appendChild(tr);
    });

    resultsDiv.classList.remove("hidden");

  } catch (err) {
    errorBox.textContent = "Error: " + err.message;
    errorBox.classList.remove("hidden");
  }
}

/* --- Form submit (button click / Enter) --- */
form.addEventListener("submit", (e) => {
  e.preventDefault();
  runCalculation();
  resultsDiv.scrollIntoView({ behavior: "smooth", block: "start" });
});
