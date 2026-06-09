"""
Test Suite for Super Mortgage Calculator
=========================================
Reference case: $500,000 home, 20% down, 6.5% interest rate, $2,000/mo rent.
"""

import math
import unittest
from super_mortgage_calculator import (
    MortgageInputs,
    compute_monthly_payment,
    build_amortization_schedule,
    calculate_mortgage,
    get_zip_cagr,
    calculate_appreciation,
    rent_at_year,
    RentVsBuyInputs,
    calculate_rent_vs_buy,
    find_break_even_year,
    monthly_housing_cost_series,
    DEFAULT_CAGR,
    PMI_CANCEL_LTV,
)


# ---------- Shared test fixture ----------

def _default_inputs(**overrides) -> MortgageInputs:
    params = dict(
        home_price=500_000,
        down_payment_pct=20.0,
        loan_term_years=30,
        annual_interest_rate=6.5,
        annual_property_tax=6_000,
        annual_homeowners_insurance=1_500,
        monthly_hoa=250,
        pmi_annual_rate=0.5,
    )
    params.update(overrides)
    return MortgageInputs(**params)


def _rvb_inputs(mi: MortgageInputs, result, **overrides) -> RentVsBuyInputs:
    costs, balances = monthly_housing_cost_series(result, mi)
    params = dict(
        monthly_rent=2000.0,
        down_payment=mi.down_payment_amount,
        home_price=mi.home_price,
        home_cagr=0.04,
        monthly_housing_costs=costs,
        loan_balances=balances,
        annual_rent_increase_pct=3.0,
        spy_annual_return=10.0,
        sale_cost_pct=6.0,
        horizon_years=mi.loan_term_years,
    )
    params.update(overrides)
    return RentVsBuyInputs(**params)


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

    def test_no_pmi_at_20pct_down(self):
        self.assertEqual(self.result.monthly_pmi, 0.0)
        self.assertEqual(self.result.total_pmi, 0.0)
        self.assertEqual(self.result.pmi_months, 0)

    def test_total_paid_is_sum_of_parts(self):
        r = self.result
        expected = (100_000 + r.total_principal + r.total_interest + r.total_pmi
                    + r.total_tax + r.total_insurance + r.total_hoa)
        self.assertAlmostEqual(r.total_paid, expected, places=2)

    def test_lifetime_escrow_totals(self):
        self.assertAlmostEqual(self.result.total_tax, 500 * 360, delta=0.01)
        self.assertAlmostEqual(self.result.total_insurance, 125 * 360, delta=0.01)
        self.assertAlmostEqual(self.result.total_hoa, 250 * 360, delta=0.01)


class TestPMICancellation(unittest.TestCase):
    """10% down → PMI required until balance hits 78% of original value."""

    def setUp(self):
        self.inputs = _default_inputs(down_payment_pct=10.0)
        self.result = calculate_mortgage(self.inputs)

    def test_pmi_charged_initially(self):
        # 0.5% of 450k / 12 = 187.50
        self.assertAlmostEqual(self.result.monthly_pmi, 187.50, places=2)
        first = self.result.amortization_schedule[0]
        self.assertAlmostEqual(first.pmi, 187.50, places=2)

    def test_pmi_cancels_before_term_end(self):
        self.assertGreater(self.result.pmi_months, 0)
        self.assertLess(self.result.pmi_months, 360)

    def test_pmi_cancels_at_78_ltv(self):
        threshold = self.inputs.home_price * PMI_CANCEL_LTV  # 390,000
        schedule = self.result.amortization_schedule
        last_pmi_month = self.result.pmi_months
        # Balance entering the last PMI month is above the threshold
        self.assertGreater(schedule[last_pmi_month - 1].pmi, 0)
        # Balance entering the following month is at/below the threshold
        self.assertLessEqual(schedule[last_pmi_month - 1].remaining_balance, threshold)
        self.assertEqual(schedule[last_pmi_month].pmi, 0.0)

    def test_total_pmi_less_than_full_term(self):
        self.assertLess(self.result.total_pmi, 187.50 * 360)
        self.assertAlmostEqual(self.result.total_pmi, 187.50 * self.result.pmi_months, delta=0.01)


