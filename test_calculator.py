"""
Test Suite for Super Mortgage Calculator
=========================================
Test case: $500,000 home, 20% down, 6.5% interest rate, $2,000/mo rent.
"""

import math
import unittest
from super_mortgage_calculator import (
    MortgageInputs,
    compute_monthly_payment,
    calculate_mortgage,
    get_zip_cagr,
    calculate_appreciation,
    rent_at_year,
    RentVsBuyInputs,
    calculate_rent_vs_buy,
    DEFAULT_CAGR,
)


# ---------- Shared test fixture ----------

def _default_inputs() -> MortgageInputs:
    return MortgageInputs(
        home_price=500_000,
        down_payment_pct=20.0,
        loan_term_years=30,
        annual_interest_rate=6.5,
        annual_property_tax=6_000,
        annual_homeowners_insurance=1_500,
        monthly_hoa=250,
        pmi_annual_rate=0.5,
    )


class TestMortgageInputs(unittest.TestCase):

    def test_down_payment_amount(self):
        mi = _default_inputs()
        self.assertAlmostEqual(mi.down_payment_amount, 100_000.0, places=2)

    def test_loan_amount(self):
        mi = _default_inputs()
        self.assertAlmostEqual(mi.loan_amount, 400_000.0, places=2)

    def test_monthly_rate(self):
        mi = _default_inputs()
        expected = 0.065 / 12
        self.assertAlmostEqual(mi.monthly_interest_rate, expected, places=12)

    def test_num_payments(self):
        mi = _default_inputs()
        self.assertEqual(mi.num_payments, 360)

    def test_pmi_not_required_at_20pct(self):
        mi = _default_inputs()
        self.assertFalse(mi.pmi_required)

    def test_pmi_required_below_20pct(self):
        mi = _default_inputs()
        mi.down_payment_pct = 10.0
        self.assertTrue(mi.pmi_required)


class TestMonthlyPayment(unittest.TestCase):

    def test_standard_payment(self):
        """$400k loan, 6.5%/12 monthly, 360 months → ~$2,528.27"""
        P = 400_000
        r = 0.065 / 12
        n = 360
        M = compute_monthly_payment(P, r, n)
        self.assertAlmostEqual(M, 2528.27, delta=0.01)

    def test_zero_interest(self):
        M = compute_monthly_payment(120_000, 0.0, 360)
        self.assertAlmostEqual(M, 333.33, delta=0.01)


class TestMortgageResult(unittest.TestCase):

    def setUp(self):
        self.result = calculate_mortgage(_default_inputs())

    def test_monthly_pi(self):
        self.assertAlmostEqual(self.result.monthly_principal_interest, 2528.27, delta=0.01)

    def test_monthly_piti_components(self):
        # tax=500, ins=125, hoa=250, pmi=0 (20% down)
        expected = 2528.27 + 500 + 125 + 250
        self.assertAlmostEqual(self.result.monthly_piti, expected, delta=0.02)

    def test_total_interest_reasonable(self):
        # Over 30 yr at 6.5% on 400k, total interest should be ~$510k
        self.assertGreater(self.result.total_interest, 500_000)
        self.assertLess(self.result.total_interest, 520_000)

    def test_total_principal_equals_loan(self):
        self.assertAlmostEqual(self.result.total_principal, 400_000, delta=1.0)

    def test_amortization_length(self):
        self.assertEqual(len(self.result.amortization_schedule), 360)

    def test_amortization_ends_at_zero(self):
        last = self.result.amortization_schedule[-1]
        self.assertAlmostEqual(last.remaining_balance, 0.0, places=2)

    def test_first_month_interest(self):
        # First month: interest = 400000 * (0.065/12) ≈ 2166.67
        first = self.result.amortization_schedule[0]
        self.assertAlmostEqual(first.interest, 2166.67, delta=0.01)


class TestAppreciation(unittest.TestCase):

    def test_known_zip(self):
        cagr = get_zip_cagr("78701")
        self.assertAlmostEqual(cagr, 0.061, places=4)

    def test_unknown_zip_fallback(self):
        cagr = get_zip_cagr("99999")
        self.assertEqual(cagr, DEFAULT_CAGR)

    def test_future_value_calculation(self):
        result = calculate_appreciation(500_000, "78701", 1_000_000)
        expected_fv = 500_000 * (1.061 ** 30)
        self.assertAlmostEqual(result.future_value_30yr, round(expected_fv, 2), delta=0.01)

    def test_roi_positive(self):
        result = calculate_appreciation(500_000, "78701", 800_000)
        self.assertGreater(result.net_real_estate_roi, 0)

    def test_roi_negative_high_cost(self):
        result = calculate_appreciation(500_000, "78701", 10_000_000)
        self.assertLess(result.net_real_estate_roi, 0)


