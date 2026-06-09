"""
Super Mortgage Calculator — Flask Web Server
"""

from flask import Flask, request, jsonify, render_template
from super_mortgage_calculator import (
    MortgageInputs,
    calculate_mortgage,
    calculate_appreciation,
    get_zip_cagr,
    RentVsBuyInputs,
    calculate_rent_vs_buy,
    find_break_even_year,
    monthly_housing_cost_series,
)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def calculate():
    data = request.get_json()

    try:
        inputs = MortgageInputs(
            home_price=float(data["home_price"]),
            down_payment_pct=float(data["down_payment_pct"]),
            loan_term_years=int(data.get("loan_term_years", 30)),
            annual_interest_rate=float(data["annual_interest_rate"]),
            annual_property_tax=float(data.get("annual_property_tax", 0)),
            annual_homeowners_insurance=float(data.get("annual_homeowners_insurance", 0)),
            monthly_hoa=float(data.get("monthly_hoa", 0)),
            pmi_annual_rate=float(data.get("pmi_annual_rate", 0.5)),
            extra_monthly_payment=float(data.get("extra_monthly_payment", 0)),
        )

        mortgage = calculate_mortgage(inputs)

        zip_code = str(data.get("zip_code", "00000"))
        appreciation = calculate_appreciation(
            inputs.home_price, zip_code, mortgage.total_paid,
            years=inputs.loan_term_years,
        )

        monthly_rent = float(data.get("monthly_rent", 0))
        spy_return = float(data.get("spy_return", 10.0))
        annual_rent_increase = float(data.get("annual_rent_increase_pct", 3.0))
        sale_cost_pct = float(data.get("sale_cost_pct", 6.0))

        costs, balances = monthly_housing_cost_series(mortgage, inputs)
        rvb_inputs = RentVsBuyInputs(
            monthly_rent=monthly_rent,
            down_payment=inputs.down_payment_amount,
            home_price=inputs.home_price,
            home_cagr=get_zip_cagr(zip_code),
            monthly_housing_costs=costs,
            loan_balances=balances,
            annual_rent_increase_pct=annual_rent_increase,
            spy_annual_return=spy_return,
            sale_cost_pct=sale_cost_pct,
            horizon_years=inputs.loan_term_years,
        )
        snapshots = calculate_rent_vs_buy(rvb_inputs)
        break_even = find_break_even_year(snapshots)

        return jsonify({
            "mortgage": {
                "monthly_principal_interest": mortgage.monthly_principal_interest,
                "monthly_property_tax": mortgage.monthly_property_tax,
                "monthly_insurance": mortgage.monthly_insurance,
                "monthly_hoa": mortgage.monthly_hoa,
                "monthly_pmi": mortgage.monthly_pmi,
                "monthly_piti": mortgage.monthly_piti,
                "total_interest": mortgage.total_interest,
                "total_principal": mortgage.total_principal,
                "total_pmi": mortgage.total_pmi,
                "total_tax": mortgage.total_tax,
                "total_insurance": mortgage.total_insurance,
                "total_hoa": mortgage.total_hoa,
                "total_paid": mortgage.total_paid,
                "months_to_payoff": mortgage.months_to_payoff,
                "pmi_months": mortgage.pmi_months,
                "interest_saved": mortgage.interest_saved,
                "months_saved": mortgage.months_saved,
                "down_payment": inputs.down_payment_amount,
                "loan_amount": inputs.loan_amount,
                "pmi_required": inputs.pmi_required,
                "balances": [row.remaining_balance for row in mortgage.amortization_schedule],
            },
            "appreciation": {
                "zip_code": appreciation.zip_code,
                "cagr_pct": round(appreciation.cagr * 100, 2),
                "years": appreciation.years,
                "current_value": appreciation.current_value,
                "future_value": appreciation.future_value,
                "total_cost_of_ownership": appreciation.total_cost_of_ownership,
                "net_gain_or_loss": appreciation.net_gain_or_loss,
                "roi_pct": round(appreciation.net_real_estate_roi * 100, 2),
            },
            "rent_vs_buy": {
                "break_even_year": break_even,
                "snapshots": [
                    {
                        "year": s.year,
                        "monthly_rent": s.monthly_rent,
                        "monthly_housing_cost": s.monthly_housing_cost,
                        "renter_portfolio": s.renter_portfolio,
                        "home_value": s.home_value,
                        "home_equity": s.home_equity,
                        "buyer_portfolio": s.buyer_portfolio,
                        "buyer_net_worth": s.buyer_net_worth,
                        "advantage": s.advantage,
                    }
                    for s in snapshots
                ],
            },
        })

    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
