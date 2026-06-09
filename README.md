# Super Mortgage Calculator

A highly accurate, multi-faceted mortgage and opportunity cost calculator.

## Features

- **Standard Mortgage Engine** — penny-level amortization using the standard formula
- **PMI Auto-Cancellation** — PMI drops off automatically once the loan reaches 78% LTV of the original home value (Homeowners Protection Act), instead of being charged for the full term
- **Extra Principal Payments** — see months shaved off the loan and total interest saved, with a before/after balance chart
- **Hyper-Local Real Estate Appreciation** — ZIP-code CAGR projection over the loan term
- **Rent vs. Buy Net-Worth Comparison** — symmetric simulation: the renter invests the down payment plus any monthly savings; the buyer builds home equity (net of sale costs) and invests any monthly savings. Reports the break-even year and charts both net-worth paths
- **Full Mathematical Transparency** — show-your-work mode for manual verification

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

The frontend is fully client-side (`index.html` + `static/`), so it also deploys
to GitHub Pages with no server.

## Run Tests

```bash
python -m unittest test_calculator.py -v
```

## CLI Demo (no server)

```bash
python super_mortgage_calculator.py
```

Runs the reference test case: $500k home, 20% down, 6.5%, $2,000/mo rent.

## Reference Output (test case)

| Metric | Value |
|--------|-------|
| Monthly PITI | $3,403.27 |
| Total Interest (30yr) | $510,179.81 |
| Home Value in 30yr (ZIP 78701, 6.1% CAGR) | $2,954,143.05 |
| Rent vs. Buy break-even | Year 6 |

With 10% down instead: PMI of $187.50/mo is charged for 109 months
($20,437.50 total), then cancels automatically at 78% LTV.

With an extra $500/mo principal payment: the loan retires in 233 months
(10 yr 7 mo early), saving $205,558.55 in interest.

## Methodology Notes

- **Amortization** uses penny rounding each month; the final payment is
  adjusted to retire the balance exactly.
- **PMI** is charged while the scheduled balance exceeds 78% of the original
  home value, matching the automatic-termination rule.
- **Rent vs. buy** compares net worth, not cash flow: buyer net worth =
  home value × (1 − sale cost %) − loan balance + invested surplus;
  renter net worth = down payment + monthly surplus invested at the
  expected market return. Rent grows at a configurable annual rate.
- **Total cost of ownership** = down payment + principal + interest + PMI
  actually paid + property tax, insurance and HOA over the full term.
