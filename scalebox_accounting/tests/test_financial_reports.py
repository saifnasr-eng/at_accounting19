# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import AtAccountingCase


@tagged("post_install", "-at_install")
class TestFinancialReports(AtAccountingCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard_model = cls.env["at.financial.report.wizard"]

        # One sale funded in cash: income 5000, cash 5000.
        cls._post_entry("2026-02-10", [
            (cls.account_cash, 5000.0, 0.0),
            (cls.account_income, 0.0, 5000.0),
        ])
        # One expense paid in cash: expense 2000, cash -2000.
        cls._post_entry("2026-02-15", [
            (cls.account_expense, 2000.0, 0.0),
            (cls.account_cash, 0.0, 2000.0),
        ])

    @classmethod
    def _post_entry(cls, date, lines):
        move = cls.env["account.move"].create({
            "journal_id": cls.journal.id,
            "company_id": cls.company.id,
            "date": date,
            "line_ids": [
                (0, 0, {
                    "name": "test",
                    "account_id": account.id,
                    "debit": debit,
                    "credit": credit,
                })
                for account, debit, credit in lines
            ],
        })
        move.action_post()
        return move

    def _wizard(self, report_type, **overrides):
        values = {
            "report_type": report_type,
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "company_id": self.company.id,
        }
        values.update(overrides)
        return self.wizard_model.create(values)

    def test_trial_balance_debits_equal_credits(self):
        wizard = self._wizard("trial_balance")
        values = self.env[
            "report.scalebox_accounting.report_trial_balance"
        ]._get_report_values(wizard.ids)

        self.assertAlmostEqual(
            values["totals"]["debit"], values["totals"]["credit"], places=2
        )
        self.assertAlmostEqual(values["totals"]["debit"], 7000.0, places=2)

    def test_profit_loss_nets_income_less_expense(self):
        wizard = self._wizard("profit_loss")
        values = self.env[
            "report.scalebox_accounting.report_profit_loss"
        ]._get_report_values(wizard.ids)

        self.assertAlmostEqual(values["income_section"]["total"], 5000.0, places=2)
        self.assertAlmostEqual(values["expense_section"]["total"], 2000.0, places=2)
        self.assertAlmostEqual(values["net_profit"], 3000.0, places=2)

    def test_balance_sheet_balances_with_earnings_reclassified(self):
        wizard = self._wizard("balance_sheet")
        values = self.env[
            "report.scalebox_accounting.report_balance_sheet"
        ]._get_report_values(wizard.ids)

        # Cash of 3000 on one side; the same 3000 of profit reclassified into
        # equity on the other. If the reclassification were missing this would
        # be off by exactly the period's profit.
        self.assertAlmostEqual(values["total_assets"], 3000.0, places=2)
        self.assertAlmostEqual(values["total_liabilities_equity"], 3000.0, places=2)
        self.assertTrue(values["is_balanced"])

    def test_cash_flow_reconciles_to_the_change_in_cash(self):
        wizard = self._wizard("cash_flow")
        values = self.env[
            "report.scalebox_accounting.report_cash_flow"
        ]._get_report_values(wizard.ids)

        self.assertAlmostEqual(values["opening"], 0.0, places=2)
        self.assertAlmostEqual(values["closing"], 3000.0, places=2)
        self.assertAlmostEqual(values["net_change"], 3000.0, places=2)
        self.assertTrue(values["reconciles"])

    def test_general_ledger_running_balance_ends_at_closing(self):
        wizard = self._wizard("general_ledger")
        values = self.env[
            "report.scalebox_accounting.report_general_ledger"
        ]._get_report_values(wizard.ids)

        cash = next(
            data for data in values["accounts"]
            if data["account"] == self.account_cash
        )
        self.assertAlmostEqual(cash["closing"], 3000.0, places=2)
        self.assertAlmostEqual(
            cash["entries"][-1]["running_balance"], 3000.0, places=2
        )

    def test_hiding_zero_rows_does_not_change_totals(self):
        shown = self._wizard("profit_loss", hide_zero_balance=False)
        hidden = self._wizard("profit_loss", hide_zero_balance=True)
        engine = self.env["report.scalebox_accounting.report_profit_loss"]

        self.assertAlmostEqual(
            engine._get_report_values(shown.ids)["net_profit"],
            engine._get_report_values(hidden.ids)["net_profit"],
            places=2,
        )

    def test_every_report_type_resolves_to_an_action(self):
        selection = dict(
            self.wizard_model._fields["report_type"]._description_selection(self.env)
        )
        for report_type in selection:
            wizard = self._wizard(report_type)
            # Odoo wraps the report in a layout-configuration wizard the
            # first time a company prints anything, so opt out of that check.
            action = wizard.with_context(discard_logo_check=True).print_report()
            self.assertEqual(action["type"], "ir.actions.report")
