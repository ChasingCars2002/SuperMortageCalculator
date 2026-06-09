"""
Super Mortgage Calculator
=========================
A highly accurate, multi-faceted mortgage and opportunity cost calculator.

Features:
1. Standard Mortgage Engine (amortization with penny-level accuracy,
   PMI auto-cancellation at 78% LTV, extra principal payments)
2. Hyper-Local Real Estate Appreciation (ZIP-code based CAGR projection)
3. Rent vs. Buy Net-Worth Comparison (renter portfolio vs. buyer equity,
   symmetric investing of the monthly difference, break-even year)
4. Full mathematical transparency ("show your work" mode)
"""

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 1. Standard Mortgage Engine
# ---------------------------------------------------------------------------

# PMI automatically terminates when the loan is scheduled to reach 78% LTV
# of the original home value (Homeowners Protection Act of 1998).
PMI_CANCEL_LTV = 0.78


@dataclass
class MortgageInputs:
    home_price: float
    down_payment_pct: float  # e.g. 20 for 20 %
    loan_term_years: int  # e.g. 30
    annual_interest_rate: float  # e.g. 6.5 for 6.5 %
    annual_property_tax: float = 0.0
    annual_homeowners_insurance: float = 0.0
    monthly_hoa: float = 0.0
    pmi_annual_rate: float = 0.0  # e.g. 0.5 for 0.5 % of loan
    extra_monthly_payment: float = 0.0  # extra principal paid each month

    @property
    def down_payment_amount(self) -> float:
        return self.home_price * (self.down_payment_pct / 100.0)

    @property
    def loan_amount(self) -> float:
        return self.home_price - self.down_payment_amount

    @property
    def monthly_interest_rate(self) -> float:
        return (self.annual_interest_rate / 100.0) / 12.0

    @property
    def num_payments(self) -> int:
        return self.loan_term_years * 12

    @property
    def pmi_required(self) -> bool:
        return self.down_payment_pct < 20.0


@dataclass
class AmortizationRow:
    month: int
    payment: float  # principal + interest + extra actually paid this month
    principal: float
    interest: float
    pmi: float
    remaining_balance: float


@dataclass
class MortgageResult:
    monthly_principal_interest: float
    monthly_property_tax: float
    monthly_insurance: float
    monthly_hoa: float
    monthly_pmi: float  # PMI charged while LTV > 78% (0 once cancelled)
    monthly_piti: float  # total monthly payment in month 1
    total_principal: float
    total_interest: float
    total_pmi: float
    total_tax: float
    total_insurance: float
    total_hoa: float
    total_paid: float  # down payment + every dollar paid over the term
    months_to_payoff: int
    pmi_months: int  # number of months PMI was actually charged
    interest_saved: float  # vs. paying no extra principal
    months_saved: int  # vs. paying no extra principal
    amortization_schedule: list  # list[AmortizationRow]


def compute_monthly_payment(principal: float, monthly_rate: float, n_payments: int) -> float:
    """M = P * r(1+r)^n / ((1+r)^n - 1)"""
    if monthly_rate == 0:
        return principal / n_payments
    r = monthly_rate
    factor = (1 + r) ** n_payments
    return principal * (r * factor) / (factor - 1)


def build_amortization_schedule(
    principal: float,
    monthly_rate: float,
    n_payments: int,
    monthly_payment: float,
    home_price: float = 0.0,
    monthly_pmi: float = 0.0,
    extra_payment: float = 0.0,
) -> list:
    """
    Month-by-month schedule with penny rounding.

    PMI is charged while the balance at the start of the month exceeds
    78% of the original home value, then drops off automatically.
    Extra principal shortens the schedule; the final payment is reduced
    to exactly retire the balance.
    """
    pmi_threshold = home_price * PMI_CANCEL_LTV
    schedule = []
    balance = round(principal, 2)

    for month in range(1, n_payments + 1):
        if balance <= 0:
            break

        pmi = monthly_pmi if (monthly_pmi > 0 and balance > pmi_threshold) else 0.0
        interest = round(balance * monthly_rate, 2)
        principal_part = round(monthly_payment - interest + extra_payment, 2)

        if month == n_payments or principal_part >= balance:
            # final payment: pay exactly what is owed
            principal_part = balance
        balance = round(balance - principal_part, 2)

        schedule.append(AmortizationRow(
            month=month,
            payment=round(principal_part + interest, 2),
            principal=principal_part,
            interest=interest,
            pmi=pmi,
            remaining_balance=balance,
        ))

    return schedule


