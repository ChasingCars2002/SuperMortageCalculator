"""
Super Mortgage Calculator — Flask Web Server
"""

from flask import Flask, request, jsonify, render_template
from super_mortgage_calculator import (
    MortgageInputs,
    calculate_mortgage,
    calculate_appreciation,
    RentVsBuyInputs,
    calculate_rent_vs_buy,
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
        )

        mortgage = calculate_mortgage(inputs)

        zip_code = str(data.get("zip_code", "00000"))
        appreciation = calculate_appreciation(
            inputs.home_price, zip_code, mortgage.total_paid
        )

        monthly_rent = float(data.get("monthly_rent", 0))
        spy_return = float(data.get("spy_return", 10.0))

        rvb_inputs = RentVsBuyInputs(
            monthly_rent=monthly_rent,
            monthly_mortgage_piti=mortgage.monthly_piti,
            down_payment=inputs.down_payment_amount,
            spy_annual_return=spy_return,
            loan_term_years=inputs.loan_term_years,
        )
        snapshots = calculate_rent_vs_buy(rvb_inputs)

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
                "total_paid": mortgage.total_paid,
                "down_payment": inputs.down_payment_amount,
                "loan_amount": inputs.loan_amount,
                "pmi_required": inputs.pmi_required,
            },
            "appreciation": {
                "zip_code": appreciation.zip_code,
                "cagr_pct": round(appreciation.cagr * 100, 2),
                "current_value": appreciation.current_value,
                "future_value_30yr": appreciation.future_value_30yr,
                "total_cost_of_ownership": appreciation.total_cost_of_ownership,
                "net_gain_or_loss": appreciation.net_gain_or_loss,
                "roi_pct": round(appreciation.net_real_estate_roi * 100, 2),
            },
            "rent_vs_buy": [
                {
                    "year": s.year,
                    "monthly_rent": s.monthly_rent,
                    "monthly_mortgage": s.monthly_mortgage,
                    "monthly_investment": s.monthly_investment,
                    "portfolio_value": s.portfolio_value,
                }
                for s in snapshots
            ],
        })

    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
