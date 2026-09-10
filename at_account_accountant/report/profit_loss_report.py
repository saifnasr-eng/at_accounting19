# -*- coding: utf-8 -*-
from odoo import _, api, models

from .financial_statement_common import EXPENSE_TYPES, INCOME_TYPES


class ReportProfitLoss(models.AbstractModel):
    _name = "report.at_account_accountant.report_profit_loss"
    _inherit = "at.financial.statement.common"
    _description = "Profit and Loss Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["at.financial.report.wizard"].browse(docids)
        wizard.ensure_one()

        currency = wizard.company_id.currency_id
        hide_zero = wizard.hide_zero_balance

        # Unlike the balance sheet, a P&L covers the selected period only.
        totals = self._sum_by_account_type(
            wizard._period_domain()
            + [("account_id.account_type", "in", INCOME_TYPES + EXPENSE_TYPES)]
        )

        # Income accounts are credit-natured, so flip the sign to show
        # revenue as positive. Expenses are debit-natured and stay as they are.
        income = self._build_section(_("Operating Income"), [
            (_("Sales and Revenue"), -self._sum_for_types(totals, ("income",))),
            (_("Other Income"), -self._sum_for_types(totals, ("income_other",))),
        ], currency, hide_zero)

        cost_of_revenue = self._build_section(_("Cost of Revenue"), [
            (_("Cost of Goods Sold"),
             self._sum_for_types(totals, ("expense_direct_cost",))),
        ], currency, hide_zero)

        operating_expenses = self._build_section(_("Operating Expenses"), [
            (_("Expenses"), self._sum_for_types(totals, ("expense",))),
            (_("Depreciation"),
             self._sum_for_types(totals, ("expense_depreciation",))),
        ], currency, hide_zero)

        gross_profit = income["total"] - cost_of_revenue["total"]
        net_profit = gross_profit - operating_expenses["total"]

        return {
            "doc_ids": docids,
            "doc_model": "at.financial.report.wizard",
            "docs": wizard,
            "currency": currency,
            "income_section": income,
            "cost_section": cost_of_revenue,
            "expense_section": operating_expenses,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
        }
