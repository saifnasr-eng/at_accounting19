# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests import tagged

from .common import AtAccountingCase


@tagged("post_install", "-at_install")
class TestAssetLifecycle(AtAccountingCase):
    """One asset from purchase to disposal, checking the ledger at each step.

    The unit tests cover each operation on its own; this one is here because
    the operations interact — a revaluation changes what a later disposal has
    to reverse, and only running them in sequence catches that.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_gain_loss = cls._make_account(
            "ATLG", "Gain/Loss on Disposal", "income_other"
        )
        cls.account_reval = cls._make_account(
            "ATLR", "Revaluation Reserve", "equity"
        )

    def _post(self, ref, lines):
        move = self.env["account.move"].create({
            "journal_id": self.journal.id,
            "company_id": self.company.id,
            "date": "2026-01-01",
            "ref": ref,
            "line_ids": [
                (0, 0, {"name": ref, "account_id": account.id,
                        "debit": debit, "credit": credit})
                for account, debit, credit in lines
            ],
        })
        move.action_post()
        return move

    def test_purchase_depreciate_revalue_dispose(self):
        # The module never books the purchase itself; a vendor bill does.
        self._post("Van purchase", [
            (self.account_asset, 24000.0, 0.0),
            (self.account_cash, 0.0, 24000.0),
        ])

        asset = self._make_asset(
            name="Delivery Van",
            original_value=24000.0,
            salvage_value=2400.0,
            method_number=24,
        )
        asset.action_confirm()
        self.assertAlmostEqual(asset.depreciable_value, 21600.0, places=2)
        self.assertAlmostEqual(
            sum(asset.depreciation_line_ids.mapped("amount")), 21600.0, places=2
        )

        # Six months of depreciation, posted the way the cron would.
        self.env["at.account.asset"]._cron_post_depreciation(
            date=date(2026, 6, 30)
        )
        self.assertEqual(
            len(asset.depreciation_line_ids.filtered("move_posted")), 6
        )
        self.assertAlmostEqual(asset.value_residual, 18600.0, places=2)

        for move in asset.depreciation_line_ids.mapped("move_id"):
            self.assertAlmostEqual(
                sum(move.line_ids.mapped("balance")), 0.0, places=2
            )

        # Revalue upward, which raises the gross value and rebuilds the board.
        self.env["at.asset.revaluation.wizard"].create({
            "asset_id": asset.id,
            "date": "2026-07-01",
            "new_value": 20000.0,
            "revaluation_account_id": self.account_reval.id,
            "journal_id": self.journal.id,
        }).action_revalue()
        self.assertAlmostEqual(asset.original_value, 25400.0, places=2)
        self.assertAlmostEqual(
            sum(asset.depreciation_line_ids.mapped("amount")),
            asset.depreciable_value,
            places=2,
        )

        # Sell below book value: a 5,000 loss against a 20,000 book value.
        self.env["at.asset.disposal.wizard"].create({
            "asset_id": asset.id,
            "date": "2026-07-31",
            "disposal_type": "sale",
            "proceeds": 15000.0,
            "proceeds_account_id": self.account_cash.id,
            "gain_loss_account_id": self.account_gain_loss.id,
            "journal_id": self.journal.id,
        }).action_dispose()

        self.assertEqual(asset.state, "disposed")
        disposal = asset.disposal_move_id
        self.assertAlmostEqual(
            sum(disposal.line_ids.mapped("balance")), 0.0, places=2
        )
        loss = sum(disposal.line_ids.filtered(
            lambda line: line.account_id == self.account_gain_loss
        ).mapped("balance"))
        self.assertAlmostEqual(loss, 5000.0, places=2)

        # The asset and its accumulated depreciation are off the books.
        remaining = sum(self.env["account.move.line"].search([
            ("account_id", "in",
             (self.account_asset.id, self.account_depreciation.id)),
            ("company_id", "=", self.company.id),
        ]).mapped("balance"))
        self.assertAlmostEqual(remaining, 0.0, places=2)

        # And the balance sheet still balances after all of it.
        wizard = self.env["at.financial.report.wizard"].create({
            "report_type": "balance_sheet",
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "company_id": self.company.id,
        })
        values = self.env[
            "report.at_account_accountant.report_balance_sheet"
        ]._get_report_values(wizard.ids)
        self.assertTrue(values["is_balanced"])