def calculate_mortgage(inputs: MortgageInputs) -> MortgageResult:
    P = inputs.loan_amount
    r = inputs.monthly_interest_rate
    n = inputs.num_payments

    monthly_pi = round(compute_monthly_payment(P, r, n), 2)
    monthly_pmi = round((inputs.pmi_annual_rate / 100.0) * P / 12.0, 2) if inputs.pmi_required else 0.0
    extra = round(max(inputs.extra_monthly_payment, 0.0), 2)

    schedule = build_amortization_schedule(
        P, r, n, monthly_pi,
        home_price=inputs.home_price,
        monthly_pmi=monthly_pmi,
        extra_payment=extra,
    )

    total_interest = round(sum(row.interest for row in schedule), 2)
    total_principal = round(sum(row.principal for row in schedule), 2)
    total_pmi = round(sum(row.pmi for row in schedule), 2)
    pmi_months = sum(1 for row in schedule if row.pmi > 0)
    months_to_payoff = len(schedule)

    # Interest/time saved vs. the no-extra-payment baseline
    interest_saved = 0.0
    months_saved = 0
    if extra > 0:
        baseline = build_amortization_schedule(
            P, r, n, monthly_pi,
            home_price=inputs.home_price,
            monthly_pmi=monthly_pmi,
        )
        interest_saved = round(sum(row.interest for row in baseline) - total_interest, 2)
        months_saved = len(baseline) - months_to_payoff

    monthly_tax = round(inputs.annual_property_tax / 12.0, 2)
    monthly_ins = round(inputs.annual_homeowners_insurance / 12.0, 2)
    monthly_hoa = round(inputs.monthly_hoa, 2)

    # Tax, insurance and HOA accrue for the full ownership horizon (the loan
    # term), even if extra payments retire the loan early.
    total_tax = round(monthly_tax * n, 2)
    total_insurance = round(monthly_ins * n, 2)
    total_hoa = round(monthly_hoa * n, 2)

    monthly_piti = round(monthly_pi + monthly_tax + monthly_ins + monthly_hoa + monthly_pmi, 2)
    total_paid = round(
        inputs.down_payment_amount + total_principal + total_interest
        + total_pmi + total_tax + total_insurance + total_hoa,
        2,
    )

    return MortgageResult(
        monthly_principal_interest=monthly_pi,
        monthly_property_tax=monthly_tax,
        monthly_insurance=monthly_ins,
        monthly_hoa=monthly_hoa,
        monthly_pmi=monthly_pmi,
        monthly_piti=monthly_piti,
        total_principal=total_principal,
        total_interest=total_interest,
        total_pmi=total_pmi,
        total_tax=total_tax,
        total_insurance=total_insurance,
        total_hoa=total_hoa,
        total_paid=total_paid,
        months_to_payoff=months_to_payoff,
        pmi_months=pmi_months,
        interest_saved=interest_saved,
        months_saved=months_saved,
        amortization_schedule=schedule,
    )


# ---------------------------------------------------------------------------
# 2. Hyper-Local Real Estate Appreciation
# ---------------------------------------------------------------------------

