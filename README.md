# Super Mortgage Calculator

A highly accurate, multi-faceted mortgage and opportunity cost calculator.

## Features

- **Standard Mortgage Engine** — penny-level amortization using the standard formula
- **Hyper-Local Real Estate Appreciation** — ZIP-code CAGR projection to 30 years
- **Rent vs. Buy Opportunity Cost** — SPY investment simulation with step-function rent increases
- **Full Mathematical Transparency** — show-your-work mode for manual verification

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

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
| Home Value in 30yr (ZIP 78701) | $2,954,143.05 |
| SPY Portfolio at 30yr | $4,432,807.28 |
