"""
Super Mortgage Calculator
=========================
A highly accurate, multi-faceted mortgage and opportunity cost calculator.

Features:
1. Standard Mortgage Engine (amortization with penny-level accuracy)
2. Hyper-Local Real Estate Appreciation (ZIP-code based CAGR projection)
3. Rent vs. Buy Opportunity Cost Calculator (SPY investment trade-off)
4. Full mathematical transparency ("show your work" mode)
"""

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 1. Standard Mortgage Engine
# ---------------------------------------------------------------------------

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
    payment: float
    principal: float
    interest: float
    remaining_balance: float


@dataclass
class MortgageResult:
    monthly_principal_interest: float
    monthly_property_tax: float
    monthly_insurance: float
    monthly_hoa: float
    monthly_pmi: float
    monthly_piti: float  # total monthly payment
    total_principal: float
    total_interest: float
    total_paid: float
    amortization_schedule: list  # list[AmortizationRow]


def compute_monthly_payment(principal: float, monthly_rate: float, n_payments: int) -> float:
    """M = P * r(1+r)^n / ((1+r)^n - 1)"""
    if monthly_rate == 0:
        return principal / n_payments
    r = monthly_rate
    factor = (1 + r) ** n_payments
    return principal * (r * factor) / (factor - 1)


def build_amortization_schedule(principal: float, monthly_rate: float, n_payments: int, monthly_payment: float) -> list:
    schedule = []
    balance = principal
    for month in range(1, n_payments + 1):
        interest = round(balance * monthly_rate, 2)
        principal_part = round(monthly_payment - interest, 2)
        balance = round(balance - principal_part, 2)
        if month == n_payments:
            # absorb rounding residual into last payment
            principal_part = round(principal_part + balance, 2)
            balance = 0.0
        schedule.append(AmortizationRow(month, round(monthly_payment, 2), principal_part, interest, balance))
    return schedule