class TestRentStepFunction(unittest.TestCase):

    def test_year_0(self):
        self.assertAlmostEqual(rent_at_year(2000, 0), 2000.0, places=2)

    def test_year_1(self):
        # floor(1/3) = 0, no increase
        self.assertAlmostEqual(rent_at_year(2000, 1), 2000.0, places=2)

    def test_year_3(self):
        # floor(3/3) = 1 → 2000 * 1.02^1 = 2040
        self.assertAlmostEqual(rent_at_year(2000, 3), 2040.0, places=2)

    def test_year_6(self):
        # floor(6/3) = 2 → 2000 * 1.02^2 = 2080.80
        self.assertAlmostEqual(rent_at_year(2000, 6), 2080.80, places=2)

    def test_year_9(self):
        # floor(9/3) = 3 → 2000 * 1.02^3 ≈ 2122.42
        expected = 2000 * (1.02 ** 3)
        self.assertAlmostEqual(rent_at_year(2000, 9), expected, places=2)

    def test_year_30(self):
        # floor(30/3) = 10 → 2000 * 1.02^10 ≈ 2437.99
        expected = 2000 * (1.02 ** 10)
        self.assertAlmostEqual(rent_at_year(2000, 30), expected, places=2)


class TestRentVsBuy(unittest.TestCase):

    def setUp(self):
        mortgage_result = calculate_mortgage(_default_inputs())
        self.rvb = RentVsBuyInputs(
            monthly_rent=2000.0,
            monthly_mortgage_piti=mortgage_result.monthly_piti,
            down_payment=100_000.0,
            spy_annual_return=10.0,
            loan_term_years=30,
        )
        self.snapshots = calculate_rent_vs_buy(self.rvb)

    def test_snapshot_years(self):
        years = [s.year for s in self.snapshots]
        self.assertEqual(years, [5, 10, 15, 20, 25, 30])

    def test_portfolio_grows_over_time(self):
        values = [s.portfolio_value for s in self.snapshots]
        for i in range(1, len(values)):
            self.assertGreater(values[i], values[i - 1])

    def test_5yr_portfolio_reasonable(self):
        # With $100k initial + ~$1,400/mo contributions at 10%, 5yr should be > $200k
        five = self.snapshots[0]
        self.assertGreater(five.portfolio_value, 200_000)

    def test_30yr_portfolio_substantial(self):
        # After 30 years of compounding, should be well over $1M
        thirty = self.snapshots[-1]
        self.assertGreater(thirty.portfolio_value, 1_000_000)

    def test_down_payment_included(self):
        # Even with 0 monthly contribution, portfolio should grow from DP alone
        rvb_no_diff = RentVsBuyInputs(
            monthly_rent=99999.0,  # rent > mortgage, so diff is negative, no contribution
            monthly_mortgage_piti=2000.0,
            down_payment=100_000.0,
            spy_annual_return=10.0,
            loan_term_years=30,
        )
        snaps = calculate_rent_vs_buy(rvb_no_diff)
        # $100k at 10% for 5 years ≈ $161k
        self.assertGreater(snaps[0].portfolio_value, 160_000)


class TestIntegration(unittest.TestCase):
    """End-to-end test with the reference scenario."""

    def test_full_pipeline(self):
        mi = _default_inputs()
        mortgage = calculate_mortgage(mi)

        # Mortgage sanity
        self.assertAlmostEqual(mortgage.monthly_principal_interest, 2528.27, delta=0.01)

        # Appreciation
        appreciation = calculate_appreciation(mi.home_price, "78701", mortgage.total_paid)
        self.assertGreater(appreciation.future_value_30yr, mi.home_price)

        # Rent vs Buy
        rvb = RentVsBuyInputs(
            monthly_rent=2000.0,
            monthly_mortgage_piti=mortgage.monthly_piti,
            down_payment=mi.down_payment_amount,
            spy_annual_return=10.0,
            loan_term_years=30,
        )
        snapshots = calculate_rent_vs_buy(rvb)
        self.assertEqual(len(snapshots), 6)

        # The 30-year SPY portfolio should significantly outperform or
        # at least be comparable to home appreciation — verifying both paths compute.
        self.assertGreater(snapshots[-1].portfolio_value, 0)
        self.assertGreater(appreciation.future_value_30yr, 0)


if __name__ == "__main__":
    unittest.main()
