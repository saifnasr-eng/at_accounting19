# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import AtAccountingCase


@tagged("post_install", "-at_install")
class TestAssetBoard(AtAccountingCase):

    def test_linear_board_totals_exactly(self):
        asset = self._make_asset(original_value=1000.0, method_number=3)
        asset.compute_depreciation_board()

        amounts = asset.depreciation_line_ids.mapped("amount")
        self.assertEqual(len(amounts), 3)
        self.assertAlmostEqual(sum(amounts), 1000.0, places=2)

    def test_salvage_value_is_never_depreciated(self):
        asset = self._make_asset(original_value=10000.0, salvage_value=1000.0)
        asset.compute_depreciation_board()

        self.assertAlmostEqual(asset.depreciable_value, 9000.0, places=2)
        self.assertAlmostEqual(
            sum(asset.depreciation_line_ids.mapped("amount")), 9000.0, places=2
        )
        self.assertAlmostEqual(
            asset.depreciation_line_ids[-1].remaining_value, 1000.0, places=2
        )

    def test_degressive_switches_to_linear_and_totals(self):
        asset = self._make_asset(method="degressive", method_progress_factor=0.3)
        asset.compute_depreciation_board()

        amounts = asset.depreciation_line_ids.mapped("amount")
        self.assertEqual(len(amounts), 10)
        self.assertAlmostEqual(sum(amounts), 10000.0, places=2)
        # Declining balance alone would never reach zero; the switch to the
        # straight-line amount is what closes the asset out.
        self.assertGreater(amounts[0], amounts[-1])
        self.assertTrue(all(amount > 0 for amount in amounts))

    def test_board_dates_follow_the_period(self):
        asset = self._make_asset(method_period="3", method_number=4)
        asset.compute_depreciation_board()

        dates = asset.depreciation_line_ids.mapped("date")
        self.assertEqual(str(dates[0]), "2026-01-01")
        self.assertEqual(str(dates[1]), "2026-04-01")
        self.assertEqual(str(dates[3]), "2026-10-01")

    def test_posting_creates_a_balanced_entry(self):
        asset = self._make_asset(original_value=1200.0, method_number=12)
        asset.action_confirm()
        self.assertEqual(asset.state, "running")

        line = asset.depreciation_line_ids[0]
        move = line.create_move()

        self.assertEqual(move.state, "posted")
        self.assertAlmostEqual(sum(move.line_ids.mapped("balance")), 0.0, places=2)
        self.assertAlmostEqual(sum(move.line_ids.mapped("debit")), 100.0, places=2)
        self.assertTrue(line.move_posted)
        self.assertAlmostEqual(asset.value_depreciated, 100.0, places=2)
        self.assertAlmostEqual(asset.value_residual, 1100.0, places=2)

    def test_deferred_revenue_reverses_the_entry_sides(self):
        asset = self._make_asset(
            asset_type="sale",
            original_value=1200.0,
            method_number=12,
            account_depreciation_id=self.account_asset.id,
            account_expense_id=self.account_income.id,
        )
        asset.action_confirm()
        move = asset.depreciation_line_ids[0].create_move()

        debit_line = move.line_ids.filtered(lambda line: line.debit)
        credit_line = move.line_ids.filtered(lambda line: line.credit)
        # Revenue is recognised: the deferral account is debited down and the
        # income account is credited.
        self.assertEqual(debit_line.account_id, self.account_asset)
        self.assertEqual(credit_line.account_id, self.account_income)

    def test_asset_closes_once_fully_posted(self):
        asset = self._make_asset(original_value=300.0, method_number=3)
        asset.action_confirm()
        asset.depreciation_line_ids.create_move()

        self.assertEqual(asset.state, "closed")
        self.assertAlmostEqual(asset.value_residual, 0.0, places=2)

    def test_posted_line_cannot_be_deleted(self):
        asset = self._make_asset(original_value=300.0, method_number=3)
        asset.action_confirm()
        line = asset.depreciation_line_ids[0]
        line.create_move()

        with self.assertRaises(UserError):
            line.unlink()

    def test_recompute_keeps_posted_periods(self):
        asset = self._make_asset(original_value=1200.0, method_number=12)
        asset.action_confirm()
        asset.depreciation_line_ids[0].create_move()

        asset.compute_depreciation_board()

        posted = asset.depreciation_line_ids.filtered("move_posted")
        self.assertEqual(len(posted), 1)
        self.assertEqual(len(asset.depreciation_line_ids), 12)

    def test_running_asset_cannot_be_reset_after_posting(self):
        asset = self._make_asset(original_value=300.0, method_number=3)
        asset.action_confirm()
        asset.depreciation_line_ids[0].create_move()

        with self.assertRaises(UserError):
            asset.action_set_to_draft()

    def test_salvage_value_above_original_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_asset(original_value=1000.0, salvage_value=1000.0)

    def test_declining_factor_must_be_a_fraction(self):
        with self.assertRaises(ValidationError):
            self._make_asset(method="degressive", method_progress_factor=1.5)