# Simulated ZIP-code CAGR lookup (placeholder for real API integration)
_ZIP_CAGR_MOCK: dict[str, float] = {
    "94105": 0.058,   # San Francisco
    "10001": 0.045,   # New York
    "60601": 0.032,   # Chicago
    "33101": 0.052,   # Miami
    "98101": 0.049,   # Seattle
    "78701": 0.061,   # Austin
    "30301": 0.038,   # Atlanta
    "02101": 0.041,   # Boston
    "80202": 0.055,   # Denver
    "85001": 0.043,   # Phoenix
}

DEFAULT_CAGR = 0.04  # 4 % national average fallback


def get_zip_cagr(zip_code: str) -> float:
    """
    Returns the 5-year CAGR for the given ZIP code.

    In production, this would call a real estate API (Zillow, Redfin, etc.).
    Currently uses a mock lookup with a national-average fallback.
    """
    return _ZIP_CAGR_MOCK.get(zip_code, DEFAULT_CAGR)


@dataclass
class AppreciationResult:
    zip_code: str
    cagr: float
    years: int
    current_value: float
    future_value: float
    total_cost_of_ownership: float
    net_real_estate_roi: float  # (FV - total_cost) / total_cost
    net_gain_or_loss: float


def calculate_appreciation(
    home_price: float,
    zip_code: str,
    total_cost_of_ownership: float,
    years: int = 30,
) -> AppreciationResult:
    """FV = PV * (1 + CAGR)^years"""
    cagr = get_zip_cagr(zip_code)
    fv = home_price * (1 + cagr) ** years
    net = fv - total_cost_of_ownership
    roi = net / total_cost_of_ownership if total_cost_of_ownership else 0.0

    return AppreciationResult(
        zip_code=zip_code,
        cagr=cagr,
        years=years,
        current_value=home_price,
        future_value=round(fv, 2),
        total_cost_of_ownership=round(total_cost_of_ownership, 2),
        net_real_estate_roi=round(roi, 6),
        net_gain_or_loss=round(net, 2),
    )


# ---------------------------------------------------------------------------
# 3. Rent vs. Buy Net-Worth Comparison
# ---------------------------------------------------------------------------

@dataclass
class RentVsBuyInputs:
    monthly_rent: float
    down_payment: float
    home_price: float
    home_cagr: float  # annual appreciation, e.g. 0.04
    monthly_housing_costs: list  # cash outflow each month (PI+extra+PMI+tax+ins+HOA)
    loan_balances: list  # remaining balance at end of each month (0 after payoff)
    annual_rent_increase_pct: float = 3.0  # percent per year
    spy_annual_return: float = 10.0  # percent
    sale_cost_pct: float = 6.0  # percent of home value lost when selling
    horizon_years: int = 30


@dataclass
class NetWorthSnapshot:
    year: int
    monthly_rent: float
    monthly_housing_cost: float
    renter_portfolio: float  # renter net worth
    home_value: float
    home_equity: float  # home value net of sale costs - loan balance
    buyer_portfolio: float  # buyer's invested surplus (months rent > housing)
    buyer_net_worth: float  # home_equity + buyer_portfolio
    advantage: float  # buyer_net_worth - renter_portfolio


def rent_at_year(base_rent: float, year: int, annual_increase_pct: float = 3.0) -> float:
    """R_y = R_0 * (1 + g)^y with annual rent increases."""
    return base_rent * (1 + annual_increase_pct / 100.0) ** year


