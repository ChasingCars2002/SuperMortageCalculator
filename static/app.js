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

function fmtMonths(months) {
  const years = Math.floor(months / 12);
  const rem = months % 12;
  if (years === 0) return `${rem} mo`;
  if (rem === 0) return `${years} yr`;
  return `${years} yr ${rem} mo`;
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
  { input: "extra_monthly_payment", slider: "extra_monthly_payment_slider" },
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

themeToggle.addEventListener("click", () => {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  applyTheme(!isDark);
  // Re-render charts so canvas text/grid colors pick up the new theme
  if (!resultsDiv.classList.contains("hidden")) runCalculation();
});

/* --- Debounced real-time calculation --- */
let debounceTimer = null;

function debouncedCalc() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(runCalculation, 300);
}

// Listen for input changes on all form fields
form.querySelectorAll("input").forEach(input => {
  input.addEventListener("input", debouncedCalc);
});

/* --- Chart colors --- */
const CHART_COLORS = {
  pi: "#6366f1",
  tax: "#f59e0b",
  ins: "#10b981",
  hoa: "#8b5cf6",
  pmi: "#ef4444",
  buyer: "#6366f1",
  renter: "#f59e0b",
  balance: "#6366f1",
  baseline: "#94a3b8",
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
      extraMonthlyPayment: parseFloat(document.getElementById("extra_monthly_payment").value || 0),
    };

    const zip = document.getElementById("zip_code").value.trim();
    const monthlyRent = parseFloat(document.getElementById("monthly_rent").value || 0);
    const spyReturn = parseFloat(document.getElementById("spy_return").value || 10);
    const rentIncrease = parseFloat(document.getElementById("annual_rent_increase").value || 3);
    const saleCostPct = parseFloat(document.getElementById("sale_cost_pct").value || 6);

    // Validate
    if (isNaN(mortgageInputs.homePrice) || mortgageInputs.homePrice <= 0) return;
    if (isNaN(mortgageInputs.downPaymentPct) || mortgageInputs.downPaymentPct < 0 || mortgageInputs.downPaymentPct > 100) return;
    if (isNaN(mortgageInputs.loanTermYears) || mortgageInputs.loanTermYears < 1) return;
    if (isNaN(mortgageInputs.annualInterestRate) || mortgageInputs.annualInterestRate < 0) return;

    // All calculations run client-side via calculator.js
    const m = calculateMortgage(mortgageInputs);
    const a = calculateAppreciation(mortgageInputs.homePrice, zip, m.totalPaid, mortgageInputs.loanTermYears);
    const { costs, balances } = monthlyHousingCostSeries(m, mortgageInputs.loanTermYears);
    const snapshots = calculateRentVsBuy({
      monthlyRent,
      downPayment: m.downPayment,
      homePrice: mortgageInputs.homePrice,
      homeCagr: a.cagr,
      monthlyHousingCosts: costs,
      loanBalances: balances,
      annualRentIncreasePct: rentIncrease,
      spyAnnualReturn: spyReturn,
      saleCostPct,
      horizonYears: mortgageInputs.loanTermYears,
    });
    const breakEven = findBreakEvenYear(snapshots);

    // Reveal results before drawing: charts size themselves from
    // parentElement.clientWidth, which is 0 while the container is hidden
    resultsDiv.classList.remove("hidden");

    // --- Render PITI ---
    set("r-pi",   fmt(m.monthlyPI));
    set("r-tax",  fmt(m.monthlyTax));
    set("r-ins",  fmt(m.monthlyIns));
    set("r-hoa",  fmt(m.monthlyHoa));
    set("r-pmi",  fmt(m.monthlyPMI) + (m.pmiMonths ? ` (first ${fmtMonths(m.pmiMonths)})` : ""));
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

    // --- Render payoff / extra payment summary ---
    set("r-payoff", fmtMonths(m.monthsToPayoff));
    const extraRow = document.getElementById("extra-savings-row");
    const extraRow2 = document.getElementById("extra-time-row");
    if (m.interestSaved > 0 || m.monthsSaved > 0) {
      extraRow.style.display = "";
      extraRow2.style.display = "";
      set("r-interest-saved", fmt(m.interestSaved));
      set("r-months-saved", fmtMonths(m.monthsSaved));
    } else {
      extraRow.style.display = "none";
      extraRow2.style.display = "none";
    }

    // --- Render loan balance chart ---
    const balancePoints = m.schedule.map(row => ({ x: row.month / 12, y: row.remainingBalance }));
    balancePoints.unshift({ x: 0, y: m.loanAmount });
    const balanceSeries = [{ label: "Loan Balance", color: CHART_COLORS.balance, points: balancePoints }];
    if (m.monthsSaved > 0) {
      const baseline = buildAmortizationSchedule(
        m.loanAmount, (mortgageInputs.annualInterestRate / 100) / 12,
        mortgageInputs.loanTermYears * 12, m.monthlyPI,
        mortgageInputs.homePrice, m.monthlyPMI, 0
      );
      const basePoints = baseline.map(row => ({ x: row.month / 12, y: row.remainingBalance }));
      basePoints.unshift({ x: 0, y: m.loanAmount });
      balanceSeries.push({ label: "Without Extra Payments", color: CHART_COLORS.baseline, points: basePoints });
    }
    drawLineChart("balance-chart", balanceSeries, { xLabel: "Year" });
    renderSeriesLegend("balance-legend", balanceSeries);

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
    set("r-hv-label", `Estimated Value in ${a.years} Years`);
    set("r-hv-30",  fmt(a.futureValue));

    document.getElementById("r-net").textContent =
      (a.netGainOrLoss >= 0 ? "+" : "") + fmt(a.netGainOrLoss);
    colorSign("r-net", a.netGainOrLoss);

    document.getElementById("r-roi").textContent =
      (a.roiPct >= 0 ? "+" : "") + fmtPct(a.roiPct);
    colorSign("r-roi", a.roiPct);

    // --- Render Rent vs Buy ---
    const verdict = document.getElementById("r-breakeven");
    if (monthlyRent <= 0) {
      verdict.textContent = "Enter your current rent to compare renting vs. buying.";
      verdict.className = "verdict";
    } else if (breakEven !== null) {
      verdict.textContent = `Buying overtakes renting in Year ${breakEven}.`;
      verdict.className = "verdict positive";
    } else {
      verdict.textContent = `Renting + investing stays ahead over the full ${mortgageInputs.loanTermYears}-year horizon.`;
      verdict.className = "verdict negative";
    }

    const nwSeries = [
      { label: "Buyer Net Worth", color: CHART_COLORS.buyer, points: snapshots.map(s => ({ x: s.year, y: s.buyerNetWorth })) },
      { label: "Renter Net Worth", color: CHART_COLORS.renter, points: snapshots.map(s => ({ x: s.year, y: s.renterPortfolio })) },
    ];
    drawLineChart("networth-chart", nwSeries, { xLabel: "Year" });
    renderSeriesLegend("networth-legend", nwSeries);

    const tbody = document.getElementById("r-rvb-body");
    tbody.innerHTML = "";
    snapshots.filter(s => s.year % 5 === 0).forEach(row => {
      const tr = document.createElement("tr");
      const advSign = row.advantage >= 0 ? "+" : "";
      tr.innerHTML = `
        <td>Year ${row.year}</td>
        <td>${fmt(row.monthlyRent)}</td>
        <td>${fmt(row.monthlyHousingCost)}</td>
        <td>${fmt(row.renterPortfolio)}</td>
        <td>${fmt(row.homeEquity)}</td>
        <td><strong>${fmt(row.buyerNetWorth)}</strong></td>
        <td class="${row.advantage >= 0 ? "positive" : "negative"}">${advSign}${fmt(row.advantage)}</td>
      `;
      tbody.appendChild(tr);
    });

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

/* --- Re-render charts on window resize --- */
let resizeTimer = null;
window.addEventListener("resize", () => {
  if (resultsDiv.classList.contains("hidden")) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(runCalculation, 200);
});
