/**
 * Super Mortgage Calculator — Core Calculation Engine (JavaScript)
 * Mirrors super_mortgage_calculator.py exactly for GitHub Pages deployment.
 */

// PMI automatically terminates when the loan is scheduled to reach 78% LTV
// of the original home value (Homeowners Protection Act of 1998).
const PMI_CANCEL_LTV = 0.78;

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
 * Month-by-month schedule with penny rounding.
 * PMI is charged while the balance at the start of the month exceeds
 * 78% of the original home value, then drops off automatically.
 * Extra principal shortens the schedule; the final payment is reduced
 * to exactly retire the balance.
 */
function buildAmortizationSchedule(principal, monthlyRate, nPayments, monthlyPayment, homePrice = 0, monthlyPMI = 0, extraPayment = 0) {
  const pmiThreshold = homePrice * PMI_CANCEL_LTV;
  const schedule = [];
  let balance = +principal.toFixed(2);

  for (let month = 1; month <= nPayments; month++) {
    if (balance <= 0) break;

    const pmi = (monthlyPMI > 0 && balance > pmiThreshold) ? monthlyPMI : 0;
    const interest = +(balance * monthlyRate).toFixed(2);
    let principalPart = +(monthlyPayment - interest + extraPayment).toFixed(2);

    if (month === nPayments || principalPart >= balance) {
      principalPart = balance; // final payment: pay exactly what is owed
    }
    balance = +(balance - principalPart).toFixed(2);

    schedule.push({
      month,
      payment: +(principalPart + interest).toFixed(2),
      principal: principalPart,
      interest,
      pmi,
      remainingBalance: balance,
    });
  }

  return schedule;
}

/**
 * @param {object} inputs
 * homePrice, downPaymentPct, loanTermYears, annualInterestRate,
 * annualPropertyTax, annualHomeownersInsurance, monthlyHoa, pmiAnnualRate,
 * extraMonthlyPayment
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
    extraMonthlyPayment = 0,
  } = inputs;

  const downPayment = homePrice * (downPaymentPct / 100);
  const loanAmount = homePrice - downPayment;
  const monthlyRate = (annualInterestRate / 100) / 12;
  const nPayments = loanTermYears * 12;
  const pmiRequired = downPaymentPct < 20;

  const monthlyPI = +computeMonthlyPayment(loanAmount, monthlyRate, nPayments).toFixed(2);
  const monthlyTax = +(annualPropertyTax / 12).toFixed(2);
  const monthlyIns = +(annualHomeownersInsurance / 12).toFixed(2);
  const monthlyHoaR = +monthlyHoa.toFixed(2);
  const monthlyPMI = pmiRequired ? +((pmiAnnualRate / 100) * loanAmount / 12).toFixed(2) : 0;
  const extra = +Math.max(extraMonthlyPayment, 0).toFixed(2);

  const schedule = buildAmortizationSchedule(loanAmount, monthlyRate, nPayments, monthlyPI, homePrice, monthlyPMI, extra);

  const totalInterest = +schedule.reduce((s, r) => s + r.interest, 0).toFixed(2);
  const totalPrincipal = +schedule.reduce((s, r) => s + r.principal, 0).toFixed(2);
  const totalPMI = +schedule.reduce((s, r) => s + r.pmi, 0).toFixed(2);
  const pmiMonths = schedule.filter(r => r.pmi > 0).length;
  const monthsToPayoff = schedule.length;

  // Interest/time saved vs. the no-extra-payment baseline
  let interestSaved = 0;
  let monthsSaved = 0;
  if (extra > 0) {
    const baseline = buildAmortizationSchedule(loanAmount, monthlyRate, nPayments, monthlyPI, homePrice, monthlyPMI, 0);
    interestSaved = +(baseline.reduce((s, r) => s + r.interest, 0) - totalInterest).toFixed(2);
    monthsSaved = baseline.length - monthsToPayoff;
  }

  // Tax, insurance and HOA accrue for the full ownership horizon (the loan
  // term), even if extra payments retire the loan early.
  const totalTax = +(monthlyTax * nPayments).toFixed(2);
  const totalInsurance = +(monthlyIns * nPayments).toFixed(2);
  const totalHoa = +(monthlyHoaR * nPayments).toFixed(2);

  const monthlyPITI = +(monthlyPI + monthlyTax + monthlyIns + monthlyHoaR + monthlyPMI).toFixed(2);
  const totalPaid = +(downPayment + totalPrincipal + totalInterest + totalPMI + totalTax + totalInsurance + totalHoa).toFixed(2);

  return {
    downPayment: +downPayment.toFixed(2),
    loanAmount: +loanAmount.toFixed(2),
    pmiRequired,
    monthlyPI,
    monthlyTax,
    monthlyIns,
    monthlyHoa: monthlyHoaR,
    monthlyPMI,
    monthlyPITI,
    totalInterest,
    totalPrincipal,
    totalPMI,
    pmiMonths,
    monthsToPayoff,
    interestSaved,
    monthsSaved,
    totalTax,
    totalInsurance,
    totalHoa,
    totalPaid,
    schedule,
  };
}

/**
 * Builds per-month {costs, balances} over the loan term horizon.
 * While the loan is active: P&I actually paid + extra + PMI + tax/ins/HOA.
 * After payoff: only tax, insurance and HOA continue.
 */