class TestExtraPayments(unittest.TestCase):

    def setUp(self):
        self.baseline = calculate_mortgage(_default_inputs())
        self.result = calculate_mortgage(_default_inputs(extra_monthly_payment=500.0))

    def test_payoff_is_shorter(self):
        self.assertLess(self.result.months_to_payoff, 360)
        self.assertEqual(self.result.months_saved,
                         360 - self.result.months_to_payoff)

    def test_interest_saved_positive(self):
        self.assertGreater(self.result.interest_saved, 0)
        self.assertAlmostEqual(
            self.result.interest_saved,
            self.baseline.total_interest - self.result.total_interest,
            places=2,
        )

    def test_principal_still_equals_loan(self):
        self.assertAlmostEqual(self.result.total_principal, 400_000, delta=1.0)

    def test_balance_reaches_zero(self):
        last = self.result.amortization_schedule[-1]
        self.assertEqual(last.remaining_balance, 0.0)

    def test_known_payoff_matches_closed_form(self):
        # n = -ln(1 - P*r/M) / ln(1+r) with M = 2528.27 + 500 → ~232.7 months
        P, r, M = 400_000, 0.065 / 12, 2528.27 + 500
        expected = math.ceil(-math.log(1 - P * r / M) / math.log(1 + r))
        self.assertEqual(self.result.months_to_payoff, expected)


class TestAmortizationEdgeCases(unittest.TestCase):

    def test_zero_rate_amortizes_exactly(self):
        schedule = build_amortization_schedule(120_000, 0.0, 360, 333.33)
        self.assertAlmostEqual(schedule[-1].remaining_balance, 0.0, places=2)
        total_principal = sum(r.principal for r in schedule)
        self.assertAlmostEqual(total_principal, 120_000, delta=1.0)

    def test_full_cash_purchase(self):
        result = calculate_mortgage(_default_inputs(down_payment_pct=100.0))
        self.assertEqual(result.months_to_payoff, 0)
        self.assertEqual(result.total_interest, 0.0)
        self.assertEqual(result.monthly_principal_interest, 0.0)


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
        self.assertAlmostEqual(result.future_value, round(expected_fv, 2), delta=0.01)

    def test_future_value_respects_horizon(self):
        result = calculate_appreciation(500_000, "78701", 1_000_000, years=15)
        expected_fv = 500_000 * (1.061 ** 15)
        self.assertAlmostEqual(result.future_value, round(expected_fv, 2), delta=0.01)
        self.assertEqual(result.years, 15)

    def test_roi_positive(self):
        result = calculate_appreciation(500_000, "78701", 800_000)
        self.assertGreater(result.net_real_estate_roi, 0)

    def test_roi_negative_high_cost(self):
        result = calculate_appreciation(500_000, "78701", 10_000_000)
        self.assertLess(result.net_real_estate_roi, 0)


class TestRentGrowth(unittest.TestCase):

    def test_year_0(self):
        self.assertAlmostEqual(rent_at_year(2000, 0), 2000.0, places=2)

    def test_year_1(self):
        # 3% annual default → 2000 * 1.03 = 2060
        self.assertAlmostEqual(rent_at_year(2000, 1), 2060.0, places=2)

    def test_year_10(self):
        expected = 2000 * (1.03 ** 10)
        self.assertAlmostEqual(rent_at_year(2000, 10), expected, places=2)

    def test_custom_increase(self):
        self.assertAlmostEqual(rent_at_year(2000, 2, 5.0), 2000 * 1.05 ** 2, places=2)

    def test_zero_increase(self):
        self.assertAlmostEqual(rent_at_year(2000, 30, 0.0), 2000.0, places=2)