def calculate_mortgage(inputs: MortgageInputs) -> MortgageResult:
    P = inputs.loan_amount
    r = inputs.monthly_interest_rate
    n = inputs.num_payments

    monthly_pi = round(compute_monthly_payment(P, r, n), 2)
    schedule = build_amortization_schedule(P, r, n, monthly_pi)

    total_interest = round(sum(row.interest for row in schedule), 2)
    total_principal = round(sum(row.principal for row in schedule), 2)

    monthly_tax = round(inputs.annual_property_tax / 12.0, 2)
    monthly_ins = round(inputs.annual_homeowners_insurance / 12.0, 2)
    monthly_hoa = round(inputs.monthly_hoa, 2)
    monthly_pmi = round((inputs.pmi_annual_rate / 100.0) * P / 12.0, 2) if inputs.pmi_required else 0.0

    monthly_piti = round(monthly_pi + monthly_tax + monthly_ins + monthly_hoa + monthly_pmi, 2)
    total_paid = round(inputs.down_payment_amount + total_principal + total_interest, 2)

    return MortgageResult(
        monthly_principal_interest=monthly_pi,
        monthly_property_tax=monthly_tax,
        monthly_insurance=monthly_ins,
        monthly_hoa=monthly_hoa,
        monthly_pmi=monthly_pmi,
        monthly_piti=monthly_piti,
        total_principal=total_principal,
        total_interest=total_interest,
        total_paid=total_paid,
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
    current_value: float
    future_value_30yr: float
    total_cost_of_ownership: float
    net_real_estate_roi: float  # (FV - total_cost) / total_cost
    net_gain_or_loss: float


def calculate_appreciation(home_price: float, zip_code: str, total_cost_of_ownership: float) -> AppreciationResult:
    """FV = PV * (1 + CAGR)^30"""
    cagr = get_zip_cagr(zip_code)
    fv = home_price * (1 + cagr) ** 30
    net = fv - total_cost_of_ownership
    roi = net / total_cost_of_ownership if total_cost_of_ownership else 0.0

    return AppreciationResult(
        zip_code=zip_code,
        cagr=cagr,
        current_value=home_price,
        future_value_30yr=round(fv, 2),
        total_cost_of_ownership=round(total_cost_of_ownership, 2),
        net_real_estate_roi=round(roi, 6),
        net_gain_or_loss=round(net, 2),
    )


# ---------------------------------------------------------------------------
# 3. Rent vs. Buy Opportunity Cost Calculator
# ---------------------------------------------------------------------------

@dataclass
class RentVsBuyInputs:
    monthly_rent: float
    monthly_mortgage_piti: float
    down_payment: float
    spy_annual_return: float = 10.0  # percent
    loan_term_years: int = 30


@dataclass
class InvestmentSnapshot:
    year: int
    monthly_rent: float
    monthly_mortgage: float
    monthly_investment: float  # difference invested into SPY
    portfolio_value: float


def rent_at_year(base_rent: float, year: int) -> float:
    """R_y = R_0 * (1 + 0.02)^floor(y/3)"""
    return base_rent * (1.02 ** (year // 3))


def calculate_rent_vs_buy(inputs: RentVsBuyInputs, snapshot_years: Optional[list] = None) -> list:
    """
    Simulates renting + investing the difference month-by-month.

    The down payment is invested at Year 0.  Each month, the difference
    (mortgage PITI - current rent) is added to the portfolio if positive.
    The portfolio compounds at the SPY monthly return.
    """
    if snapshot_years is None:
        snapshot_years = [5, 10, 15, 20, 25, 30]

    monthly_return = (1 + inputs.spy_annual_return / 100.0) ** (1.0 / 12.0) - 1.0
    portfolio = inputs.down_payment  # lump-sum invested at t=0
    snapshots: list[InvestmentSnapshot] = []

    total_months = inputs.loan_term_years * 12

    for month in range(1, total_months + 1):
        year = (month - 1) // 12  # 0-indexed year
        current_rent = rent_at_year(inputs.monthly_rent, year)
        diff = inputs.monthly_mortgage_piti - current_rent

        # Portfolio grows first, then contribution is added
        portfolio = portfolio * (1 + monthly_return)
        if diff > 0:
            portfolio += diff

        # Check if this is the end of a snapshot year
        if month % 12 == 0:
            yr = month // 12
            if yr in snapshot_years:
                snapshots.append(InvestmentSnapshot(
                    year=yr,
                    monthly_rent=round(current_rent, 2),
                    monthly_mortgage=round(inputs.monthly_mortgage_piti, 2),
                    monthly_investment=round(max(diff, 0), 2),
                    portfolio_value=round(portfolio, 2),
                ))

    return snapshots


# ---------------------------------------------------------------------------
# 4. Show-Your-Work / Transparency Mode
# ---------------------------------------------------------------------------

def show_work(
    mortgage_inputs: MortgageInputs,
    zip_code: str = "00000",
    monthly_rent: float = 2000.0,
    spy_return: float = 10.0,
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
    ln(f"   ─────────────────────────────────")
    ln(f"   Monthly PITI Total     = ${result.monthly_piti:,.2f}")
    ln()
    ln(f"   Total Interest Paid    = ${result.total_interest:,.2f}")
    ln(f"   Total Principal Paid   = ${result.total_principal:,.2f}")
    ln(f"   Total Paid (incl. DP)  = ${result.total_paid:,.2f}")

    # First 3 months of amortization
    ln()
    ln("   Amortization (first 3 months):")
    ln("   Month | Payment   | Principal | Interest  | Balance")
    for row in result.amortization_schedule[:3]:
        ln(f"   {row.month:5d} | ${row.payment:>9,.2f} | ${row.principal:>9,.2f} | ${row.interest:>9,.2f} | ${row.remaining_balance:>12,.2f}")
    ln("   ...")

    # --- Section 2: Appreciation ---
    ln()
    ln("2. HYPER-LOCAL REAL ESTATE APPRECIATION")
    ln("-" * 40)
    cagr = get_zip_cagr(zip_code)
    fv = mi.home_price * (1 + cagr) ** 30
    ln(f"   ZIP Code            = {zip_code}")
    ln(f"   5-Year CAGR         = {cagr * 100:.2f}%")
    ln(f"   Formula: FV = PV × (1 + CAGR)^30")
    ln(f"   FV = ${mi.home_price:,.2f} × (1 + {cagr:.4f})^30")
    ln(f"   FV = ${mi.home_price:,.2f} × {(1 + cagr) ** 30:.10f}")
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
    ln("3. RENT vs. BUY OPPORTUNITY COST")
    ln("-" * 40)
    ln(f"   Starting Rent       = ${monthly_rent:,.2f}/mo")
    ln(f"   Mortgage PITI       = ${result.monthly_piti:,.2f}/mo")
    ln(f"   Down Payment (invested at Year 0) = ${mi.down_payment_amount:,.2f}")
    ln(f"   SPY Annual Return   = {spy_return:.1f}%")
    ln(f"   Monthly Return      = (1 + {spy_return / 100:.4f})^(1/12) − 1 = {((1 + spy_return / 100) ** (1 / 12) - 1):.10f}")
    ln()
    ln("   Rent Step Function: R_y = R_0 × (1.02)^floor(y/3)")
    for y in [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]:
        ry = rent_at_year(monthly_rent, y)
        ln(f"     Year {y:2d}: R = ${monthly_rent:,.2f} × 1.02^{y // 3} = ${ry:,.2f}")

    rvb_inputs = RentVsBuyInputs(
        monthly_rent=monthly_rent,
        monthly_mortgage_piti=result.monthly_piti,
        down_payment=mi.down_payment_amount,
        spy_annual_return=spy_return,
        loan_term_years=mi.loan_term_years,
    )
    snapshots = calculate_rent_vs_buy(rvb_inputs)
    ln()
    ln("   SPY Portfolio Snapshots:")
    ln("   Year | Rent/mo   | Mortgage/mo | Investing/mo | Portfolio Value")
    for s in snapshots:
        ln(f"   {s.year:4d} | ${s.monthly_rent:>9,.2f} | ${s.monthly_mortgage:>11,.2f} | ${s.monthly_investment:>12,.2f} | ${s.portfolio_value:>15,.2f}")

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