function monthlyHousingCostSeries(result, loanTermYears) {
  const fixed = result.monthlyTax + result.monthlyIns + result.monthlyHoa;
  const costs = [];
  const balances = [];
  const nPayments = loanTermYears * 12;

  for (let m = 0; m < nPayments; m++) {
    if (m < result.schedule.length) {
      const row = result.schedule[m];
      costs.push(+(row.payment + row.pmi + fixed).toFixed(2));
      balances.push(row.remainingBalance);
    } else {
      costs.push(+fixed.toFixed(2));
      balances.push(0);
    }
  }

  return { costs, balances };
}

// ---------------------------------------------------------------------------
// 2. Hyper-Local Real Estate Appreciation
// ---------------------------------------------------------------------------

/**
 * FV = PV * (1 + CAGR)^years
 */
function calculateAppreciation(homePrice, zip, totalCostOfOwnership, years = 30) {
  const cagr = getZipCagr(zip);
  const futureValue = +(homePrice * Math.pow(1 + cagr, years)).toFixed(2);
  const netGainOrLoss = +(futureValue - totalCostOfOwnership).toFixed(2);
  const roiPct = totalCostOfOwnership
    ? +((netGainOrLoss / totalCostOfOwnership) * 100).toFixed(2)
    : 0;

  return {
    zip,
    cagr,
    cagrPct: +(cagr * 100).toFixed(2),
    years,
    currentValue: homePrice,
    futureValue,
    totalCostOfOwnership: +totalCostOfOwnership.toFixed(2),
    netGainOrLoss,
    roiPct,
  };
}

// ---------------------------------------------------------------------------
// 3. Rent vs. Buy Net-Worth Comparison
// ---------------------------------------------------------------------------

/**
 * R_y = R_0 * (1 + g)^y with annual rent increases.
 */
function rentAtYear(baseRent, year, annualIncreasePct = 3) {
  return baseRent * Math.pow(1 + annualIncreasePct / 100, year);
}

/**
 * Simulates renter and buyer net worth month-by-month, symmetrically.
 *
 * Renter: invests the down payment at t=0, plus the monthly difference
 * whenever owning costs more than renting.
 * Buyer: builds equity through principal paydown and appreciation, and
 * invests the monthly difference whenever renting costs more than owning.
 * Both portfolios compound at the same expected market return.
 *
 * Buyer net worth = home value x (1 - sale cost %) - loan balance
 *                   + buyer's investment portfolio.
 * Renter net worth = renter's investment portfolio.
 *
 * @returns {object[]} one snapshot per year (1..horizonYears)
 */
function calculateRentVsBuy(inputs) {
  const {
    monthlyRent,
    downPayment,
    homePrice,
    homeCagr,
    monthlyHousingCosts,
    loanBalances,
    annualRentIncreasePct = 3,
    spyAnnualReturn = 10,
    saleCostPct = 6,
    horizonYears = 30,
  } = inputs;

  const monthlyReturn = Math.pow(1 + spyAnnualReturn / 100, 1 / 12) - 1;
  const monthlyGrowth = Math.pow(1 + homeCagr, 1 / 12) - 1;
  const saleFactor = 1 - saleCostPct / 100;

  let renterPortfolio = downPayment; // lump-sum invested at t=0
  let buyerPortfolio = 0;
  let homeValue = homePrice;

  const snapshots = [];
  const totalMonths = horizonYears * 12;

  for (let month = 1; month <= totalMonths; month++) {
    const year = Math.floor((month - 1) / 12); // 0-indexed
    const currentRent = rentAtYear(monthlyRent, year, annualRentIncreasePct);

    const idx = month - 1;
    const housingCost = idx < monthlyHousingCosts.length ? monthlyHousingCosts[idx] : 0;
    const balance = idx < loanBalances.length ? loanBalances[idx] : 0;

    // Portfolios grow first, then this month's surplus is contributed
    renterPortfolio *= (1 + monthlyReturn);
    buyerPortfolio *= (1 + monthlyReturn);
    const diff = housingCost - currentRent;
    if (diff > 0) {
      renterPortfolio += diff;
    } else {
      buyerPortfolio += -diff;
    }

    homeValue *= (1 + monthlyGrowth);

    if (month % 12 === 0) {
      const equity = homeValue * saleFactor - balance;
      const buyerNet = equity + buyerPortfolio;
      snapshots.push({
        year: month / 12,
        monthlyRent: +currentRent.toFixed(2),
        monthlyHousingCost: +housingCost.toFixed(2),
        renterPortfolio: +renterPortfolio.toFixed(2),
        homeValue: +homeValue.toFixed(2),
        homeEquity: +equity.toFixed(2),
        buyerPortfolio: +buyerPortfolio.toFixed(2),
        buyerNetWorth: +buyerNet.toFixed(2),
        advantage: +(buyerNet - renterPortfolio).toFixed(2),
      });
    }
  }

  return snapshots;
}

/**
 * First year the buyer's net worth meets or exceeds the renter's, or null.
 */
function findBreakEvenYear(snapshots) {
  for (const s of snapshots) {
    if (s.buyerNetWorth >= s.renterPortfolio) return s.year;
  }
  return null;
}
