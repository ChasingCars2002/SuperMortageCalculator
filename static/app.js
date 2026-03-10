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

form.addEventListener("submit", (e) => {
  e.preventDefault();
  errorBox.classList.add("hidden");
  resultsDiv.classList.add("hidden");

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

    // --- Render totals ---
    set("r-dp",        fmt(m.downPayment));
    set("r-principal", fmt(m.totalPrincipal));
    set("r-interest",  fmt(m.totalInterest));
    set("r-total",     fmt(m.totalPaid));

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
    resultsDiv.scrollIntoView({ behavior: "smooth", block: "start" });

  } catch (err) {
    errorBox.textContent = "Error: " + err.message;
    errorBox.classList.remove("hidden");
  }
});
