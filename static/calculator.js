/**
 * Super Mortgage Calculator — Core Calculation Engine (JavaScript)
 * Mirrors super_mortgage_calculator.py exactly for GitHub Pages deployment.
 */

// ---------------------------------------------------------------------------
// ZIP-code CAGR lookup (mock — replace with real API call if desired)
// ---------------------------------------------------------------------------
const ZIP_CAGR = {
  "94105": 0.058,
  "10001": 0.045,
  "60601": 0.032,
  "33101": 0.052,
  "98101": 0.049,
  "78701": 0.061,
  "30301": 0.038,
  "02101": 0.041,
  "80202": 0.055,
  "85001": 0.043,
};
const DEFAULT_CAGR = 0.04;

function getZipCagr(zip) {
  return ZIP_CAGR[zip.trim()] ?? DEFAULT_CAGR;
}

// ---------------------------------------------------------------------------
// 1. Standard Mortgage Engine
// ---------------------------------------------------------------------------

/**
 * M = P * r(1+r)^n / ((1+r)^n - 1)
 */
function computeMonthlyPayment(principal, monthlyRate, nPayments) {
  if (monthlyRate === 0) return principal / nPayments;
  const factor = Math.pow(1 + monthlyRate, nPayments);
  return principal * (monthlyRate * factor) / (factor - 1);
}

/**
 * @param {object} inputs
 *   homePrice, downPaymentPct, loanTermYears, annualInterestRate,
 *   annualPropertyTax, annualHomeownersInsurance, monthlyHoa, pmiAnnualRate
 * @returns {object} full mortgage result
 */
function calculateMortgage(inputs) {
  const {
    homePrice,
    downPaymentPct,
    loanTermYears,
    annualInterestRate,
    annualPropertyTax = 0,
    annualHomeownersInsurance = 0,
    monthlyHoa = 0,
    pmiAnnualRate = 0.5,
  } = inputs;

  const downPayment = homePrice * (downPaymentPct / 100);
  const loanAmount = homePrice - downPayment;
  const monthlyRate = (annualInterestRate / 100) / 12;
  const nPayments = loanTermYears * 12;
  const pmiRequired = downPaymentPct < 20;

  const monthlyPI = computeMonthlyPayment(loanAmount, monthlyRate, nPayments);
  const monthlyTax = annualPropertyTax / 12;
  const monthlyIns = annualHomeownersInsurance / 12;
  const monthlyPMI = pmiRequired ? (pmiAnnualRate / 100) * loanAmount / 12 : 0;

  // Build amortization to get exact totals
  let balance = loanAmount;
  let totalInterest = 0;
  let totalPrincipal = 0;

  for (let month = 1; month <= nPayments; month++) {
    const interest = +(balance * monthlyRate).toFixed(2);
    let principalPart = +(monthlyPI - interest).toFixed(2);
    if (month === nPayments) {
      principalPart = +balance.toFixed(2);
      balance = 0;
    } else {
      balance = +(balance - principalPart).toFixed(2);
    }
    totalInterest += interest;
    totalPrincipal += principalPart;
  }

  totalInterest = +totalInterest.toFixed(2);
  totalPrincipal = +totalPrincipal.toFixed(2);

  const monthlyPITI = +(monthlyPI + monthlyTax + monthlyIns + monthlyHoa + monthlyPMI).toFixed(2);
  const totalPaid = +(downPayment + totalPrincipal + totalInterest).toFixed(2);

  return {
    downPayment: +downPayment.toFixed(2),
    loanAmount: +loanAmount.toFixed(2),
    pmiRequired,
    monthlyPI: +monthlyPI.toFixed(2),
    monthlyTax: +monthlyTax.toFixed(2),
    monthlyIns: +monthlyIns.toFixed(2),
    monthlyHoa: +monthlyHoa.toFixed(2),
    monthlyPMI: +monthlyPMI.toFixed(2),
    monthlyPITI,
    totalInterest,
    totalPrincipal,
    totalPaid,
  };
}

// ---------------------------------------------------------------------------
// 2. Hyper-Local Real Estate Appreciation
// ---------------------------------------------------------------------------

/**
 * FV = PV * (1 + CAGR)^30
 */
function calculateAppreciation(homePrice, zip, totalCostOfOwnership) {
  const cagr = getZipCagr(zip);
  const futureValue30yr = +(homePrice * Math.pow(1 + cagr, 30)).toFixed(2);
  const netGainOrLoss = +(futureValue30yr - totalCostOfOwnership).toFixed(2);
  const roiPct = totalCostOfOwnership
    ? +((netGainOrLoss / totalCostOfOwnership) * 100).toFixed(2)
    : 0;

  return {
    zip,
    cagrPct: +(cagr * 100).toFixed(2),
    currentValue: homePrice,
    futureValue30yr,
    totalCostOfOwnership: +totalCostOfOwnership.toFixed(2),
    netGainOrLoss,
    roiPct,
  };
}

// ---------------------------------------------------------------------------
// 3. Rent vs. Buy Opportunity Cost
// ---------------------------------------------------------------------------

/**
 * R_y = R_0 * (1.02)^floor(y/3)
 */
function rentAtYear(baseRent, year) {
  return baseRent * Math.pow(1.02, Math.floor(year / 3));
}

/**
 * Simulate month-by-month SPY investment.
 * Down payment invested at Year 0. Each month the difference
 * (mortgage PITI - current rent) is added if positive.
 *
 * @param {object} inputs  monthlyRent, monthlyMortgagePITI, downPayment,
 *                         spyAnnualReturn, loanTermYears
 * @param {number[]} snapshotYears
 * @returns {object[]} array of snapshot objects
 */
function calculateRentVsBuy(inputs, snapshotYears = [5, 10, 15, 20, 25, 30]) {
  const {
    monthlyRent,
    monthlyMortgagePITI,
    downPayment,
    spyAnnualReturn = 10,
    loanTermYears = 30,
  } = inputs;

  const monthlyReturn = Math.pow(1 + spyAnnualReturn / 100, 1 / 12) - 1;
  let portfolio = downPayment;
  const snapshots = [];
  const totalMonths = loanTermYears * 12;
  const snapshotSet = new Set(snapshotYears);

  for (let month = 1; month <= totalMonths; month++) {
    const year = Math.floor((month - 1) / 12); // 0-indexed
    const currentRent = rentAtYear(monthlyRent, year);
    const diff = monthlyMortgagePITI - currentRent;

    portfolio = portfolio * (1 + monthlyReturn);
    if (diff > 0) portfolio += diff;

    if (month % 12 === 0) {
      const yr = month / 12;
      if (snapshotSet.has(yr)) {
        snapshots.push({
          year: yr,
          monthlyRent: +currentRent.toFixed(2),
          monthlyMortgage: +monthlyMortgagePITI.toFixed(2),
          monthlyInvestment: +Math.max(diff, 0).toFixed(2),
          portfolioValue: +portfolio.toFixed(2),
        });
      }
    }
  }

  return snapshots;
}