def calculate_rent_vs_buy(inputs: RentVsBuyInputs) -> list:
    """
    Simulates renter and buyer net worth month-by-month, symmetrically.

    Renter: invests the down payment at t=0, plus the monthly difference
    whenever owning costs more than renting.
    Buyer: builds equity through principal paydown and appreciation, and
    invests the monthly difference whenever renting costs more than owning.
    Both portfolios compound at the same expected market return.

    Buyer net worth = home value x (1 - sale cost %) - loan balance
                      + buyer's investment portfolio.
    Renter net worth = renter's investment portfolio.

    Returns one NetWorthSnapshot per year (1..horizon_years).
    """
    monthly_return = (1 + inputs.spy_annual_return / 100.0) ** (1.0 / 12.0) - 1.0
    monthly_growth = (1 + inputs.home_cagr) ** (1.0 / 12.0) - 1.0
    sale_factor = 1.0 - inputs.sale_cost_pct / 100.0

    renter_portfolio = inputs.down_payment  # lump-sum invested at t=0
    buyer_portfolio = 0.0
    home_value = inputs.home_price

    snapshots: list[NetWorthSnapshot] = []
    total_months = inputs.horizon_years * 12

    for month in range(1, total_months + 1):
        year = (month - 1) // 12  # 0-indexed year
        current_rent = rent_at_year(inputs.monthly_rent, year, inputs.annual_rent_increase_pct)

        idx = month - 1
        housing_cost = inputs.monthly_housing_costs[idx] if idx < len(inputs.monthly_housing_costs) else 0.0
        balance = inputs.loan_balances[idx] if idx < len(inputs.loan_balances) else 0.0

        # Portfolios grow first, then this month's surplus is contributed
        renter_portfolio *= (1 + monthly_return)
        buyer_portfolio *= (1 + monthly_return)
        diff = housing_cost - current_rent
        if diff > 0:
            renter_portfolio += diff
        else:
            buyer_portfolio += -diff

        home_value *= (1 + monthly_growth)

        if month % 12 == 0:
            equity = home_value * sale_factor - balance
            buyer_net = equity + buyer_portfolio
            snapshots.append(NetWorthSnapshot(
                year=month // 12,
                monthly_rent=round(current_rent, 2),
                monthly_housing_cost=round(housing_cost, 2),
                renter_portfolio=round(renter_portfolio, 2),
                home_value=round(home_value, 2),
                home_equity=round(equity, 2),
                buyer_portfolio=round(buyer_portfolio, 2),
                buyer_net_worth=round(buyer_net, 2),
                advantage=round(buyer_net - renter_portfolio, 2),
            ))

    return snapshots


def find_break_even_year(snapshots: list) -> Optional[int]:
    """First year the buyer's net worth meets or exceeds the renter's."""
    for s in snapshots:
        if s.buyer_net_worth >= s.renter_portfolio:
            return s.year
    return None


def monthly_housing_cost_series(result: MortgageResult, inputs: MortgageInputs) -> tuple:
    """
    Builds (costs, balances) per month over the loan term horizon.

    While the loan is active: P&I actually paid + extra + PMI + tax/ins/HOA.
    After payoff: only tax, insurance and HOA continue.
    """
    fixed = result.monthly_property_tax + result.monthly_insurance + result.monthly_hoa
    costs: list[float] = []
    balances: list[float] = []
    schedule = result.amortization_schedule

    for m in range(inputs.num_payments):
        if m < len(schedule):
            row = schedule[m]
            costs.append(round(row.payment + row.pmi + fixed, 2))
            balances.append(row.remaining_balance)
        else:
            costs.append(round(fixed, 2))
            balances.append(0.0)

    return costs, balances


# ---------------------------------------------------------------------------
# 4. Show-Your-Work / Transparency Mode
# ---------------------------------------------------------------------------