class TestRentVsBuy(unittest.TestCase):

    def setUp(self):
        self.mi = _default_inputs()
        self.result = calculate_mortgage(self.mi)
        self.rvb = _rvb_inputs(self.mi, self.result)
        self.snapshots = calculate_rent_vs_buy(self.rvb)

    def test_one_snapshot_per_year(self):
        years = [s.year for s in self.snapshots]
        self.assertEqual(years, list(range(1, 31)))

    def test_renter_portfolio_grows(self):
        values = [s.renter_portfolio for s in self.snapshots]
        for i in range(1, len(values)):
            self.assertGreater(values[i], values[i - 1])

    def test_buyer_net_worth_grows(self):
        values = [s.buyer_net_worth for s in self.snapshots]
        for i in range(1, len(values)):
            self.assertGreater(values[i], values[i - 1])

    def test_renter_invests_down_payment(self):
        # Renter starts with the $100k down payment; year-1 portfolio
        # must exceed 100k * monthly compounding alone is ~110k
        self.assertGreater(self.snapshots[0].renter_portfolio, 100_000)

    def test_home_value_appreciates(self):
        year1 = self.snapshots[0]
        self.assertAlmostEqual(year1.home_value, 500_000 * 1.04, delta=5)

    def test_equity_accounts_for_sale_costs_and_balance(self):
        s = self.snapshots[0]
        expected = s.home_value * 0.94 - self.result.amortization_schedule[11].remaining_balance
        self.assertAlmostEqual(s.home_equity, expected, delta=1.0)

    def test_buyer_net_worth_is_equity_plus_portfolio(self):
        for s in self.snapshots:
            self.assertAlmostEqual(s.buyer_net_worth, s.home_equity + s.buyer_portfolio, places=1)

    def test_advantage_is_difference(self):
        for s in self.snapshots:
            self.assertAlmostEqual(s.advantage, s.buyer_net_worth - s.renter_portfolio, places=1)

    def test_buyer_invests_surplus_when_rent_exceeds_housing(self):
        # Very high rent: buyer invests (rent - housing cost) each month
        rvb = _rvb_inputs(self.mi, self.result, monthly_rent=10_000.0)
        snaps = calculate_rent_vs_buy(rvb)
        self.assertGreater(snaps[0].buyer_portfolio, 0)
        # And the renter only has the down payment compounding
        self.assertAlmostEqual(
            snaps[0].renter_portfolio, 100_000 * 1.10, delta=10
        )

    def test_break_even_with_cheap_rent(self):
        # Rent far below ownership cost → renting + investing should win
        rvb = _rvb_inputs(self.mi, self.result, monthly_rent=500.0,
                          annual_rent_increase_pct=0.0)
        snaps = calculate_rent_vs_buy(rvb)
        self.assertIsNone(find_break_even_year(snaps))

    def test_break_even_with_expensive_rent(self):
        # Rent far above ownership cost → buying wins quickly
        rvb = _rvb_inputs(self.mi, self.result, monthly_rent=15_000.0)
        snaps = calculate_rent_vs_buy(rvb)
        be = find_break_even_year(snaps)
        self.assertIsNotNone(be)
        self.assertLessEqual(be, 5)


class TestHousingCostSeries(unittest.TestCase):

    def test_length_equals_term(self):
        mi = _default_inputs()
        result = calculate_mortgage(mi)
        costs, balances = monthly_housing_cost_series(result, mi)
        self.assertEqual(len(costs), 360)
        self.assertEqual(len(balances), 360)

    def test_first_month_cost(self):
        mi = _default_inputs()
        result = calculate_mortgage(mi)
        costs, _ = monthly_housing_cost_series(result, mi)
        # P&I + tax + ins + hoa (no PMI at 20% down)
        self.assertAlmostEqual(costs[0], 2528.27 + 500 + 125 + 250, delta=0.05)

    def test_costs_drop_after_early_payoff(self):
        mi = _default_inputs(extra_monthly_payment=2000.0)
        result = calculate_mortgage(mi)
        costs, balances = monthly_housing_cost_series(result, mi)
        payoff = result.months_to_payoff
        self.assertLess(payoff, 360)
        # After payoff only tax + ins + hoa remain
        self.assertAlmostEqual(costs[payoff], 500 + 125 + 250, delta=0.05)
        self.assertEqual(balances[payoff], 0.0)


class TestIntegration(unittest.TestCase):
    """End-to-end test with the reference scenario."""

    def test_full_pipeline(self):
        mi = _default_inputs()
        mortgage = calculate_mortgage(mi)

        # Mortgage sanity
        self.assertAlmostEqual(mortgage.monthly_principal_interest, 2528.27, delta=0.01)

        # Appreciation
        appreciation = calculate_appreciation(
            mi.home_price, "78701", mortgage.total_paid, years=mi.loan_term_years
        )
        self.assertGreater(appreciation.future_value, mi.home_price)

        # Rent vs Buy
        costs, balances = monthly_housing_cost_series(mortgage, mi)
        rvb = RentVsBuyInputs(
            monthly_rent=2000.0,
            down_payment=mi.down_payment_amount,
            home_price=mi.home_price,
            home_cagr=appreciation.cagr,
            monthly_housing_costs=costs,
            loan_balances=balances,
            annual_rent_increase_pct=3.0,
            spy_annual_return=10.0,
            sale_cost_pct=6.0,
            horizon_years=mi.loan_term_years,
        )
        snapshots = calculate_rent_vs_buy(rvb)
        self.assertEqual(len(snapshots), 30)

        # Both net-worth paths must be positive and computed
        self.assertGreater(snapshots[-1].renter_portfolio, 0)
        self.assertGreater(snapshots[-1].buyer_net_worth, 0)

        # At year 30 the loan is retired: equity = home value net of sale costs
        final = snapshots[-1]
        self.assertAlmostEqual(
            final.home_equity, final.home_value * 0.94, delta=1.0
        )


if __name__ == "__main__":
    unittest.main()
