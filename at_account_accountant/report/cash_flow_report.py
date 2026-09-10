# -*- coding: utf-8 -*-
from odoo import _, api, models

CASH_TYPES = ("asset_cash",)

# Cash movements are classified by what the *other* side of the entry hits.
OPERATING_TYPES = (
    "asset_receivable", "liability_payable", "asset_prepayments",
    "asset_current", "liability_current", "liability_credit_card",
    "income", "income_other",
    "expense", "expense_depreciation", "expense_direct_cost",
)
INVESTING_TYPES = ("asset_fixed", "asset_non_current")
FINANCING_TYPES = ("equity", "equity_unaffected", "liability_non_current")


class ReportCashFlow(models.AbstractModel):
    _name = "report.at_account_accountant.report_cash_flow"
    _inherit = "at.financial.statement.common"
    _description = "Cash Flow Statement"

    def _cash_balance(self, wizard, domain_extra):
        groups = self.env["account.move.line"]._read_group(
            wizard._base_domain()
            + [("account_id.account_type", "in", CASH_TYPES)]
            + domain_extra,
            groupby=[],
            aggregates=["balance:sum"],
        )
        return groups[0][0] or 0.0

    def _counterpart_totals(self, wizard):
        """Attribute each cash movement to the account type it faced.

        Odoo stores no 'cash flow category' on a move, so the classification
        is derived: take every entry that touched cash during the period, then
        look at its non-cash lines. Their balance, negated, is the cash the
        entry produced or consumed.
        """
        AccountMoveLine = self.env["account.move.line"]

        cash_lines = AccountMoveLine.search(
            wizard._period_domain()
            + [("account_id.account_type", "in", CASH_TYPES)]
        )
        moves = cash_lines.move_id
        if not moves:
            return {}

        counterpart_lines = AccountMoveLine.search([
            ("move_id", "in", moves.ids),
            ("account_id.account_type", "not in", CASH_TYPES),
        ])

        totals = {}
        for line in counterpart_lines:
            account_type = line.account_id.account_type
            totals[account_type] = totals.get(account_type, 0.0) - line.balance
        return totals

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["at.financial.report.wizard"].browse(docids)
        wizard.ensure_one()

        currency = wizard.company_id.currency_id
        hide_zero = wizard.hide_zero_balance

        opening = self._cash_balance(wizard, [("date", "<", wizard.date_from)])
        closing = self._cash_balance(wizard, [("date", "<=", wizard.date_to)])

        totals = self._counterpart_totals(wizard)

        operating = self._build_section(_("Operating Activities"), [
            (_("Customer Receipts"),
             self._sum_for_types(totals, ("asset_receivable",))),
            (_("Supplier Payments"),
             self._sum_for_types(totals, ("liability_payable",))),
            (_("Income Received Directly"),
             self._sum_for_types(totals, ("income", "income_other"))),
            (_("Expenses Paid Directly"),
             self._sum_for_types(totals, ("expense", "expense_depreciation",
                                          "expense_direct_cost"))),
            (_("Other Working Capital"),
             self._sum_for_types(totals, ("asset_prepayments", "asset_current",
                                          "liability_current",
                                          "liability_credit_card"))),
        ], currency, hide_zero)

        investing = self._build_section(_("Investing Activities"), [
            (_("Fixed Assets"), self._sum_for_types(totals, ("asset_fixed",))),
            (_("Other Non-current Assets"),
             self._sum_for_types(totals, ("asset_non_current",))),
        ], currency, hide_zero)

        financing = self._build_section(_("Financing Activities"), [
            (_("Equity"),
             self._sum_for_types(totals, ("equity", "equity_unaffected"))),
            (_("Long-term Liabilities"),
             self._sum_for_types(totals, ("liability_non_current",))),
        ], currency, hide_zero)

        # Anything the classification above did not cover, so the statement
        # always reconciles to the actual change in cash.
        classified = set(OPERATING_TYPES + INVESTING_TYPES + FINANCING_TYPES)
        unclassified = sum(
            amount for account_type, amount in totals.items()
            if account_type not in classified
        )

        net_change = (
            operating["total"] + investing["total"] + financing["total"]
            + unclassified
        )

        return {
            "doc_ids": docids,
            "doc_model": "at.financial.report.wizard",
            "docs": wizard,
            "currency": currency,
            "sections": [operating, investing, financing],
            "unclassified": unclassified,
            "opening": opening,
            "closing": closing,
            "net_change": net_change,
            "reconciles": currency.is_zero(closing - opening - net_change),
        }
