# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import AtAccountingCase


@tagged("post_install", "-at_install")
class TestAssetDisposal(AtAccountingCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_gain_loss = cls._make_account(
            "ATGL", "Gain/Loss on Disposal", "income_other"
        )
        cls.account_reval = cls._make_account(
            "ATRV", "Revaluation Reserve", "equity"
        )

    def _running_asset(self, periods_posted=0, **overrides):
        asset = self._make_asset(**overrides)
        asset.action_confirm()
        for line in asset.depreciation_line_ids[:periods_posted]:
            line.create_move()
        return asset

    def _dispose(self, asset, **overrides):
        values = {
            "asset_id": asset.id,
            "date": "2026-06-30",
            "gain_loss_account_id": self.account_gain_loss.id,
            "journal_id": self.journal.id,
        }
        values.update(overrides)
        wizard = self.env["at.asset.disposal.wizard"].create(values)
        wizard.action_dispose()
        return wizard

    def test_scrapping_writes_off_the_whole_book_value(self):
        asset = self._running_asset(
            periods_posted=2, original_value=10000.0, method_number=10
        )
        self.assertAlmostEqual(asset.value_residual, 8000.0, places=2)

        self._dispose(asset, disposal_type="scrap")

        self.assertEqual(asset.state, "disposed")
        move = asset.disposal_move_id
        self.assertEqual(move.state, "posted")
        self.assertAlmostEqual(sum(move.line_ids.mapped("balance")), 0.0, places=2)

        # The whole remaining book value is the loss.
        loss = move.line_ids.filtered(
            lambda line: line.account_id == self.account_gain_loss
        )
        self.assertAlmostEqual(loss.debit, 8000.0, places=2)

    def test_selling_above_book_value_records_a_gain(self):
        asset = self._running_asset(
            periods_posted=2, original_value=10000.0, method_number=10
        )
        self._dispose(
            asset,
            disposal_type="sale",
            proceeds=9000.0,
            proceeds_account_id=self.account_cash.id,
        )

        move = asset.disposal_move_id
        self.assertAlmostEqual(sum(move.line_ids.mapped("balance")), 0.0, places=2)

        gain = move.line_ids.filtered(
            lambda line: line.account_id == self.account_gain_loss
        )
        # Sold for 9000 against a book value of 8000.
        self.assertAlmostEqual(gain.credit, 1000.0, places=2)

    def test_selling_at_book_value_records_no_gain_or_loss(self):
        asset = self._running_asset(
            periods_posted=2, original_value=10000.0, method_number=10
        )
        self._dispose(
            asset,
            proceeds=8000.0,
            proceeds_account_id=self.account_cash.id,
        )

        move = asset.disposal_move_id
        self.assertFalse(move.line_ids.filtered(
            lambda line: line.account_id == self.account_gain_loss
        ))
        self.assertAlmostEqual(sum(move.line_ids.mapped("balance")), 0.0, places=2)

    def test_disposal_voids_future_periods(self):
        asset = self._running_asset(
            periods_posted=2, original_value=10000.0, method_number=10
        )
        self._dispose(asset, disposal_type="scrap")

        self.assertEqual(len(asset.depreciation_line_ids), 2)
        self.assertTrue(all(asset.depreciation_line_ids.mapped("move_posted")))

    def test_draft_asset_cannot_be_disposed(self):
        asset = self._make_asset()
        with self.assertRaises(UserError):
            self._dispose(asset, disposal_type="scrap")

    def test_proceeds_require_an_account(self):
        asset = self._running_asset(periods_posted=1)
        with self.assertRaises(UserError):
            self._dispose(asset, proceeds=500.0)

    def test_revaluation_upward_adjusts_asset_and_remaining_board(self):
        asset = self._running_asset(
            periods_posted=2, original_value=10000.0, method_number=10
        )
        wizard = self.env["at.asset.revaluation.wizard"].create({
            "asset_id": asset.id,
            "date": "2026-06-30",
            "new_value": 12000.0,
            "revaluation_account_id": self.account_reval.id,
            "journal_id": self.journal.id,
        })
        self.assertAlmostEqual(wizard.current_value, 8000.0, places=2)
        self.assertAlmostEqual(wizard.difference, 4000.0, places=2)

        wizard.action_revalue()

        # Gross value rose by the adjustment, and the board still totals it.
        self.assertAlmostEqual(asset.original_value, 14000.0, places=2)
        self.assertAlmostEqual(
            sum(asset.depreciation_line_ids.mapped("amount")), 14000.0, places=2
        )
        self.assertEqual(len(asset.depreciation_line_ids.filtered("move_posted")), 2)

    def test_revaluation_downward_is_an_impairment(self):
        asset = self._running_asset(
            periods_posted=2, original_value=10000.0, method_number=10
        )
        self.env["at.asset.revaluation.wizard"].create({
            "asset_id": asset.id,
            "date": "2026-06-30",
            "new_value": 6000.0,
            "revaluation_account_id": self.account_reval.id,
            "journal_id": self.journal.id,
        }).action_revalue()

        self.assertAlmostEqual(asset.original_value, 8000.0, places=2)

    def test_revaluation_to_the_same_value_is_rejected(self):
        asset = self._running_asset(periods_posted=2, original_value=10000.0,
                                    method_number=10)
        wizard = self.env["at.asset.revaluation.wizard"].create({
            "asset_id": asset.id,
            "date": "2026-06-30",
            "new_value": asset.value_residual,
            "revaluation_account_id": self.account_reval.id,
            "journal_id": self.journal.id,
        })
        with self.assertRaises(UserError):
            wizard.action_revalue()
