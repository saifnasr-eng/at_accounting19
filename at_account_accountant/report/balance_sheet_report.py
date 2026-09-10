# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.tools import float_compare

from .financial_statement_common import PL_TYPES


class ReportBalanceSheet(models.AbstractModel):
    _name = "report.at_account_accountant.report_balance_sheet"
    _inherit = "at.financial.statement.common"
    _description = "Balance Sheet Report"

    def _retained_earnings(self, wizard):
        """Split accumulated profit into prior years and the current year.

        Odoo does not post a closing entry per year, so the profit sitting in
        income and expense accounts has to be reclassified into equity here.
        Anything dated before the fiscal year of the end date is 'previous
        years', the rest is 'current year'.
        """
        fy_start = wizard._fiscalyear_start()
        pl_filter = [("account_id.account_type", "in", PL_TYPES)]

        previous = self.env["account.move.line"]._read_group(
            wizard._base_domain() + pl_filter + [("date", "<", fy_start)],
            groupby=[],
            aggregates=["balance:sum"],
        )
        current = self.env["account.move.line"]._read_group(
            wizard._base_domain() + pl_filter + [
                ("date", ">=", fy_start),
                ("date", "<=", wizard.date_to),
            ],
            groupby=[],
            aggregates=["balance:sum"],
        )
        # _read_group with no groupby returns a single tuple of aggregates.
        previous_balance = previous[0][0] or 0.0
        current_balance = current[0][0] or 0.0

        # Income and expense carry a negative balance when profitable; flip
        # the sign so a profit shows as a positive equity figure.
        return -previous_balance, -current_balance

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["at.financial.report.wizard"].browse(docids)
        wizard.ensure_one()

        currency = wizard.company_id.currency_id
        hide_zero = wizard.hide_zero_balance

        # Off-balance accounts are excluded: they are memo entries and would
        # break the accounting equation.
        totals = self._sum_by_account_type(
            wizard._as_of_domain() + [("account_id.account_type", "!=", "off_balance")]
        )

        current_assets = self._build_section(_("Current Assets"), [
            (_("Bank and Cash"), self._sum_for_types(totals, ("asset_cash",))),
            (_("Receivables"), self._sum_for_types(totals, ("asset_receivable",))),
            (_("Prepayments"), self._sum_for_types(totals, ("asset_prepayments",))),
            (_("Other Current Assets"), self._sum_for_types(totals, ("asset_current",))),
        ], currency, hide_zero)

        fixed_assets = self._build_section(_("Non-current Assets"), [
            (_("Fixed Assets"), self._sum_for_types(totals, ("asset_fixed",))),
            (_("Other Non-current Assets"),
             self._sum_for_types(totals, ("asset_non_current",))),
        ], currency, hide_zero)

        # Liabilities and equity are credit-natured, so flip the sign.
        current_liabilities = self._build_section(_("Current Liabilities"), [
            (_("Payables"), -self._sum_for_types(totals, ("liability_payable",))),
            (_("Credit Cards"), -self._sum_for_types(totals, ("liability_credit_card",))),
            (_("Other Current Liabilities"),
             -self._sum_for_types(totals, ("liability_current",))),
        ], currency, hide_zero)

        non_current_liabilities = self._build_section(_("Non-current Liabilities"), [
            (_("Long-term Liabilities"),
             -self._sum_for_types(totals, ("liability_non_current",))),
        ], currency, hide_zero)

        previous_earnings, current_earnings = self._retained_earnings(wizard)
        equity = self._build_section(_("Equity"), [
            (_("Capital and Reserves"), -self._sum_for_types(totals, ("equity",))),
            (_("Unallocated Earnings"),
             -self._sum_for_types(totals, ("equity_unaffected",))),
            (_("Previous Years Earnings"), previous_earnings),
            (_("Current Year Earnings"), current_earnings),
        ], currency, hide_zero)

        total_assets = current_assets["total"] + fixed_assets["total"]
        total_liabilities = (
            current_liabilities["total"] + non_current_liabilities["total"]
        )
        total_equity = equity["total"]

        return {
            "doc_ids": docids,
            "doc_model": "at.financial.report.wizard",
            "docs": wizard,
            "currency": currency,
            "asset_sections": [current_assets, fixed_assets],
            "liability_sections": [current_liabilities, non_current_liabilities],
            "equity_section": equity,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "total_liabilities_equity": total_liabilities + total_equity,
            "is_balanced": float_compare(
                total_assets,
                total_liabilities + total_equity,
                precision_rounding=currency.rounding,
            ) == 0,
        }