def show_work(
    mortgage_inputs: MortgageInputs,
    zip_code: str = "00000",
    monthly_rent: float = 2000.0,
    spy_return: float = 10.0,
    annual_rent_increase_pct: float = 3.0,
    sale_cost_pct: float = 6.0,
) -> str:
    """
    Returns a detailed, step-by-step breakdown of every calculation so the
    user can verify the math manually.
    """
    lines: list[str] = []

    def ln(text: str = ""):
        lines.append(text)

    mi = mortgage_inputs
    ln("=" * 70)
    ln("SUPER MORTGAGE CALCULATOR — FULL MATHEMATICAL BREAKDOWN")
    ln("=" * 70)

    # --- Section 1: Mortgage ---
    ln()
    ln("1. STANDARD MORTGAGE ENGINE")
    ln("-" * 40)
    ln(f"   Home Price          = ${mi.home_price:,.2f}")
    ln(f"   Down Payment        = {mi.down_payment_pct:.1f}%  →  ${mi.down_payment_amount:,.2f}")
    ln(f"   Loan Amount (P)     = ${mi.loan_amount:,.2f}")
    ln(f"   Annual Rate         = {mi.annual_interest_rate:.3f}%")
    ln(f"   Monthly Rate (r)    = {mi.annual_interest_rate:.3f}% / 12 = {mi.monthly_interest_rate:.10f}")
    ln(f"   Loan Term           = {mi.loan_term_years} years  →  n = {mi.num_payments} payments")
    if mi.extra_monthly_payment:
        ln(f"   Extra Principal     = ${mi.extra_monthly_payment:,.2f}/mo")
    ln()
    ln("   Formula: M = P × r(1+r)^n / ((1+r)^n − 1)")

    r = mi.monthly_interest_rate
    n = mi.num_payments
    P = mi.loan_amount
    factor = (1 + r) ** n
    M = compute_monthly_payment(P, r, n)

    ln(f"   (1+r)^n  = (1 + {r:.10f})^{n} = {factor:.10f}")
    ln(f"   r×(1+r)^n = {r:.10f} × {factor:.10f} = {r * factor:.10f}")
    ln(f"   (1+r)^n−1 = {factor - 1:.10f}")
    ln(f"   M = ${P:,.2f} × {r * factor:.10f} / {factor - 1:.10f}")
    ln(f"   M = ${M:,.2f}  (monthly principal & interest)")

    result = calculate_mortgage(mi)
    ln()
    ln(f"   Monthly Property Tax   = ${result.monthly_property_tax:,.2f}")
    ln(f"   Monthly Insurance      = ${result.monthly_insurance:,.2f}")
    ln(f"   Monthly HOA            = ${result.monthly_hoa:,.2f}")
    ln(f"   Monthly PMI            = ${result.monthly_pmi:,.2f}  (PMI required: {mi.pmi_required})")
    if result.pmi_months:
        ln(f"   PMI cancels after      = {result.pmi_months} months (78% LTV reached)")
        ln(f"   Total PMI paid         = ${result.total_pmi:,.2f}")
    ln(f"   ─────────────────────────────────")
    ln(f"   Monthly PITI Total     = ${result.monthly_piti:,.2f}  (month 1)")
    ln()
    ln(f"   Months to Payoff       = {result.months_to_payoff}")
    if result.months_saved:
        ln(f"   Months Saved (extra)   = {result.months_saved}")
        ln(f"   Interest Saved (extra) = ${result.interest_saved:,.2f}")
    ln(f"   Total Interest Paid    = ${result.total_interest:,.2f}")
    ln(f"   Total Principal Paid   = ${result.total_principal:,.2f}")
    ln(f"   Total Paid (incl. DP)  = ${result.total_paid:,.2f}")

    # First 3 months of amortization
    ln()
    ln("   Amortization (first 3 months):")
    ln("   Month | Payment   | Principal | Interest  | PMI    | Balance")
    for row in result.amortization_schedule[:3]:
        ln(f"   {row.month:5d} | ${row.payment:>9,.2f} | ${row.principal:>9,.2f} | ${row.interest:>9,.2f} | ${row.pmi:>6,.2f} | ${row.remaining_balance:>12,.2f}")
    ln("   ...")

    # --- Section 2: Appreciation ---
    ln()
    ln("2. HYPER-LOCAL REAL ESTATE APPRECIATION")
    ln("-" * 40)
    cagr = get_zip_cagr(zip_code)
    years = mi.loan_term_years
    fv = mi.home_price * (1 + cagr) ** years
    ln(f"   ZIP Code            = {zip_code}")
    ln(f"   5-Year CAGR         = {cagr * 100:.2f}%")
    ln(f"   Formula: FV = PV × (1 + CAGR)^{years}")
    ln(f"   FV = ${mi.home_price:,.2f} × (1 + {cagr:.4f})^{years}")
    ln(f"   FV = ${mi.home_price:,.2f} × {(1 + cagr) ** years:.10f}")
    ln(f"   FV = ${fv:,.2f}")
    ln()
    total_cost = result.total_paid
    net = fv - total_cost
    roi = net / total_cost if total_cost else 0
    ln(f"   Total Cost of Ownership = ${total_cost:,.2f}")
    ln(f"   Net Gain / (Loss)       = ${net:,.2f}")
    ln(f"   ROI                     = {roi * 100:.2f}%")

    # --- Section 3: Rent vs Buy ---
    ln()
    ln("3. RENT vs. BUY — NET WORTH COMPARISON")
    ln("-" * 40)
    ln(f"   Starting Rent       = ${monthly_rent:,.2f}/mo (grows {annual_rent_increase_pct:.1f}%/yr)")
    ln(f"   Mortgage PITI       = ${result.monthly_piti:,.2f}/mo (month 1)")
    ln(f"   Down Payment (renter invests at Year 0) = ${mi.down_payment_amount:,.2f}")
    ln(f"   Market Annual Return = {spy_return:.1f}%")
    ln(f"   Monthly Return      = (1 + {spy_return / 100:.4f})^(1/12) − 1 = {((1 + spy_return / 100) ** (1 / 12) - 1):.10f}")
    ln(f"   Home Sale Cost      = {sale_cost_pct:.1f}% of value")
    ln()
    ln(f"   Rent Growth: R_y = R_0 × (1 + {annual_rent_increase_pct / 100:.3f})^y")
    for y in [0, 5, 10, 15, 20, 25]:
        ry = rent_at_year(monthly_rent, y, annual_rent_increase_pct)
        ln(f"     Year {y:2d}: R = ${monthly_rent:,.2f} × {(1 + annual_rent_increase_pct / 100):.3f}^{y} = ${ry:,.2f}")

    costs, balances = monthly_housing_cost_series(result, mi)
    rvb_inputs = RentVsBuyInputs(
        monthly_rent=monthly_rent,
        down_payment=mi.down_payment_amount,
        home_price=mi.home_price,
        home_cagr=cagr,
        monthly_housing_costs=costs,
        loan_balances=balances,
        annual_rent_increase_pct=annual_rent_increase_pct,
        spy_annual_return=spy_return,
        sale_cost_pct=sale_cost_pct,
        horizon_years=mi.loan_term_years,
    )
    snapshots = calculate_rent_vs_buy(rvb_inputs)
    break_even = find_break_even_year(snapshots)
    ln()
    ln("   Net Worth Snapshots (every 5 years):")
    ln("   Year | Rent/mo   | Own/mo    | Renter NW       | Buyer NW        | Advantage")
    for s in snapshots:
        if s.year % 5 == 0:
            ln(f"   {s.year:4d} | ${s.monthly_rent:>9,.2f} | ${s.monthly_housing_cost:>9,.2f} | ${s.renter_portfolio:>15,.2f} | ${s.buyer_net_worth:>15,.2f} | ${s.advantage:>15,.2f}")
    ln()
    if break_even:
        ln(f"   Break-even: buying overtakes renting in Year {break_even}.")
    else:
        ln("   Break-even: renting + investing stays ahead over the full horizon.")

    ln()
    ln("=" * 70)
    ln("END OF REPORT")
    ln("=" * 70)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main — demo with test case
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test case: $500k home, 20% down, 6.5%, $2,000 rent
    inputs = MortgageInputs(
        home_price=500_000,
        down_payment_pct=20.0,
        loan_term_years=30,
        annual_interest_rate=6.5,
        annual_property_tax=6_000,
        annual_homeowners_insurance=1_500,
        monthly_hoa=250,
        pmi_annual_rate=0.5,
    )

    report = show_work(inputs, zip_code="78701", monthly_rent=2000.0, spy_return=10.0)
    print(report)
